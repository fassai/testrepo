"""Deterministic metrics computed in Python from scraped data.

These are the FACTS the LLM is allowed to ground its analysis in — keeping the
LLM input small (cheap) and every claim traceable to a real scraped signal.
"""


def _engagement(posts: list[dict], followers: int | None) -> dict:
    likes = [p.get("likes") for p in posts if isinstance(p.get("likes"), (int, float))]
    comments = [p.get("comments") for p in posts if isinstance(p.get("comments"), (int, float))]
    views = [p.get("video_views") or p.get("plays") for p in posts
             if isinstance(p.get("video_views") or p.get("plays"), (int, float))]
    shares = [p.get("shares") for p in posts if isinstance(p.get("shares"), (int, float))]
    out: dict = {"posts_sampled": len(posts)}
    if likes:
        out["avg_likes"] = round(sum(likes) / len(likes), 1)
    if comments:
        out["avg_comments"] = round(sum(comments) / len(comments), 1)
    if views:
        out["avg_views"] = round(sum(views) / len(views), 1)
    if shares:
        out["avg_shares"] = round(sum(shares) / len(shares), 1)
    if likes and followers:
        out["engagement_rate_pct"] = round(
            (sum(likes) + sum(comments or [0])) / max(len(likes), 1) / followers * 100, 2
        )
    if views and likes:
        avg_views = sum(views) / len(views)
        if avg_views:
            out["like_to_view_pct"] = round(sum(likes) / len(likes) / avg_views * 100, 2)
    return out


def _platform_metrics(p: dict | None) -> dict | None:
    if not p:
        return None
    if not p.get("found"):
        return {"found": False, "private": bool(p.get("private"))}
    posts = p.get("recent_posts") or []
    return {
        "found": True,
        "private": bool(p.get("private")),
        "username": p.get("username"),
        "bio": (p.get("bio") or "")[:400],
        "has_link_in_bio": bool(p.get("external_url")),
        "followers": p.get("followers"),
        "posts_total": p.get("posts_total"),
        "recent_captions": [pp.get("caption") for pp in posts[:5] if pp.get("caption")],
        "engagement": _engagement(posts, p.get("followers")),
    }


def build_metrics(bundle: dict, form: dict) -> dict:
    """Compact fact sheet handed to the scoring layer."""
    ig = _platform_metrics(bundle.get("instagram"))
    tt = _platform_metrics(bundle.get("tiktok"))
    comp = _platform_metrics(bundle.get("competitor"))

    platforms_provided = sum(1 for h in (form.get("ig_handle"), form.get("fb_handle"),
                                         form.get("tiktok_handle")) if h)
    platforms_found = sum(1 for m in (ig, tt) if m and m.get("found"))
    if bundle.get("facebook_presence"):
        platforms_provided_note = "FB handle provided (presence only, not scraped)"
    else:
        platforms_provided_note = None

    any_data = any(m and m.get("found") for m in (ig, tt))
    if any_data and not bundle.get("errors"):
        quality = "full"
    elif any_data:
        quality = "partial"
    else:
        quality = "limited"

    return {
        "business": {
            "name": form.get("business_name"),
            "owner": form.get("name"),
            "sell_to": form.get("sell_to"),
            "industry": form.get("industry"),
        },
        "handles": {
            "instagram": form.get("ig_handle"),
            "facebook": form.get("fb_handle"),
            "tiktok": form.get("tiktok_handle"),
            "competitor": form.get("competitor_handle"),
        },
        "instagram": ig,
        "tiktok": tt,
        "facebook_note": platforms_provided_note,
        "competitor": comp,
        "platforms_provided": platforms_provided,
        "platforms_found_by_scraper": platforms_found,
        "scrape_errors": bundle.get("errors") or [],
        "data_quality": quality,
    }
