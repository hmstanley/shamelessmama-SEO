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

---

## Configuration (start here)

All configuration lives in two JSON files in the `config/` folder. No Python editing required.

### `config/keywords.json` — tracked keywords

| List | Used by | Notes |
|------|---------|-------|
| `rankings` | `seo_monitor.py` | Keywords checked for Google position daily. Brand terms fine here. |
| `competitor_analysis` | `competitor_monitor.py` | Keywords used to find and benchmark competitors. Each one costs a Serper credit per run — keep this list focused. |

Add or remove entries from either list, save the file, and the next run picks up the changes automatically.

---

### `config/settings.json` — everything else

#### Blocked domains (`directory_domains`)
Sites suppressed everywhere — competitor tables, keyword spy, dashboard display. Add any domain you never want to see:
```json
"directory_domains": [
  "psychologytoday.com",
  "yelp.com",
  "talkspace.com"
]
```

#### Pinned competitors (`pinned_competitors`)
Domains you always want to spy on, regardless of whether they appear in search results that week. These are your known direct competitors:
```json
"pinned_competitors": [
  "bloomtherapysf.com",
  "mccartneytherapy.com"
]
```
- Pinned competitors fill slots first, then auto-discovered competitors fill the rest up to `max_competitors`
- If you pin more domains than `max_competitors` allows, raise `max_competitors` too
- A domain in both `pinned_competitors` and `directory_domains` is silently skipped

#### Competitor spy tuning (`competitor_spy`)

| Setting | Default | What it controls |
|---------|---------|-----------------|
| `max_competitors` | 8 | Total competitor domains to crawl per run (pinned + discovered) |
| `max_pages_per_competitor` | 50 | Max pages to scan from each competitor's sitemap |
| `max_keyword_words` | 6 | Max words kept from a URL slug — prevents long blog titles becoming noisy keywords |
| `skip_segments` | *(list)* | URL path words that identify non-content pages (about, faq, contact, etc.) — add words to filter junk |
| `credential_words` | *(list)* | Words that identify therapist bio/staff pages (lmft, lcsw, phd, etc.) — keeps people pages out of keyword results |
| `stop_words` | *(list)* | Common words stripped before keyword matching |

---

## Monitor Scripts

| Script | What it does |
|--------|-------------|
| `monitor/run_daily.py` | Orchestrates all monitors, writes `daily_digest.json` |
| `monitor/seo_monitor.py` | Keyword ranking checks via Serper |
| `monitor/competitor_monitor.py` | SERP competitor analysis, authority scores, keyword gap report |
| `monitor/competitor_keyword_spy.py` | Sitemap crawl of pinned + discovered competitors, keyword extraction, page matching |
| `monitor/gsc_monitor.py` | Google Search Console weekly trends and quick wins |
| `monitor/site_audit.py` | Technical SEO health (schema, meta, page speed) |
| `monitor/email_monitor.py` | iCloud IMAP digest for Marilyn's inbox |
| `monitor/amazon_monitor.py` | Amazon order history via Playwright |
| `monitor/gsc_auth.py` | OAuth2 helper for GSC API (run once to authenticate) |
| `monitor/content_brief.py` | Blog topic and content brief generator |

---

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

**PDF Export:** say `export PDF` → a styled HTML file is saved to `~/Desktop` → open in Chrome or Safari → Cmd+P → Save as PDF.

> Note: after editing `seo_pipe.py`, re-push to Open WebUI via Admin → Functions → paste updated code, or re-run the API push script.

---

## Data Files (dashboard/data/)

These are written automatically by the monitor scripts. Do not edit manually.

| File | Written by |
|------|-----------|
| `rankings.json` | `seo_monitor.py` |
| `competitors.json` | `competitor_monitor.py` |
| `keyword_gap.json` | `competitor_monitor.py` |
| `competitor_keywords.json` | `competitor_keyword_spy.py` |
| `gsc.json` | `gsc_monitor.py` |
| `audit.json` | `site_audit.py` |
| `daily_digest.json` | `run_daily.py` |

---

## Setup

```bash
pip install -r requirements.txt

# GSC auth (one-time browser login)
python monitor/gsc_auth.py

# Run everything manually
python monitor/run_daily.py
```

**API keys required:**

| Key | Where to put it | Used by |
|-----|----------------|---------|
| Serper.dev | `.serperAPI` in repo root | `seo_monitor.py`, `competitor_monitor.py` |
| Open PageRank | `~/.openpagerank-api-key` | `competitor_monitor.py` |
| Amazon cookies | `~/.amazon_cookies.json` | `amazon_monitor.py` — export from Cookie-Editor at amazon.com/gp/css/order-history |

---

## Automation (launchd)

`com.shamelessmama.seo.plist` runs `run_daily.py` at **7am and 3pm** daily on the HomeAI Mac.

```bash
cp com.shamelessmama.seo.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.shamelessmama.seo.plist
```
