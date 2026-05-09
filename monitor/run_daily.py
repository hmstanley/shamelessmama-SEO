"""
Daily SEO runner for shamelessmamawellness.com
Runs all monitors and writes a consolidated daily_digest.json.

Cron: runs at 7am via launchd (see com.shamelessmama.seo.plist)
Manual: python monitor/run_daily.py
"""

import subprocess
import sys
import os
import json
import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(SCRIPT_DIR, "..")
DATA_DIR = os.path.join(REPO_ROOT, "dashboard", "data")


def run_script(name):
    path = os.path.join(SCRIPT_DIR, name)
    print(f"\n{'='*50}")
    print(f"Running {name}...")
    print('='*50)
    result = subprocess.run([sys.executable, path], capture_output=False)
    return result.returncode == 0


def write_digest():
    """Consolidate key findings into a single daily_digest.json."""
    digest = {
        "generated_at": datetime.datetime.now().isoformat(),
        "date": datetime.date.today().isoformat(),
        "sections": {},
    }

    # GSC summary
    gsc_file = os.path.join(DATA_DIR, "gsc.json")
    if os.path.exists(gsc_file):
        with open(gsc_file) as f:
            gsc = json.load(f)
        trend = gsc.get("weekly_trend", {})
        digest["sections"]["gsc"] = {
            "clicks_this_week": trend.get("this_week", {}).get("clicks", 0),
            "impressions_this_week": trend.get("this_week", {}).get("impressions", 0),
            "clicks_change_pct": trend.get("clicks_change_pct"),
            "impressions_change_pct": trend.get("impressions_change_pct"),
            "position_change": trend.get("position_change"),
            "quick_wins": gsc.get("quick_wins", [])[:5],
            "top_pages": gsc.get("top_pages", [])[:5],
        }

    # Rankings summary
    rankings_file = os.path.join(DATA_DIR, "rankings.json")
    if os.path.exists(rankings_file):
        with open(rankings_file) as f:
            rankings = json.load(f)
        r = rankings.get("rankings", {})
        top3 = [(k, v) for k, v in r.items() if v.get("position") and v["position"] <= 3]
        top10 = [(k, v) for k, v in r.items() if v.get("position") and 3 < v["position"] <= 10]
        unranked = [(k, v) for k, v in r.items() if not v.get("position")]
        digest["sections"]["rankings"] = {
            "top3_count": len(top3),
            "top10_count": len(top10),
            "unranked_count": len(unranked),
            "top3": [{"keyword": k, "position": v["position"]} for k, v in sorted(top3, key=lambda x: x[1]["position"])],
            "unranked": [k for k, v in unranked],
        }

    # Competitor summary
    comp_file = os.path.join(DATA_DIR, "competitors.json")
    if os.path.exists(comp_file):
        with open(comp_file) as f:
            comp = json.load(f)
        beatable = []
        for kw in comp.get("keywords", []):
            for c in kw.get("competitors", []):
                if c.get("difficulty") == "Beatable now":
                    beatable.append({"keyword": kw["keyword"], "domain": c["domain"], "position": c["position"]})
        digest["sections"]["competitors"] = {
            "target_authority": comp.get("target_authority_score"),
            "beatable_count": len(beatable),
            "beatable_opportunities": beatable[:5],
        }

    # Audit summary
    audit_file = os.path.join(DATA_DIR, "audit.json")
    if os.path.exists(audit_file):
        with open(audit_file) as f:
            audit = json.load(f)
        digest["sections"]["audit"] = {
            "issue_count": audit.get("issue_count", 0),
            "total_issues": audit.get("total_issues", [])[:10],
        }

    # Keyword gap summary
    gap_file = os.path.join(DATA_DIR, "keyword_gap.json")
    if os.path.exists(gap_file):
        with open(gap_file) as f:
            kg = json.load(f)
        s = kg.get("summary", {})
        top_gap = kg.get("gaps", [{}])[0] if kg.get("gaps") else {}
        top_imp = kg.get("improvements", [{}])[0] if kg.get("improvements") else {}
        digest["sections"]["keyword_gap"] = {
            "gap_count": s.get("gap_count", 0),
            "improvement_count": s.get("improvement_count", 0),
            "win_count": s.get("win_count", 0),
            "discovered_count": s.get("discovered_keywords_count", 0),
            "top_gap": top_gap.get("keyword") if top_gap else None,
            "top_gap_action": top_gap.get("action") if top_gap else None,
            "top_improvement": top_imp.get("keyword") if top_imp else None,
            "top_improvement_action": top_imp.get("action") if top_imp else None,
        }

    os.makedirs(DATA_DIR, exist_ok=True)
    digest_file = os.path.join(DATA_DIR, "daily_digest.json")
    with open(digest_file, "w") as f:
        json.dump(digest, f, indent=2)
    print(f"\nDigest saved to {digest_file}")


if __name__ == "__main__":
    print("\nShameless Mama Wellness — Daily SEO Run")
    print(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    ok_gsc          = run_script("gsc_monitor.py")
    ok_audit        = run_script("site_audit.py")
    ok_rankings     = run_script("seo_monitor.py")
    ok_competitors  = run_script("competitor_monitor.py")
    ok_keyword_spy  = run_script("competitor_keyword_spy.py")
    ok_email        = run_script("email_monitor.py")
    ok_amazon       = run_script("amazon_monitor.py")

    print(f"\n{'='*50}")
    print("Results:")
    print(f"  Google Search Console:   {'OK' if ok_gsc else 'FAILED'}")
    print(f"  Site audit:              {'OK' if ok_audit else 'FAILED'}")
    print(f"  Keyword rankings:        {'OK' if ok_rankings else 'FAILED'}")
    print(f"  Competitor monitor:      {'OK' if ok_competitors else 'FAILED'}")
    print(f"  Competitor keyword spy:  {'OK' if ok_keyword_spy else 'FAILED'}")
    print(f"  Email monitor:           {'OK' if ok_email else 'FAILED'}")
    print(f"  Amazon orders:           {'OK' if ok_amazon else 'FAILED'}")

    write_digest()

    print(f"\nDone at {datetime.datetime.now().strftime('%H:%M')}")
