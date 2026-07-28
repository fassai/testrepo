"""SQLite storage.

Every run captures the lead + their raw inputs — this doubles as market-research
data (who wants the audit, what niches, who they think their competitors are).
"""
import json
import sqlite3
import threading
import time
import uuid

from . import config

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db() -> None:
    with _lock:
        c = get_conn()
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                created_at INTEGER NOT NULL,
                name TEXT NOT NULL,
                business_name TEXT NOT NULL,
                sell_to TEXT NOT NULL,
                industry TEXT NOT NULL,
                ig_handle TEXT,
                fb_handle TEXT,
                tiktok_handle TEXT,
                competitor_handle TEXT,
                email TEXT,
                line_id TEXT,
                ip TEXT,
                user_agent TEXT
            );
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL REFERENCES leads(id),
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                status TEXT NOT NULL,            -- queued | scraping | scoring | done | error
                data_quality TEXT,               -- full | partial | limited
                primary_handle TEXT,             -- for result caching / dedup
                result_json TEXT,
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_leads_ip ON leads(ip, created_at);
            CREATE INDEX IF NOT EXISTS idx_runs_handle ON runs(primary_handle, created_at);
            """
        )
        c.commit()


def create_lead(data: dict, ip: str, user_agent: str) -> str:
    lead_id = uuid.uuid4().hex
    with _lock:
        c = get_conn()
        c.execute(
            """INSERT INTO leads (id, created_at, name, business_name, sell_to, industry,
                 ig_handle, fb_handle, tiktok_handle, competitor_handle, email, line_id, ip, user_agent)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                lead_id, int(time.time()),
                data["name"], data["business_name"], data["sell_to"], data["industry"],
                data.get("ig_handle"), data.get("fb_handle"), data.get("tiktok_handle"),
                data.get("competitor_handle"), data.get("email"), data.get("line_id"),
                ip, user_agent,
            ),
        )
        c.commit()
    return lead_id


def create_run(lead_id: str, primary_handle: str) -> str:
    run_id = uuid.uuid4().hex
    now = int(time.time())
    with _lock:
        c = get_conn()
        c.execute(
            "INSERT INTO runs (id, lead_id, created_at, updated_at, status, primary_handle) VALUES (?,?,?,?,?,?)",
            (run_id, lead_id, now, now, "queued", primary_handle.lower()),
        )
        c.commit()
    return run_id


def update_run(run_id: str, *, status: str | None = None, data_quality: str | None = None,
               result: dict | None = None, error: str | None = None) -> None:
    sets, vals = ["updated_at=?"], [int(time.time())]
    if status is not None:
        sets.append("status=?"); vals.append(status)
    if data_quality is not None:
        sets.append("data_quality=?"); vals.append(data_quality)
    if result is not None:
        sets.append("result_json=?"); vals.append(json.dumps(result, ensure_ascii=False))
    if error is not None:
        sets.append("error=?"); vals.append(error[:500])
    vals.append(run_id)
    with _lock:
        c = get_conn()
        c.execute(f"UPDATE runs SET {', '.join(sets)} WHERE id=?", vals)
        c.commit()


def get_run(run_id: str) -> dict | None:
    with _lock:
        row = get_conn().execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("result_json"):
        d["result"] = json.loads(d["result_json"])
    return d


def count_runs_by_ip_today(ip: str) -> int:
    day_ago = int(time.time()) - 86400
    with _lock:
        row = get_conn().execute(
            "SELECT COUNT(*) AS n FROM leads WHERE ip=? AND created_at>=?", (ip, day_ago)
        ).fetchone()
    return int(row["n"])


def find_cached_result(primary_handle: str) -> dict | None:
    """Same handle scored recently → reuse (cost control: free tool, repeat/viral traffic)."""
    cutoff = int(time.time()) - config.CACHE_TTL_HOURS * 3600
    with _lock:
        row = get_conn().execute(
            """SELECT result_json, data_quality FROM runs
               WHERE primary_handle=? AND status='done' AND created_at>=? AND result_json IS NOT NULL
               ORDER BY created_at DESC LIMIT 1""",
            (primary_handle.lower(), cutoff),
        ).fetchone()
    if not row:
        return None
    return {"result": json.loads(row["result_json"]), "data_quality": row["data_quality"]}
