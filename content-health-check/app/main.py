"""Biz Content Health Check — free lead-magnet MVP (Content Clinic, Offer Ladder FREE rung).

Loop: input (lead capture) → scrape → score → gated result → soft CTA to ฿5k audit.
"""
import logging
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import config, db, metrics, scoring, scraper
from .schemas import CheckupRequest

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("chc")

app = FastAPI(title="Biz Content Health Check", docs_url=None, redoc_url=None)

STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _process_run(run_id: str, form: dict) -> None:
    """Background pipeline. Any failure → error state with a usable message, never a hang."""
    try:
        db.update_run(run_id, status="scraping")
        bundle = scraper.scrape_all(
            form.get("ig_handle"), form.get("fb_handle"),
            form.get("tiktok_handle"), form.get("competitor_handle"),
        )
        fact_sheet = metrics.build_metrics(bundle, form)
        db.update_run(run_id, status="scoring", data_quality=fact_sheet["data_quality"])
        result = scoring.score(fact_sheet)
        db.update_run(run_id, status="done", result=result)
    except Exception as e:  # noqa: BLE001 — last-resort net; degrade to heuristic-on-empty
        log.exception("run %s failed hard, serving minimal result", run_id)
        try:
            fact_sheet = metrics.build_metrics(
                {"instagram": None, "tiktok": None, "facebook_presence": bool(form.get("fb_handle")),
                 "competitor": None, "errors": ["pipeline_error"]},
                form,
            )
            result = scoring.score_with_heuristic(fact_sheet)
            db.update_run(run_id, status="done", data_quality="limited", result=result)
        except Exception:  # noqa: BLE001
            db.update_run(run_id, status="error", error=str(e))


@app.post("/api/checkup")
async def create_checkup(request: Request, background: BackgroundTasks):
    try:
        payload = await request.json()
        form = CheckupRequest(**payload)
    except ValidationError as e:
        msgs = [err.get("msg", "invalid") for err in e.errors()][:3]
        return JSONResponse(status_code=422, content={"detail": "; ".join(msgs)})
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "invalid request"})

    ip = _client_ip(request)
    if db.count_runs_by_ip_today(ip) >= config.RATE_LIMIT_PER_IP_PER_DAY:
        return JSONResponse(
            status_code=429,
            content={"detail": "วันนี้ตรวจครบโควต้าแล้ว ลองใหม่พรุ่งนี้ หรือทักหาเราทาง LINE ได้เลย"},
        )

    # Lead is captured FIRST — even if scraping later fails, we keep the market data.
    form_dict = form.model_dump()
    lead_id = db.create_lead(form_dict, ip=ip, user_agent=request.headers.get("user-agent", "")[:300])
    run_id = db.create_run(lead_id, form.primary_handle)

    # Cost control: same handle checked recently → reuse the cached result.
    cached = db.find_cached_result(form.primary_handle)
    if cached:
        db.update_run(run_id, status="done", data_quality=cached["data_quality"],
                      result=cached["result"])
    else:
        background.add_task(_process_run, run_id, form_dict)

    return {"run_id": run_id}


@app.get("/api/checkup/{run_id}")
def get_checkup(run_id: str):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="not found")
    out = {"run_id": run_id, "status": run["status"], "data_quality": run.get("data_quality")}
    if run["status"] == "done":
        out["result"] = run.get("result")
    if run["status"] == "error":
        out["detail"] = "ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้ง"
    return out


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "scraper_configured": bool(config.APIFY_TOKEN),
        "llm_configured": bool(config.ANTHROPIC_API_KEY),
        "model": config.SCORING_MODEL,
    }


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
