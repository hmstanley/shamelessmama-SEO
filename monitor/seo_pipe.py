"""
title: SEO Dashboard — Shameless Mama Wellness
author: HomeAI
description: Live SEO dashboard for shamelessmamawellness.com. Triggers on 'SEO report', 'what's new today', 'show my rankings', 'quick wins', 'what needs fixing', 'site health', 'keyword rankings', 'seo dashboard', 'daily digest'.
version: 0.7.0
"""

import json
import os
import datetime
from pydantic import BaseModel, Field

DATA_DIR = "/Users/Will.Coleman/shamelessmama-SEO/dashboard/data"
SERPER_KEY = "5e92a651e8cedbf894e75d55e447a1f92396beb6"

TRIGGERS = [
    "seo report", "seo dashboard", "show my rankings", "keyword rankings",
    "what needs fixing", "site health", "what's new today", "daily digest",
    "quick wins", "gsc", "search console", "competitors", "competition",
    "keyword gap", "gap analysis", "competitor keywords", "keyword spy",
    "export pdf", "export dashboard", "save pdf", "download dashboard", "print dashboard",
]

EXPORT_TRIGGERS = {
    "export pdf", "export dashboard", "save pdf", "download dashboard", "print dashboard",
}

DIRECTORY_DOMAINS = {
    "psychologytoday.com", "zencare.co", "therapyden.com", "yelp.com",
    "zocdoc.com", "healthgrades.com", "therapistfinder.com", "betterhelp.com",
    "talkspace.com", "goodtherapy.org", "psychology.com", "therapist.com",
    "findatherapist.com", "therapyroute.com",
}


class Pipe:
    class Valves(BaseModel):
        serper_api_key: str = Field(default=SERPER_KEY, description="Serper.dev API key")

    def __init__(self):
        self.valves = self.Valves()

    def _is_triggered(self, message: str) -> bool:
        msg = message.lower()
        return any(t in msg for t in TRIGGERS)

    def _load(self, filename):
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None

    def _pos_emoji(self, pos):
        if pos is None:
            return "⚫"
        if pos <= 3:
            return "🟢"
        if pos <= 10:
            return "🟡"
        return "🔴"

    def _change_str(self, diff):
        if diff is None:
            return "—"
        if diff > 0:
            return f"⬆️ +{diff}"
        if diff < 0:
            return f"⬇️ {diff}"
        return "➡️ same"

    def _pct_str(self, val, invert=False):
        """Format a percentage change with up/down arrow."""
        if val is None:
            return ""
        good = (val > 0) if not invert else (val < 0)
        arrow = "⬆️" if val > 0 else "⬇️"
        return f"{arrow} {abs(val)}%"

    def _difficulty_emoji(self, label):
        return {
            "Beatable now": "✅",
            "Competitive":  "🟡",
            "Hard":         "🔴",
            "Dominant":     "⚫",
            "Unknown":      "❓",
        }.get(label, "❓")

    # ── Section builders ──────────────────────────────────────────

    def _build_gsc_section(self, gsc):
        if not gsc:
            return "_No GSC data yet — run `python monitor/run_daily.py` to fetch._\n"

        trend     = gsc.get("weekly_trend", {})
        this_week = trend.get("this_week", {})
        last_week = trend.get("last_week", {})
        clicks    = this_week.get("clicks", 0)
        imp       = this_week.get("impressions", 0)
        pos       = this_week.get("position", 0)
        pos_chg   = trend.get("position_change", 0)
        pos_note  = f"⬆️ improved {abs(pos_chg)} spots" if pos_chg < 0 else f"⬇️ dropped {pos_chg} spots" if pos_chg > 0 else "➡️ no change"

        lines = [
            f"| Metric | This Week | vs Last Week |",
            f"|---|---|---|",
            f"| Clicks | **{clicks}** | vs {last_week.get('clicks', 0)}  {self._pct_str(trend.get('clicks_change_pct'))} |",
            f"| Impressions | **{imp:,}** | vs {last_week.get('impressions', 0):,}  {self._pct_str(trend.get('impressions_change_pct'))} |",
            f"| Avg Position | **{pos}** | vs {last_week.get('position', 0)}  {pos_note} |",
            "",
        ]

        quick_wins = gsc.get("quick_wins", [])
        if quick_wins:
            lines.append("**⚡ Quick Wins — You're showing up, but people aren't clicking:**")
            lines.append("_Fixing your page title and description for these searches could increase clicks significantly — no ranking change needed._")
            lines.append("")
            lines.append("| Search Query | Impressions | Position | CTR |")
            lines.append("|---|---|---|---|")
            for q in quick_wins:
                lines.append(f"| {q['query']} | {q['impressions']:,} | {self._pos_emoji(int(q['position']))} #{q['position']} | 🔴 {q['ctr']}% |")

        return "\n".join(lines)

    def _build_top_pages_section(self, gsc):
        if not gsc:
            return "_No data yet._\n"
        top_pages = gsc.get("top_pages", [])[:8]
        if not top_pages:
            return "_No page data yet._\n"
        lines = ["| Page | Clicks | Impressions | CTR |", "|---|---|---|---|"]
        for p in top_pages:
            slug = p["page"].replace("https://www.shamelessmamawellness.com", "") or "/"
            short = slug[:55] + "…" if len(slug) > 55 else slug
            ctr_icon = "🟢" if p["ctr"] >= 3 else "🟡" if p["ctr"] >= 1 else "🔴"
            lines.append(f"| {short} | {p['clicks']} | {p['impressions']:,} | {ctr_icon} {p['ctr']}% |")
        return "\n".join(lines)

    def _build_rankings_section(self, rankings):
        if not rankings:
            return "_No ranking data yet — run `python monitor/run_daily.py` to fetch._\n"

        r       = rankings.get("rankings", {})
        updated = rankings.get("last_updated", "")[:10]

        history_file = os.path.join(DATA_DIR, "rankings_history.json")
        prev = {}
        if os.path.exists(history_file):
            try:
                with open(history_file) as f:
                    history = json.load(f)
                if len(history) >= 2:
                    prev = history[-2].get("rankings", {})
            except Exception:
                pass

        lines = [f"_Last checked: {updated}_", ""]
        lines.append("| Keyword | Position | Change |")
        lines.append("|---|---|---|")

        for keyword, data in r.items():
            pos      = data.get("position")
            prev_pos = prev.get(keyword)
            diff     = (prev_pos - pos) if (prev_pos and pos) else None
            pos_str  = f"{self._pos_emoji(pos)} #{pos}" if pos else "⚫ Not ranked"
            kw_label = f"**{keyword}**" if (pos and pos <= 10) else keyword
            lines.append(f"| {kw_label} | {pos_str} | {self._change_str(diff)} |")

        lines.append("")
        lines.append("🟢 Top 3  ·  🟡 4–10  ·  🔴 11+  ·  ⚫ Not ranked")
        return "\n".join(lines)

    def _build_competitor_section(self, competitors):
        if not competitors:
            return "_No competitor data yet — run `python monitor/run_daily.py` to fetch._\n"

        target_score = competitors.get("target_authority_score")
        lines = []

        if target_score:
            bar = "█" * int(target_score) + "░" * (10 - int(target_score))
            lines.append(f"**Your Site's Authority: {target_score}/10** `{bar}`")
            lines.append("_This score shows how much Google trusts your site based on links from other reputable websites. It grows over time as you earn more directory listings, blog mentions, and backlinks. Most individual competitors score under 3/10 — you're already competitive._")
            lines.append("")

        for kw_data in competitors.get("keywords", []):
            keyword    = kw_data["keyword"]
            target_pos = kw_data.get("target_position")
            comps      = [c for c in kw_data.get("competitors", []) if not c.get("is_directory")]
            if not comps:
                continue

            pos_str = f"you rank #{target_pos}" if target_pos else "not in top 10"
            lines.append(f"**{keyword}** — {pos_str}")
            lines.append("| # | Competitor | Authority | Difficulty | What this means |")
            lines.append("|---|---|---|---|---|")
            for c in comps:
                score = c.get("authority_score")
                score_str = f"{score}/10" if score is not None else "n/a"
                diff  = c.get("difficulty", "Unknown")
                emoji = self._difficulty_emoji(diff)
                explanation = c.get("difficulty_explanation", "")
                lines.append(f"| {c['position']} | {c['domain']} | {score_str} | {emoji} {diff} | {explanation} |")
            lines.append("")

        lines.append("✅ Beatable now  ·  🟡 Competitive  ·  🔴 Hard  ·  ⚫ Dominant")
        return "\n".join(lines)

    def _build_health_section(self, audit):
        if not audit:
            return "_No audit data yet — run `python monitor/run_daily.py` to fetch._\n"

        lines = []
        for path, data in audit.get("pages", {}).items():
            issues = data.get("issues", [])
            label  = "Homepage" if path == "/" else path.split("/")[-1].replace("-", " ").title()
            if issues:
                lines.append(f"- **⚠️ {label}**")
                for issue in issues:
                    lines.append(f"    - {issue}")
            else:
                lines.append(f"- ✅ **{label}** — no issues")

        return "\n".join(lines) if lines else "✅ No issues found on any page"

    def _build_fix_list(self, audit, gsc):
        critical, important, nice = [], [], []

        if audit:
            for path, data in audit.get("pages", {}).items():
                for issue in data.get("issues", []):
                    clean = issue.lstrip("❌🔴⚠️ ")
                    if "❌" in issue or "🔴" in issue:
                        critical.append(clean) if (path == "/" or "homepage" in path.lower()) else important.append(clean)
                    elif "⚠️" in issue:
                        important.append(clean) if ("meta description" in issue.lower() or "h1" in issue.lower()) else nice.append(clean)

        if gsc:
            wins = gsc.get("quick_wins", [])
            if wins:
                top = wins[0]
                important.append(
                    f'Your title/description for "{top["query"]}" isn\'t compelling — '
                    f'{top["impressions"]:,} impressions, only {top["ctr"]}% CTR. '
                    f'In Squarespace → Pages → SEO, rewrite the description to directly address what someone searching this needs.'
                )

        # Psychology Today directory check — only flag if it's actually down
        if audit:
            pt = audit.get("directories", {}).get("Psychology Today", {})
            if pt and not pt.get("reachable"):
                critical.append(
                    "Your Psychology Today profile isn't loading correctly — check that your listing is still active at psychologytoday.com."
                )

        lines = []
        if critical:
            lines.append("**🚨 Critical — fix these first:**")
            for item in critical[:5]:
                lines.append(f"- {item}")
            lines.append("")
        if important:
            lines.append("**⚠️ Important:**")
            for item in important[:5]:
                lines.append(f"- {item}")
            lines.append("")
        if nice:
            lines.append("**💡 Nice to Have:**")
            for item in nice[:3]:
                lines.append(f"- {item}")

        return "\n".join(lines) if lines else "🎉 Nothing to fix today — great shape!"

    def _today_priority(self, audit, gsc):
        if audit:
            for path, data in audit.get("pages", {}).items():
                for issue in data.get("issues", []):
                    if "❌" in issue and (path == "/" or "homepage" in path.lower()):
                        return issue.lstrip("❌ ")
        if gsc:
            wins = gsc.get("quick_wins", [])
            if wins:
                top = wins[0]
                return (
                    f'Update your meta description for "{top["query"]}" — '
                    f'you\'re showing up {top["impressions"]:,} times/month but only {top["ctr"]}% of people click. '
                    f'A better description could add dozens of visits per month with no extra ranking effort.'
                )
        return "Great shape — focus on publishing a new blog post targeting one of your quick win queries."

    def _build_keyword_gap_section(self, kg):
        if not kg:
            return "_No keyword gap data yet — run `python monitor/run_daily.py` to fetch._\n"

        s = kg.get("summary", {})
        gap_count  = s.get("gap_count", 0)
        imp_count  = s.get("improvement_count", 0)
        win_count  = s.get("win_count", 0)
        disc_count = s.get("discovered_keywords_count", 0)
        updated    = kg.get("last_updated", "")[:10]

        lines = [
            f"_Last checked: {updated}_",
            "",
            f"**{gap_count} Gaps** · **{imp_count} Improvements** · **{win_count} Wins** · **{disc_count} new keyword opportunities found**",
            "",
            "_A **Gap** means a competitor ranks for a keyword you don't. An **Improvement** means you both rank, but they're ahead. A **Win** means you're outranking them._",
            "",
        ]

        gaps = kg.get("gaps", [])
        if gaps:
            lines.append("### ❌ Gaps — They rank here, you don't")
            lines.append("_These are the highest-priority items. Each one is traffic you're leaving on the table._")
            lines.append("")
            for g in gaps:
                tc = g.get("top_competitor", {})
                lines.append(f"**\"{g['keyword']}\"**")
                lines.append(f"- Top competitor: `{tc.get('domain')}` at #{tc.get('position')}")
                lines.append(f"- **Action:** {g['action']}")
                lines.append(f"- {g['action_detail']}")
                paa = g.get("paa_questions", [])
                if paa:
                    lines.append(f"- _People Also Ask: {' · '.join(f'\"{q}\"' for q in paa[:2])}_")
                lines.append("")

        improvements = kg.get("improvements", [])
        if improvements:
            lines.append("### ⬆️ Improvements — You both rank, they're ahead")
            lines.append("_You already have a foothold. These are quickest to move._")
            lines.append("")
            for g in improvements:
                tc = g.get("top_competitor", {})
                our_pos = g.get("our_position")
                lines.append(f"**\"{g['keyword']}\"** — You: #{our_pos} | {tc.get('domain')}: #{tc.get('position')}")
                lines.append(f"- **Action:** {g['action']}")
                lines.append(f"- {g['action_detail']}")
                paa = g.get("paa_questions", [])
                if paa:
                    lines.append(f"- _People Also Ask: {' · '.join(f'\"{q}\"' for q in paa[:2])}_")
                lines.append("")

        wins = kg.get("wins", [])
        if wins:
            lines.append("### ✅ Wins — You're outranking the competition")
            lines.append("_Keep these pages fresh. Don't let them go stale._")
            lines.append("")
            for g in wins:
                tc = g.get("top_competitor", {})
                our_pos = g.get("our_position")
                lines.append(f"- **\"{g['keyword']}\"** — You: #{our_pos} | next competitor: {tc.get('domain')} at #{tc.get('position')}")
            lines.append("")

        discovered = kg.get("discovered_keywords", [])
        if discovered:
            lines.append("### 💡 Keyword Opportunities Discovered")
            lines.append("_These surfaced from People Also Ask boxes and Related Searches while checking your competitors. Consider adding them to your tracking list or targeting them with content._")
            lines.append("")
            lines.append("| Keyword | Source |")
            lines.append("|---|---|")
            for d in discovered[:15]:
                src = "People Also Ask" if d["source"] == "paa" else "Related searches"
                lines.append(f"| {d['keyword']} | {src} |")

        return "\n".join(lines)

    def _build_competitor_keywords_section(self, ck):
        if not ck:
            return "_No competitor keyword data yet — run `python monitor/competitor_keyword_spy.py` to fetch._\n"

        updated = ck.get("last_updated", "")[:10]
        competitors = ck.get("competitors", [])
        if not competitors:
            return "_No competitor keyword data found._\n"

        lines = [
            f"_Last checked: {updated}_",
            "",
            "_Keywords your competitors rank for, matched against your existing content. ❌ = gap (nothing on your site covers this) · 🟡 = partial match · ✅ = covered_",
            "",
        ]

        for comp in competitors:
            domain  = comp.get("domain", "")
            summary = comp.get("summary", {})
            total   = summary.get("total", 0)
            gaps    = summary.get("gaps", 0)
            partial = summary.get("partial", 0)
            covered = summary.get("covered", 0)

            if total == 0:
                note = comp.get("note", "")
                lines.append(f"**{domain}** — {note or 'No keywords extracted'}")
                lines.append("")
                continue

            lines.append(f"**{domain}** — {total} keywords · ❌ {gaps} gaps · 🟡 {partial} partial · ✅ {covered} covered")
            lines.append("| Keyword | Match | Your Closest Page |")
            lines.append("|---|---|---|")

            for kw in comp.get("keywords", [])[:20]:
                match      = kw.get("our_match", "none")
                keyword    = kw.get("keyword", "")
                match_page = kw.get("our_match_page") or ""

                if match == "none":
                    emoji    = "❌"
                    page_str = "—"
                elif match == "partial":
                    emoji    = "🟡"
                    slug     = match_page.strip("/").split("/")[-1].replace("-", " ") or "Homepage"
                    page_str = f"_{slug[:45]}_"
                else:
                    emoji    = "✅"
                    slug     = match_page.strip("/").split("/")[-1].replace("-", " ") or "Homepage"
                    page_str = f"_{slug[:45]}_"

                lines.append(f"| {keyword} | {emoji} | {page_str} |")

            lines.append("")

        return "\n".join(lines)

    # ── HTML export ───────────────────────────────────────────────

    def _html_gsc(self, gsc):
        if not gsc:
            return "<p><em>No GSC data available.</em></p>"
        trend     = gsc.get("weekly_trend", {})
        this_week = trend.get("this_week", {})
        last_week = trend.get("last_week", {})
        clicks    = this_week.get("clicks", 0)
        imp       = this_week.get("impressions", 0)
        pos       = this_week.get("position", 0)
        pos_chg   = trend.get("position_change", 0)
        clk_pct   = trend.get("clicks_change_pct")
        imp_pct   = trend.get("impressions_change_pct")

        def pct(v):
            if v is None: return ""
            arrow = "▲" if v > 0 else "▼"
            return f" <span class='{'up' if v > 0 else 'dn'}'>{arrow} {abs(v)}%</span>"

        pos_note = f"▲ improved {abs(pos_chg)}" if pos_chg < 0 else f"▼ dropped {pos_chg}" if pos_chg > 0 else "no change"

        html = f"""<table>
<tr><th>Metric</th><th>This Week</th><th>vs Last Week</th></tr>
<tr><td>Clicks</td><td><strong>{clicks}</strong></td><td>vs {last_week.get('clicks',0)}{pct(clk_pct)}</td></tr>
<tr><td>Impressions</td><td><strong>{imp:,}</strong></td><td>vs {last_week.get('impressions',0):,}{pct(imp_pct)}</td></tr>
<tr><td>Avg Position</td><td><strong>{pos}</strong></td><td>{pos_note}</td></tr>
</table>"""

        quick_wins = gsc.get("quick_wins", [])
        if quick_wins:
            html += "<p><strong>⚡ Quick Wins — showing up but not getting clicked:</strong></p>"
            html += "<table><tr><th>Query</th><th>Impressions</th><th>Position</th><th>CTR</th></tr>"
            for q in quick_wins:
                html += f"<tr><td>{q['query']}</td><td>{q['impressions']:,}</td><td>#{q['position']}</td><td class='dn'>{q['ctr']}%</td></tr>"
            html += "</table>"
        return html

    def _html_rankings(self, rankings):
        if not rankings:
            return "<p><em>No ranking data available.</em></p>"
        r = rankings.get("rankings", {})
        updated = rankings.get("last_updated", "")[:10]
        history_file = os.path.join(DATA_DIR, "rankings_history.json")
        prev = {}
        if os.path.exists(history_file):
            try:
                with open(history_file) as f:
                    history = json.load(f)
                if len(history) >= 2:
                    prev = history[-2].get("rankings", {})
            except Exception:
                pass

        html = f"<p><em>Last checked: {updated}</em></p>"
        html += "<table><tr><th>Keyword</th><th>Position</th><th>Change</th></tr>"
        for keyword, data in r.items():
            pos      = data.get("position")
            prev_pos = prev.get(keyword)
            diff     = (prev_pos - pos) if (prev_pos and pos) else None
            pos_str  = f"#{pos}" if pos else "Not ranked"
            cls      = "pos-top" if (pos and pos <= 3) else "pos-mid" if (pos and pos <= 10) else "pos-low"
            chg_str  = (f"<span class='up'>▲ +{diff}</span>" if diff and diff > 0
                        else f"<span class='dn'>▼ {diff}</span>" if diff and diff < 0
                        else "—")
            html += f"<tr><td>{keyword}</td><td class='{cls}'>{pos_str}</td><td>{chg_str}</td></tr>"
        html += "</table>"
        html += "<p class='legend'>🟢 Top 3 &nbsp;·&nbsp; 🟡 4–10 &nbsp;·&nbsp; 🔴 11+ &nbsp;·&nbsp; ⚫ Not ranked</p>"
        return html

    def _html_competitors(self, competitors):
        if not competitors:
            return "<p><em>No competitor data available.</em></p>"
        target_score = competitors.get("target_authority_score")
        html = ""
        if target_score:
            bar  = "█" * int(target_score) + "░" * (10 - int(target_score))
            html += f"<p><strong>Your Site Authority: {target_score}/10</strong> <code>{bar}</code></p>"

        for kw_data in competitors.get("keywords", []):
            keyword    = kw_data["keyword"]
            target_pos = kw_data.get("target_position")
            comps      = [c for c in kw_data.get("competitors", []) if not c.get("is_directory")]
            if not comps:
                continue
            pos_str = f"you rank #{target_pos}" if target_pos else "not in top 10"
            html += f"<p class='kw-title'><strong>{keyword}</strong> — {pos_str}</p>"
            html += "<table><tr><th>#</th><th>Competitor</th><th>Authority</th><th>Difficulty</th><th>What this means</th></tr>"
            for c in comps:
                score     = c.get("authority_score")
                score_str = f"{score}/10" if score is not None else "n/a"
                diff      = c.get("difficulty", "Unknown")
                expl      = c.get("difficulty_explanation", "")
                diff_cls  = {"Beatable now": "up", "Competitive": "mid", "Hard": "dn", "Dominant": "dn"}.get(diff, "")
                html += f"<tr><td>{c['position']}</td><td>{c['domain']}</td><td>{score_str}</td><td class='{diff_cls}'>{diff}</td><td>{expl}</td></tr>"
            html += "</table>"
        return html

    def _html_keyword_gap(self, kg):
        if not kg:
            return "<p><em>No keyword gap data available.</em></p>"
        s          = kg.get("summary", {})
        updated    = kg.get("last_updated", "")[:10]
        gap_count  = s.get("gap_count", 0)
        imp_count  = s.get("improvement_count", 0)
        win_count  = s.get("win_count", 0)
        disc_count = s.get("discovered_keywords_count", 0)

        html = f"<p><em>Last checked: {updated}</em></p>"
        html += f"<p><strong>{gap_count} Gaps · {imp_count} Improvements · {win_count} Wins · {disc_count} keyword opportunities</strong></p>"

        gaps = kg.get("gaps", [])
        if gaps:
            html += "<h3>❌ Gaps — They rank here, you don't</h3>"
            for g in gaps:
                tc = g.get("top_competitor", {})
                kw = g['keyword']
                html += f"<div class='action-block'><strong>&ldquo;{kw}&rdquo;</strong><br>"
                html += f"Top competitor: <code>{tc.get('domain')}</code> at #{tc.get('position')}<br>"
                html += f"<strong>Action:</strong> {g['action']}<br>"
                html += f"{g['action_detail']}"
                paa = g.get("paa_questions", [])
                if paa:
                    html += f"<br><em>People Also Ask: {' &middot; '.join(paa[:2])}</em>"
                html += "</div>"

        improvements = kg.get("improvements", [])
        if improvements:
            html += "<h3>⬆️ Improvements — You both rank, they're ahead</h3>"
            for g in improvements:
                tc      = g.get("top_competitor", {})
                our_pos = g.get("our_position")
                kw = g['keyword']
                html += f"<div class='action-block'><strong>&ldquo;{kw}&rdquo;</strong> — You: #{our_pos} | {tc.get('domain')}: #{tc.get('position')}<br>"
                html += f"<strong>Action:</strong> {g['action']}<br>{g['action_detail']}</div>"

        wins = kg.get("wins", [])
        if wins:
            html += "<h3>✅ Wins — You're outranking the competition</h3><ul>"
            for g in wins:
                tc      = g.get("top_competitor", {})
                our_pos = g.get("our_position")
                kw = g['keyword']
                html += f"<li><strong>&ldquo;{kw}&rdquo;</strong> — You: #{our_pos} | next competitor: {tc.get('domain')} at #{tc.get('position')}</li>"
            html += "</ul>"

        discovered = kg.get("discovered_keywords", [])
        if discovered:
            html += "<h3>💡 Keyword Opportunities Discovered</h3>"
            html += "<table><tr><th>Keyword</th><th>Source</th></tr>"
            for d in discovered[:15]:
                src = "People Also Ask" if d["source"] == "paa" else "Related searches"
                html += f"<tr><td>{d['keyword']}</td><td>{src}</td></tr>"
            html += "</table>"
        return html

    def _html_competitor_keywords(self, ck):
        if not ck:
            return "<p><em>No competitor keyword data available.</em></p>"
        updated     = ck.get("last_updated", "")[:10]
        competitors = ck.get("competitors", [])
        if not competitors:
            return "<p><em>No competitor keyword data found.</em></p>"

        html = f"<p><em>Last checked: {updated} · ❌ gap &nbsp;·&nbsp; 🟡 partial &nbsp;·&nbsp; ✅ covered</em></p>"
        for comp in competitors:
            domain  = comp.get("domain", "")
            summary = comp.get("summary", {})
            total   = summary.get("total", 0)
            gaps    = summary.get("gaps", 0)
            partial = summary.get("partial", 0)
            covered = summary.get("covered", 0)
            if total == 0:
                html += f"<p><strong>{domain}</strong> — {comp.get('note','No keywords extracted')}</p>"
                continue
            html += f"<p class='kw-title'><strong>{domain}</strong> — {total} keywords · <span class='dn'>{gaps} gaps</span> · <span class='mid'>{partial} partial</span> · <span class='up'>{covered} covered</span></p>"
            html += "<table><tr><th>Keyword</th><th>Match</th><th>Your Closest Page</th></tr>"
            for kw in comp.get("keywords", [])[:20]:
                match      = kw.get("our_match", "none")
                keyword    = kw.get("keyword", "")
                match_page = kw.get("our_match_page") or ""
                if match == "none":
                    emoji, page_str = "❌", "—"
                else:
                    emoji    = "🟡" if match == "partial" else "✅"
                    slug     = match_page.strip("/").split("/")[-1].replace("-", " ") or "Homepage"
                    page_str = slug[:50]
                html += f"<tr><td>{keyword}</td><td>{emoji}</td><td>{page_str}</td></tr>"
            html += "</table>"
        return html

    def _html_site_health(self, audit):
        if not audit:
            return "<p><em>No audit data available.</em></p>"
        html = "<ul>"
        for path, data in audit.get("pages", {}).items():
            issues = data.get("issues", [])
            label  = "Homepage" if path == "/" else path.split("/")[-1].replace("-", " ").title()
            if issues:
                html += f"<li><strong>⚠️ {label}</strong><ul>"
                for issue in issues:
                    html += f"<li>{issue}</li>"
                html += "</ul></li>"
            else:
                html += f"<li class='up'>✅ <strong>{label}</strong> — no issues</li>"
        html += "</ul>"
        return html

    def _html_top_pages(self, gsc):
        if not gsc:
            return "<p><em>No data available.</em></p>"
        top_pages = gsc.get("top_pages", [])[:8]
        if not top_pages:
            return "<p><em>No page data yet.</em></p>"
        html = "<table><tr><th>Page</th><th>Clicks</th><th>Impressions</th><th>CTR</th></tr>"
        for p in top_pages:
            slug    = p["page"].replace("https://www.shamelessmamawellness.com", "") or "/"
            short   = slug[:60] + "…" if len(slug) > 60 else slug
            ctr_cls = "up" if p["ctr"] >= 3 else "mid" if p["ctr"] >= 1 else "dn"
            html   += f"<tr><td>{short}</td><td>{p['clicks']}</td><td>{p['impressions']:,}</td><td class='{ctr_cls}'>{p['ctr']}%</td></tr>"
        html += "</table>"
        return html

    def _generate_html_export(self, gsc, rankings, audit, competitors, keyword_gap, competitor_keywords):
        updated = datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")
        css = """
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 960px; margin: 40px auto; padding: 0 24px; color: #1a1a1a; font-size: 14px; line-height: 1.5; }
        h1 { font-size: 22px; border-bottom: 2px solid #222; padding-bottom: 10px; margin-bottom: 6px; }
        h2 { font-size: 15px; font-weight: 700; color: #222; margin: 28px 0 8px; padding-bottom: 4px; border-bottom: 1px solid #e0e0e0; }
        h3 { font-size: 13px; font-weight: 600; color: #444; margin: 16px 0 6px; }
        p { margin: 6px 0; }
        table { width: 100%; border-collapse: collapse; margin: 8px 0 14px; font-size: 13px; }
        th { background: #f2f2f2; text-align: left; padding: 6px 10px; border: 1px solid #ddd; font-weight: 600; font-size: 12px; }
        td { padding: 6px 10px; border: 1px solid #e0e0e0; vertical-align: top; }
        tr:nth-child(even) td { background: #fafafa; }
        .up { color: #1a7a1a; }
        .dn { color: #b00; }
        .mid { color: #b7700a; }
        .pos-top { color: #1a7a1a; font-weight: 600; }
        .pos-mid { color: #b7700a; font-weight: 600; }
        .pos-low { color: #b00; }
        .meta { font-size: 12px; color: #777; margin-bottom: 18px; }
        .legend { font-size: 12px; color: #777; margin-top: 4px; }
        .action-block { background: #f8f8f8; border-left: 3px solid #bbb; padding: 10px 14px; margin: 8px 0; border-radius: 2px; font-size: 13px; }
        .kw-title { margin: 16px 0 4px; font-size: 13px; }
        ul { padding-left: 20px; margin: 6px 0; }
        li { margin: 3px 0; }
        code { background: #f0f0f0; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
        .section { margin-top: 8px; }
        footer { margin-top: 40px; padding-top: 12px; border-top: 1px solid #eee; font-size: 11px; color: #aaa; }
        #print-btn { position: fixed; top: 18px; right: 18px; background: #222; color: #fff; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; z-index: 999; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
        #print-btn:hover { background: #444; }
        @media print {
          #print-btn { display: none; }
          body { margin: 16px; max-width: 100%; }
          h2 { page-break-after: avoid; }
          table { page-break-inside: auto; }
          tr { page-break-inside: avoid; }
          .action-block { page-break-inside: avoid; }
        }
        """

        body = f"""
        <button id="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
        <h1>Shameless Mama Wellness — SEO Dashboard</h1>
        <div class="meta">Generated {updated} · shamelessmamawellness.com</div>

        <h2>📊 Google Search Console</h2>
        <div class="section">{self._html_gsc(gsc)}</div>

        <h2>🔑 Keyword Rankings</h2>
        <div class="section">{self._html_rankings(rankings)}</div>

        <h2>🏆 Competitor Landscape</h2>
        <div class="section">{self._html_competitors(competitors)}</div>

        <h2>🎯 Keyword Gap Analysis</h2>
        <div class="section">{self._html_keyword_gap(keyword_gap)}</div>

        <h2>🔍 Competitor Keyword Intelligence</h2>
        <div class="section">{self._html_competitor_keywords(competitor_keywords)}</div>

        <h2>🏥 Site Health</h2>
        <div class="section">{self._html_site_health(audit)}</div>

        <h2>📄 Top Pages (last 28 days)</h2>
        <div class="section">{self._html_top_pages(gsc)}</div>

        <footer>Generated by Shameless Mama SEO Monitor · {updated}</footer>
        """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SEO Dashboard — Shameless Mama Wellness</title>
<style>{css}</style>
</head>
<body>{body}</body>
</html>"""

    def _save_html_export(self, gsc, rankings, audit, competitors, keyword_gap, competitor_keywords):
        html     = self._generate_html_export(gsc, rankings, audit, competitors, keyword_gap, competitor_keywords)
        date_str = datetime.date.today().isoformat()
        path     = os.path.expanduser(f"~/Desktop/seo-dashboard-{date_str}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path

    def pipe(self, body: dict, __user: dict = {}) -> str:
        messages = body.get("messages", [])
        if not messages:
            return ""
        last_message = messages[-1].get("content", "")
        if not self._is_triggered(last_message):
            return ""

        gsc                  = self._load("gsc.json")
        rankings             = self._load("rankings.json")
        audit                = self._load("audit.json")
        competitors          = self._load("competitors.json")
        keyword_gap          = self._load("keyword_gap.json")
        competitor_keywords  = self._load("competitor_keywords.json")

        if any(t in last_message.lower() for t in EXPORT_TRIGGERS):
            try:
                path = self._save_html_export(gsc, rankings, audit, competitors, keyword_gap, competitor_keywords)
                return (
                    f"✅ Dashboard exported to `{path}`\n\n"
                    f"Open in Chrome or Safari → **File → Print → Save as PDF**"
                )
            except Exception as e:
                return f"❌ Export failed: {e}"

        updated = datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")

        return f"""# Shameless Mama Wellness — SEO Dashboard
_Generated {updated} · Data refreshes daily at 7am & 3pm_

---

## 📊 Google Search Console
{self._build_gsc_section(gsc)}

---

## 🔑 Keyword Rankings
{self._build_rankings_section(rankings)}

---

## 🏆 Competitor Landscape
{self._build_competitor_section(competitors)}

---

## 🎯 Keyword Gap Analysis
{self._build_keyword_gap_section(keyword_gap)}

---

## 🔍 Competitor Keyword Intelligence
{self._build_competitor_keywords_section(competitor_keywords)}

---

## 🏥 Site Health
{self._build_health_section(audit)}

---

## 📄 Top Pages (last 28 days)
{self._build_top_pages_section(gsc)}

---

## 🔧 Fix List
{self._build_fix_list(audit, gsc)}

---

## ⭐ Today's Priority
> {self._today_priority(audit, gsc)}

---

**Quick Links:** [Website](https://www.shamelessmamawellness.com) · [Squarespace](https://account.squarespace.com) · [Psychology Today](https://www.psychologytoday.com/us/therapists/marilyn-cross-coleman-san-francisco-ca/1309990) · [Google Business](https://business.google.com) · [Search Console](https://search.google.com/search-console)
"""
