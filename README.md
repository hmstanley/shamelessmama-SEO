# Shameless Mama Wellness — SEO Monitor

Agentic SEO monitoring for [shamelessmamawellness.com](https://www.shamelessmamawellness.com)

## What This Does

- Tracks keyword rankings daily across search engines
- Monitors website technical health (schema, page speed, crawl errors)
- Checks directory listings (Psychology Today, Healthgrades, Google Business Profile)
- Generates a simple browser-based dashboard Marilyn can open each morning
- Suggests blog topics based on trending searches in the perinatal mental health space

## Docs (Start Here)

- [`docs/executive-summary.md`](docs/executive-summary.md) — Big picture: what's working, what's not, what the impact is
- [`docs/what-to-fix.md`](docs/what-to-fix.md) — Step-by-step non-technical fix guide for Marilyn

## Dashboard

Open `dashboard/index.html` in any browser — no installation required.

## Scripts (for automation)

- `monitor/seo_monitor.py` — Daily keyword ranking checks
- `monitor/site_audit.py` — Technical SEO health check
- `monitor/keyword_suggestions.py` — Trending topic suggestions
- `monitor/run_all.py` — Runs everything and updates dashboard data

## Setup

```bash
pip install -r requirements.txt
python monitor/run_all.py
# Then open dashboard/index.html in your browser
```

## Target Keywords Being Tracked

| Keyword | Target Position |
|---------|----------------|
| Birth trauma therapist San Francisco | Top 3 |
| Postpartum therapist San Francisco Bay Area | Top 5 |
| EMDR therapist moms California | Top 5 |
| Postpartum depression therapist California | Top 5 |
| Prenatal therapist San Francisco | Top 3 |
| EMDR intensive birth trauma | Top 3 |
| Perinatal mental health therapist California | Top 5 |
| Birth trauma therapist online California | Top 3 |
| Postpartum anxiety therapist Bay Area | Top 5 |
| Mother wound therapist California | Top 3 |
