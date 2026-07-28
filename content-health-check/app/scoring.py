"""Scoring engine.

Primary: one cheap LLM call (structured outputs → guaranteed JSON).
Fallback: deterministic heuristic scores from the metric fact sheet.
Either way the run ALWAYS produces 7 aspect scores — sparse/private accounts get
hedged, low-confidence notes instead of a crash or a confidently-wrong guess.
"""
import json
import logging
import time

from . import config

log = logging.getLogger("chc.scoring")

ASPECT_KEYS = [
    "discoverability", "readability", "presence", "content",
    "target", "competitor", "international",
]

ASPECT_TITLES_TH = {
    "discoverability": "ค้นเจอง่ายแค่ไหน (Discoverability)",
    "readability": "ข้อเสนอเข้าใจง่ายแค่ไหน (Readability)",
    "presence": "ครอบคลุมหลายแพลตฟอร์ม (Presence)",
    "content": "คนชอบคอนเทนต์แค่ไหน (Content Score)",
    "target": "กลุ่มเป้าหมายของคุณคือใคร (Target Analysis)",
    "competitor": "เทียบกับคู่แข่ง (Competitor Analysis)",
    "international": "มาตรฐานสากลในวงการนี้ (International Practice)",
}

_ASPECT_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "description": "1-10"},
        "headline": {"type": "string", "description": "Thai, <=12 words, blunt health-report style"},
        "detail": {"type": "string", "description": "Thai, 2-4 sentences"},
        "evidence": {
            "type": "array", "items": {"type": "string"},
            "description": "Thai. Each item cites a concrete scraped signal from the fact sheet. Empty if none.",
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["score", "headline", "detail", "evidence", "confidence"],
    "additionalProperties": False,
}

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "aspects": {
            "type": "object",
            "properties": {k: _ASPECT_SCHEMA for k in ASPECT_KEYS},
            "required": ASPECT_KEYS,
            "additionalProperties": False,
        },
        "overall": {
            "type": "object",
            "properties": {
                "score": {"type": "integer"},
                "summary": {"type": "string", "description": "Thai, 2-3 sentences, health-checkup verdict"},
            },
            "required": ["score", "summary"],
            "additionalProperties": False,
        },
    },
    "required": ["aspects", "overall"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """คุณคือ AI วิเคราะห์สุขภาพคอนเทนต์ธุรกิจของ Content Clinic — เอเจนซี่คอนเทนต์สาย data ที่ช่วยเจ้าของธุรกิจ "สื่อสารคุณค่าของธุรกิจให้คนเข้าใจและอยากซื้อ"

ลูกค้าของเราคือเจ้าของธุรกิจ/CEO ไทยที่ติด "กับดักคอนเทนต์": รู้ว่าต้องทำคอนเทนต์แต่ทำเองไม่เวิร์ค จ้างใครก็ไม่ถูกใจ ได้ยอดวิวแต่ไม่ได้ยอดขาย ผลตรวจนี้ต้องให้ความรู้สึกเหมือนใบตรวจสุขภาพ (BMI/BIA printout): ตัวเลขตรงไปตรงมา เห็นแล้วรู้ว่ามีอะไรต้องแก้หลายจุด แต่ไม่ดูถูก ไม่ประชด

กติกาเหล็ก (ห้ามละเมิด):
1. อ้างอิงได้เฉพาะข้อเท็จจริงใน fact sheet เท่านั้น ห้ามแต่งตัวเลข ห้ามเดาว่าบัญชีมีอะไรถ้าข้อมูลไม่มี
2. ทุกข้อวิเคราะห์ต้องมี evidence อ้างอิงสัญญาณจริงจากข้อมูล (เช่น "bio เขียนว่า …", "engagement เฉลี่ย 1.2%", "โพสต์ล่าสุดพูดถึง …") หรือถ้าข้อมูลไม่พอ ให้ hedge ตรง ๆ ว่า "ข้อมูลจำกัด ประเมินจาก …" และตั้ง confidence เป็น low — การเดาผิดเรื่องธุรกิจของเขาเองทำลายความเชื่อถือทันที
3. target analysis: เดา avatar แบบมีหลักฐานได้เฉพาะเมื่อธุรกิจค้นเจอและมี caption/bio ให้อ่าน ไม่งั้นให้บอกว่าประเมินจากที่เจ้าของกรอกมา (sell_to) เท่านั้น
4. international practice: ใช้ความรู้ทั่วไปเรื่อง best practice ของ niche นี้ในต่างประเทศเป็น benchmark ได้ แต่ระบุชัดว่าเป็น benchmark ไม่ใช่ข้อมูลที่ scrape มา
5. คะแนน 1-10 ต่อหัวข้อ ให้ granular และตรงไปตรงมา — บัญชีทั่วไปที่ยังไม่จัดระบบควรได้ 3-6 ไม่ใช่ 7-8 ทุกช่อง ความรู้สึกที่ต้องการคือ "มีหลายอย่างต้องแก้" + "ระบบนี้เข้าใจธุรกิจเราจริง"
6. ภาษาไทยล้วน กระชับ อ่านบนมือถือ ห้ามใช้ศัพท์เทคนิคโดยไม่อธิบาย

นิยามหัวข้อ:
- discoverability: ค้นเจอง่ายไหม (เจอบัญชีไหม, follower, ชื่อ/bio ชัดไหม, มีลิงก์ไหม)
- readability: คนแปลกหน้าอ่าน bio+โพสต์แล้วเข้าใจใน 5 วินาทีไหมว่าขายอะไร ให้ใคร ทำไมต้องซื้อ
- presence: มีตัวตนกี่แพลตฟอร์ม สม่ำเสมอไหม
- content: คนชอบจริงไหม (engagement rate, like:view, shares) คอนเทนต์ตรง brand และ avatar ไหม
- target: avatar ของเขาคือใคร (เดาจากหลักฐาน หรือ hedge)
- competitor: ถ้ามีข้อมูลคู่แข่ง เทียบตรง ๆ (follower, engagement, ความชัดของ offer) ถ้าไม่มี วิเคราะห์ภาพรวมการแข่งขันใน niche แบบ low confidence
- international: niche นี้ในต่างประเทศทำกันยังไง เราห่างแค่ไหน"""


def _clamp(x, lo=1, hi=10) -> int:
    try:
        return max(lo, min(hi, int(x)))
    except (TypeError, ValueError):
        return lo


def _finalize(aspects: dict, overall: dict, metrics: dict, engine: str) -> dict:
    ordered = []
    for k in ASPECT_KEYS:
        a = aspects.get(k) or {}
        ordered.append({
            "key": k,
            "title_th": ASPECT_TITLES_TH[k],
            "score": _clamp(a.get("score", 4)),
            "headline": a.get("headline") or "",
            "detail": a.get("detail") or "",
            "evidence": [str(e) for e in (a.get("evidence") or [])][:5],
            "confidence": a.get("confidence") if a.get("confidence") in ("high", "medium", "low") else "low",
        })
    scores = [a["score"] for a in ordered]
    overall_score = _clamp(overall.get("score", round(sum(scores) / len(scores))))
    return {
        "business_name": (metrics.get("business") or {}).get("name"),
        "generated_at": int(time.time()),
        "data_quality": metrics.get("data_quality", "limited"),
        "engine": engine,
        "overall": {"score": overall_score, "summary": overall.get("summary") or ""},
        "aspects": ordered,
        "cta_url": config.CTA_URL,
    }


# ---------------------------------------------------------------- LLM scoring

def score_with_llm(metrics: dict) -> dict | None:
    """One cheap structured-output call. Returns None on any failure → caller falls back."""
    if not config.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=config.SCORING_MODEL,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": RESULT_SCHEMA}},
            messages=[{
                "role": "user",
                "content": (
                    "Fact sheet (ข้อมูลจริงที่ scrape มา + ข้อมูลที่เจ้าของกรอก):\n"
                    + json.dumps(metrics, ensure_ascii=False)
                    + "\n\nวิเคราะห์และให้คะแนนตามกติกาใน system prompt"
                ),
            }],
        )
        if response.stop_reason not in ("end_turn", "stop_sequence"):
            log.warning("LLM stop_reason=%s — falling back", response.stop_reason)
            return None
        text = next((b.text for b in response.content if b.type == "text"), None)
        if not text:
            return None
        data = json.loads(text)
        return _finalize(data["aspects"], data["overall"], metrics, engine="llm")
    except Exception as e:  # noqa: BLE001 — free tool: degrade, never crash
        log.warning("LLM scoring failed: %s", e)
        return None


# ---------------------------------------------------------- heuristic fallback

def _heuristic_aspects(m: dict) -> dict:
    ig, tt, comp = m.get("instagram"), m.get("tiktok"), m.get("competitor")
    best = next((p for p in (ig, tt) if p and p.get("found")), None)
    found = best is not None
    followers = (best or {}).get("followers") or 0
    bio = (best or {}).get("bio") or ""
    has_link = bool((best or {}).get("has_link_in_bio"))
    eng = (best or {}).get("engagement") or {}
    er = eng.get("engagement_rate_pct")

    def ev_followers():
        return [f"ผู้ติดตาม {followers:,} คน"] if followers else []

    disc = 2
    if found:
        disc = 4 + (1 if followers > 1000 else 0) + (1 if followers > 10000 else 0) \
             + (1 if bio else 0) + (1 if has_link else 0)
    read = 3 if not found else (5 if len(bio) > 30 else 4) + (1 if has_link else 0)

    prov = m.get("platforms_provided") or 1
    pres = {1: 3, 2: 5, 3: 6}.get(prov, 3) + min(m.get("platforms_found_by_scraper") or 0, 2)

    if er is None:
        cont = 4 if found else 3
        cont_ev = []
    elif er >= 3:
        cont, cont_ev = 7, [f"engagement rate เฉลี่ย {er}%"]
    elif er >= 1:
        cont, cont_ev = 5, [f"engagement rate เฉลี่ย {er}%"]
    else:
        cont, cont_ev = 3, [f"engagement rate เฉลี่ย {er}%"]

    comp_found = bool(comp and comp.get("found"))
    if comp_found:
        cf = comp.get("followers") or 0
        comp_score = 6 if followers >= cf else 3
        comp_ev = [f"คู่แข่งมีผู้ติดตาม {cf:,} คน เทียบกับคุณ {followers:,} คน"]
    else:
        comp_score, comp_ev = 5, []

    hedge = "ข้อมูลจากการสแกนมีจำกัด ประเมินเบื้องต้นจากข้อมูลที่กรอกมา — ผลละเอียดต้องตรวจเชิงลึก"
    limited = m.get("data_quality") == "limited"

    def note(txt_full: str, txt_limited: str | None = None) -> str:
        return (txt_limited or hedge) if limited else txt_full

    return {
        "discoverability": {
            "score": disc, "confidence": "medium" if found else "low",
            "headline": note("พอค้นเจอ แต่ยังไม่โดดเด่น", "ยังสแกนบัญชีไม่เจอ / เข้าถึงไม่ได้"),
            "detail": note(
                "บัญชีค้นเจอได้ แต่องค์ประกอบที่ทำให้คนแปลกหน้าหยุดดู (ชื่อ, bio, ลิงก์) ยังไม่ครบหรือยังไม่คม",
                "ระบบยังเข้าถึงข้อมูลบัญชีไม่ได้ (อาจเป็นบัญชีส่วนตัว/ใหม่/สะกดไม่ตรง) — คะแนนนี้เป็นการประเมินขั้นต่ำ"),
            "evidence": ev_followers() + ([f"bio: \"{bio[:80]}\""] if bio else []),
        },
        "readability": {
            "score": read, "confidence": "low",
            "headline": "ยังตอบไม่ได้ใน 5 วินาทีว่า ขายอะไร-ให้ใคร",
            "detail": note(
                "จาก bio และโพสต์ล่าสุด ยังต้องใช้เวลาตีความว่าธุรกิจขายอะไรให้ใคร — ลูกค้าส่วนใหญ่ไม่รอ",
                hedge),
            "evidence": [f"bio: \"{bio[:80]}\""] if bio else [],
        },
        "presence": {
            "score": min(pres, 10), "confidence": "medium",
            "headline": f"มีตัวตน {prov} แพลตฟอร์มจาก 3 หลัก",
            "detail": "ลูกค้าแต่ละกลุ่มอยู่คนละแพลตฟอร์ม การมีตัวตนที่สม่ำเสมอหลายช่องทางคือฐานของการถูกค้นเจอ",
            "evidence": [f"กรอก handle มา {prov} แพลตฟอร์ม"],
        },
        "content": {
            "score": cont, "confidence": "medium" if cont_ev else "low",
            "headline": note("คอนเทนต์มีคนดู แต่ยังไม่เปลี่ยนเป็นลูกค้า", "ยังวัด engagement จริงไม่ได้"),
            "detail": note(
                "ตัวเลข engagement บอกว่าคอนเทนต์พอไปได้ แต่ยังไม่เห็นสัญญาณว่าคนดูกลายเป็นคนซื้อ",
                hedge),
            "evidence": cont_ev,
        },
        "target": {
            "score": 4, "confidence": "low",
            "headline": "กลุ่มเป้าหมายยังเบลอ",
            "detail": f"จากที่กรอกมา คุณอยากขายให้ \"{(m.get('business') or {}).get('sell_to', '')}\" "
                      "แต่คอนเทนต์ที่สแกนได้ยังไม่สะท้อนว่าพูดกับคนกลุ่มนี้ชัด ๆ — ต้องวิเคราะห์เชิงลึกเพื่อยืนยัน avatar",
            "evidence": [],
        },
        "competitor": {
            "score": comp_score, "confidence": "medium" if comp_found else "low",
            "headline": "คู่แข่งขยับเร็วกว่าในสนามคอนเทนต์" if comp_found else "ยังไม่มีข้อมูลคู่แข่งตรง ๆ",
            "detail": ("เทียบตัวเลขเบื้องต้น คู่แข่งที่คุณระบุมามีฐานผู้ติดตามและความสม่ำเสมอที่วัดได้ "
                       "— ช่องว่างนี้ปิดได้ แต่ต้องรู้ว่าเขาทำอะไรถูก" if comp_found else
                       "ยังไม่ได้ระบุ/สแกนคู่แข่งไม่ได้ ประเมินจากภาพรวมการแข่งขันใน niche เท่านั้น"),
            "evidence": comp_ev,
        },
        "international": {
            "score": 4, "confidence": "low",
            "headline": "ยังห่างจากมาตรฐานที่ niche นี้ทำกันในต่างประเทศ",
            "detail": "เป็น benchmark จากแนวปฏิบัติสากลของธุรกิจประเภทนี้ (ไม่ใช่ข้อมูลที่สแกนมา): "
                      "แบรนด์ต่างประเทศใน niche เดียวกันมักมี offer ชัดใน bio, คอนเทนต์เป็นซีรีส์, และ CTA ทุกโพสต์",
            "evidence": [],
        },
    }


def score_with_heuristic(metrics: dict) -> dict:
    aspects = _heuristic_aspects(metrics)
    scores = [a["score"] for a in aspects.values()]
    overall = {
        "score": round(sum(scores) / len(scores)),
        "summary": "ผลตรวจเบื้องต้น: มีหลายหัวข้อที่ยังต่ำกว่าเกณฑ์และมีช่องว่างให้ปรับอีกมาก "
                   "ผลนี้ประเมินจากสัญญาณที่วัดได้อัตโนมัติ — การเจาะว่าต้องแก้ตรงไหนก่อนต้องดูกันตัวต่อตัว",
    }
    return _finalize(aspects, overall, metrics, engine="heuristic")


def score(metrics: dict) -> dict:
    return score_with_llm(metrics) or score_with_heuristic(metrics)
