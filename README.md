# Shameless Mama Wellness — SEO Monitor

Agentic SEO monitoring for [shamelessmamawellness.com](https://www.shamelessmamawellness.com)

## What This Does

- Tracks keyword rankings daily via Serper.dev
- Monitors technical site health (schema, meta tags, page speed signals)
- Pulls Google Search Console data (clicks, impressions, position trends, quick wins)
- Analyzes competitor landscape with authority scores and difficulty ratings
- Reverse-engineers competitor keyword targets via sitemap crawl and matches them against our pages
- Generates keyword gap reports (gaps, improvements, wins, new keyword opportunities)
- Surfaces all findings in a live chat dashboard via Open WebUI
- Exports the full dashboard to a print-ready HTML file (PDF via browser print)
- Runs automatically at 7am and 3pm via launchd

## Monitor Scripts

| Script | What it does |
|--------|-------------|
| `monitor/run_daily.py` | Orchestrates all monitors, writes `daily_digest.json` |
| `monitor/seo_monitor.py` | Keyword ranking checks via Serper |
| `monitor/competitor_monitor.py` | SERP competitor analysis, authority scores, keyword gap report |
| `monitor/competitor_keyword_spy.py` | Sitemap crawl of top competitors, keyword extraction, page matching |
| `monitor/gsc_monitor.py` | Google Search Console weekly trends and quick wins |
| `monitor/site_audit.py` | Technical SEO health (schema, meta, page speed) |
| `monitor/email_monitor.py` | iCloud IMAP digest for Marilyn's inbox |
| `monitor/amazon_monitor.py` | Amazon order history via Playwright |
| `monitor/gsc_auth.py` | OAuth2 helper for GSC API |
| `monitor/content_brief.py` | Blog topic and content brief generator |

## Open WebUI Dashboard (seo_pipe.py)

The dashboard runs as a pipe inside [Home AI](http://192.168.1.197:8080) (Open WebUI). Trigger it by typing any of:

> `SEO dashboard` · `show my rankings` · `keyword gap` · `competitor keywords` · `what needs fixing` · `export PDF`

**Sections:**
- 📊 Google Search Console — weekly clicks, impressions, position, quick wins
- 🔑 Keyword Rankings — position + week-over-week change for all tracked keywords
- 🏆 Competitor Landscape — real competitors only (directories filtered), authority scores, difficulty ratings
- 🎯 Keyword Gap Analysis — gaps, improvements, wins with specific action recommendations
- 🔍 Competitor Keyword Intelligence — keywords competitors rank for, matched against our pages (❌ gap · 🟡 partial · ✅ covered)
- 🏥 Site Health — per-page technical issues
- 📄 Top Pages — last 28 days from GSC
- 🔧 Fix List — prioritized action items

**PDF Export:** say `export PDF` → opens a styled HTML file on `~/Desktop` → open in browser → Cmd+P → Save as PDF.

## Data Files (dashboard/data/)

| File | Written by |
|------|-----------|
| `rankings.json` | `seo_monitor.py` |
| `competitors.json` | `competitor_monitor.py` |
| `keyword_gap.json` | `competitor_monitor.py` |
| `competitor_keywords.json` | `competitor_keyword_spy.py` |
| `gsc.json` | `gsc_monitor.py` |
| `audit.json` | `site_audit.py` |
| `daily_digest.json` | `run_daily.py` |

## Configuration — What to Edit and Where

### Add or remove tracked keywords

Keywords live in **two separate files** — keep them in sync.

**`monitor/seo_monitor.py` — `KEYWORDS` list (~line 22)**
Rankings are checked for these. Add/remove strings from the list.

**`monitor/competitor_monitor.py` — `KEYWORDS` list (~line 28)**
These drive the competitor SERP analysis and keyword gap report. Same format — one string per line.

---

### Block a domain from appearing in the competitor dashboard

Three files share a `DIRECTORY_DOMAINS` set. Add the domain to all three to fully suppress it:

- `monitor/competitor_monitor.py` — `DIRECTORY_DOMAINS` (~line 40)
- `monitor/competitor_keyword_spy.py` — `DIRECTORY_DOMAINS` (~line 28)
- `monitor/seo_pipe.py` — `DIRECTORY_DOMAINS` (~line 28)

---

### Competitor keyword spy settings

All in `monitor/competitor_keyword_spy.py`:

| Constant | Line | What it controls |
|----------|------|-----------------|
| `MAX_COMPETITORS` | ~54 | How many competitor domains to crawl (default: 8) |
| `MAX_PAGES_PER_COMPETITOR` | ~53 | Max pages to scan per competitor (default: 50) |
| `SKIP_SEGMENTS` | ~41 | URL path words that mark non-content pages (about, contact, faq, etc.) — add words here to filter out junk pages |
| `CREDENTIAL_WORDS` | ~50 | Words that identify therapist bio/staff pages (lmft, lcsw, phd, etc.) |
| `MAX_KEYWORD_WORDS` | ~52 | Max words kept from a URL slug — prevents long blog titles becoming noisy keywords (default: 6) |

---

### Dashboard chat triggers

In `monitor/seo_pipe.py`:

- **`TRIGGERS`** (~line 16) — phrases that show the full dashboard in chat
- **`EXPORT_TRIGGERS`** (~line 23) — phrases that generate the PDF export file

After editing `seo_pipe.py`, push it to Open WebUI:
```bash
python3 monitor/push_pipe.py   # or re-paste via Admin → Functions
```

---

### API keys

| Key | Location | Used by |
|-----|----------|---------|
| Serper.dev | `.serperAPI` in repo root | `seo_monitor.py`, `competitor_monitor.py` |
| Open PageRank | `~/.openpagerank-api-key` | `competitor_monitor.py` |
| Amazon cookies | `~/.amazon_cookies.json` | `amazon_monitor.py` |

---

## Setup

```bash
pip install -r requirements.txt

# GSC auth (one-time)
python monitor/gsc_auth.py

# Run everything manually
python monitor/run_daily.py
```

API keys required:
- `.serperAPI` in repo root — Serper.dev key
- `~/.openpagerank-api-key` — Open PageRank key
- `~/.amazon_cookies.json` — exported from Cookie-Editor at amazon.com/gp/css/order-history

## Automation (launchd)

`com.shamelessmama.seo.plist` runs `run_daily.py` at **7am and 3pm** daily.

```bash
cp com.shamelessmama.seo.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.shamelessmama.seo.plist
```

## Target Keywords

| Keyword | Target Position |
|---------|----------------|
| Birth trauma therapist San Francisco | Top 3 |
| Postpartum therapist San Francisco Bay Area | Top 5 |
| EMDR therapist moms California | Top 5 |
| Postpartum depression therapist California | Top 5 |
| Prenatal therapist San Francisco | Top 3 |
| Perinatal mental health therapist California | Top 5 |
| Birth trauma therapist online California | Top 3 |
| Postpartum anxiety therapist Bay Area | Top 5 |
| Mother wound therapist California | Top 3 |
