# Biz Content Health Check — free lead-magnet MVP

The FREE rung of the Content Clinic offer ladder (DB0 · Toggle 4).
A business owner enters their name + business + niche + who they sell to +
social handle(s) (+ competitor handle = the viral hook), leaves email/LINE,
and gets a **BMI-style health printout**: 7 aspect scores (1–10) grounded in
real scraped signals, ending in a soft CTA to the ฿5,000 1-1 Online Audit.

## The loop

```
input (lead capture, gated) → APIFY scrape (IG/TikTok + competitor IG)
→ deterministic metrics (facts) → LLM scoring (claude-haiku-4-5, structured JSON)
→ health printout (Thai, mobile-first) → soft CTA → lead + inputs stored (market research)
```

## Run it

```bash
cd content-health-check
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill APIFY_TOKEN + ANTHROPIC_API_KEY + CTA_URL
set -a; source .env; set +a
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 — mobile-first, QR-friendly, no install.

## Graceful degradation (by design — never crash, never confidently wrong)

| Situation | Behavior |
|---|---|
| No `APIFY_TOKEN` / scrape fails / private account | Runs in **limited data** mode: scores still produced, hedged, flagged "ข้อมูลจำกัด" |
| No `ANTHROPIC_API_KEY` / LLM error / refusal | Deterministic **heuristic scores** from the metric fact sheet |
| Same handle re-checked within `CACHE_TTL_HOURS` | Cached result reused (cost + abuse control) |
| IP over `RATE_LIMIT_PER_IP_PER_DAY` | 429 with a friendly Thai message |

Every AI claim must cite a scraped signal (`evidence[]`) or carry
`confidence: low` + hedged wording — a confidently-wrong guess about the
owner's own business kills trust instantly, so the system prompt forbids it.

## Cost per run (approx, 2026-07)

- LLM: ~2.5–4K input + ~2K output tokens on `claude-haiku-4-5` ($1/$5 per MTok) ≈ **$0.01–0.015**
- Apify: 2–3 profile scrapes (IG own + competitor + TikTok) ≈ **$0.01–0.05** depending on actor pricing
- Total ≈ **฿0.7–2.5 per run**, cached repeats ≈ ฿0

## Data captured (market research)

`leads` table: name, business, sell-to, industry, handles, competitor handle,
email/LINE, IP, UA. `runs` table: status, data quality, full scored result.
SQLite (`DB_PATH`) — swap for Postgres when it outgrows one box.

## Deliberately NOT built (per DB0 scope)

Paid audit flow · payment · score→fix engine · CCH integration · FB deep
scraping (login-walled + expensive → FB counts toward presence only).
