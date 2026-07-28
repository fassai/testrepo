"""Central config — everything overridable via env so the free tool stays cheap to run."""
import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "").strip()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

# Fast/cheap model on purpose: free lead magnet, abuse-prone surface.
SCORING_MODEL = os.environ.get("SCORING_MODEL", "claude-haiku-4-5").strip()

RATE_LIMIT_PER_IP_PER_DAY = _int("RATE_LIMIT_PER_IP_PER_DAY", 5)
CACHE_TTL_HOURS = _int("CACHE_TTL_HOURS", 24)
SCRAPE_TIMEOUT_SECONDS = _int("SCRAPE_TIMEOUT_SECONDS", 90)

CTA_URL = os.environ.get("CTA_URL", "https://lin.ee/REPLACE_ME").strip()

DB_PATH = os.environ.get("DB_PATH", "./health_check.db").strip()
