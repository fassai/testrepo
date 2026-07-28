"""Apify scraping layer.

Design rule: NEVER crash the run. Every failure path returns a partial bundle
with `errors` noted, and downstream scoring degrades to "limited data" mode.
FB is presence-only in the MVP — reliable FB page scraping is login-walled and
expensive, so the FB handle counts toward cross-platform presence but isn't mined.
"""
import logging

import httpx

from . import config

log = logging.getLogger("chc.scraper")

APIFY_BASE = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
IG_ACTOR = "apify~instagram-profile-scraper"
TIKTOK_ACTOR = "clockworks~tiktok-profile-scraper"


def _run_actor(actor: str, payload: dict) -> list[dict]:
    url = APIFY_BASE.format(actor=actor)
    r = httpx.post(
        url,
        params={"token": config.APIFY_TOKEN},
        json=payload,
        timeout=config.SCRAPE_TIMEOUT_SECONDS,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def scrape_instagram(handle: str) -> dict:
    items = _run_actor(IG_ACTOR, {"usernames": [handle]})
    if not items:
        return {"found": False}
    p = items[0]
    if p.get("error"):
        return {"found": False, "private": "private" in str(p.get("error", "")).lower()}
    posts = p.get("latestPosts") or []
    return {
        "found": True,
        "private": bool(p.get("private")),
        "username": p.get("username", handle),
        "full_name": p.get("fullName"),
        "bio": p.get("biography"),
        "external_url": p.get("externalUrl"),
        "followers": p.get("followersCount"),
        "following": p.get("followsCount"),
        "posts_total": p.get("postsCount"),
        "is_business": p.get("isBusinessAccount"),
        "recent_posts": [
            {
                "caption": (post.get("caption") or "")[:300],
                "likes": post.get("likesCount"),
                "comments": post.get("commentsCount"),
                "video_views": post.get("videoViewCount"),
                "type": post.get("type"),
                "timestamp": post.get("timestamp"),
            }
            for post in posts[:12]
        ],
    }


def scrape_tiktok(handle: str) -> dict:
    items = _run_actor(TIKTOK_ACTOR, {"profiles": [handle], "resultsPerPage": 10})
    if not items:
        return {"found": False}
    author = (items[0].get("authorMeta") or {}) if items else {}
    videos = [
        {
            "caption": (it.get("text") or "")[:300],
            "plays": it.get("playCount"),
            "likes": it.get("diggCount"),
            "comments": it.get("commentCount"),
            "shares": it.get("shareCount"),
            "timestamp": it.get("createTimeISO"),
        }
        for it in items[:10]
        if it.get("text") is not None or it.get("playCount") is not None
    ]
    return {
        "found": bool(author.get("name") or videos),
        "username": author.get("name", handle),
        "bio": author.get("signature"),
        "followers": author.get("fans"),
        "recent_posts": videos,
    }


def scrape_all(ig: str | None, fb: str | None, tiktok: str | None,
               competitor: str | None) -> dict:
    """Returns a bundle: per-platform data + competitor + error notes.

    Missing token, timeouts, private accounts → still returns a usable bundle.
    """
    bundle: dict = {
        "instagram": None, "tiktok": None,
        "facebook_presence": bool(fb), "fb_handle": fb,
        "competitor": None, "errors": [],
    }
    if not config.APIFY_TOKEN:
        bundle["errors"].append("no_scraper_configured")
        return bundle

    if ig:
        try:
            bundle["instagram"] = scrape_instagram(ig)
        except Exception as e:  # noqa: BLE001 — degrade, never crash
            log.warning("IG scrape failed for %s: %s", ig, e)
            bundle["errors"].append(f"ig_scrape_failed")
    if tiktok:
        try:
            bundle["tiktok"] = scrape_tiktok(tiktok)
        except Exception as e:  # noqa: BLE001
            log.warning("TikTok scrape failed for %s: %s", tiktok, e)
            bundle["errors"].append("tiktok_scrape_failed")
    if competitor:
        # Viral hook: competitor peek. IG only — cheapest per run.
        try:
            bundle["competitor"] = scrape_instagram(competitor)
            if bundle["competitor"] is not None:
                bundle["competitor"]["handle"] = competitor
        except Exception as e:  # noqa: BLE001
            log.warning("Competitor scrape failed for %s: %s", competitor, e)
            bundle["errors"].append("competitor_scrape_failed")
    return bundle
