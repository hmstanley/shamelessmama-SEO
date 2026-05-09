"""
Google Search Console Monitor for shamelessmamawellness.com
Fetches real search performance data: queries, impressions, clicks, CTR, position.

Reads:  ~/.shameless-gsc-token.json (created by gsc_auth.py)
Writes: dashboard/data/gsc.json

Run: python monitor/gsc_monitor.py
"""

import json
import urllib.request
import urllib.parse
import datetime
import os

TOKEN_FILE = os.path.expanduser("~/.shameless-gsc-token.json")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "gsc.json")
SITE_URL = "https://www.shamelessmamawellness.com/"


def get_access_token():
    """Exchange refresh token for a fresh access token."""
    with open(TOKEN_FILE) as f:
        creds = json.load(f)

    payload = urllib.parse.urlencode({
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": creds["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request(
        creds["token_uri"],
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.load(resp)

    return result["access_token"]


def query_gsc(access_token, body):
    """POST to the Search Console searchAnalytics API."""
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(SITE_URL, safe='')}/searchAnalytics/query"
    payload = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def run():
    if not os.path.exists(TOKEN_FILE):
        print(f"Token file not found: {TOKEN_FILE}")
        print("Run monitor/gsc_auth.py first.")
        return {}

    print(f"\nGoogle Search Console — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    try:
        access_token = get_access_token()
    except Exception as e:
        print(f"Failed to get access token: {e}")
        print("Try running monitor/gsc_auth.py again to reauthorize.")
        return {}

    today = datetime.date.today()
    end_date = today.isoformat()
    start_28 = (today - datetime.timedelta(days=28)).isoformat()
    start_7  = (today - datetime.timedelta(days=7)).isoformat()

    results = {}

    # --- Top queries (28 days) ---
    print("  Fetching top search queries (28 days)...")
    try:
        data = query_gsc(access_token, {
            "startDate": start_28,
            "endDate": end_date,
            "dimensions": ["query"],
            "rowLimit": 50,
            "orderBy": [{"fieldName": "impressions", "sortOrder": "DESCENDING"}],
        })
        rows = data.get("rows", [])
        results["top_queries"] = [
            {
                "query": r["keys"][0],
                "clicks": r["clicks"],
                "impressions": r["impressions"],
                "ctr": round(r["ctr"] * 100, 1),
                "position": round(r["position"], 1),
            }
            for r in rows
        ]
        print(f"    {len(rows)} queries found")
    except Exception as e:
        print(f"    Error: {e}")
        results["top_queries"] = []

    # --- Top pages (28 days) ---
    print("  Fetching top pages (28 days)...")
    try:
        data = query_gsc(access_token, {
            "startDate": start_28,
            "endDate": end_date,
            "dimensions": ["page"],
            "rowLimit": 20,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
        })
        rows = data.get("rows", [])
        results["top_pages"] = [
            {
                "page": r["keys"][0],
                "clicks": r["clicks"],
                "impressions": r["impressions"],
                "ctr": round(r["ctr"] * 100, 1),
                "position": round(r["position"], 1),
            }
            for r in rows
        ]
        print(f"    {len(rows)} pages found")
    except Exception as e:
        print(f"    Error: {e}")
        results["top_pages"] = []

    # --- Overall site totals: last 7 days vs previous 7 days ---
    print("  Fetching weekly totals (for trend comparison)...")
    try:
        def get_totals(start, end):
            data = query_gsc(access_token, {
                "startDate": start,
                "endDate": end,
                "dimensions": [],
                "rowLimit": 1,
            })
            rows = data.get("rows", [{}])
            r = rows[0] if rows else {}
            return {
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": round(r.get("ctr", 0) * 100, 1),
                "position": round(r.get("position", 0), 1),
            }

        start_prev = (today - datetime.timedelta(days=14)).isoformat()
        end_prev   = (today - datetime.timedelta(days=8)).isoformat()

        this_week = get_totals(start_7, end_date)
        last_week = get_totals(start_prev, end_prev)

        def delta(curr, prev):
            if prev == 0:
                return None
            return round(((curr - prev) / prev) * 100, 1)

        results["weekly_trend"] = {
            "this_week": this_week,
            "last_week": last_week,
            "clicks_change_pct": delta(this_week["clicks"], last_week["clicks"]),
            "impressions_change_pct": delta(this_week["impressions"], last_week["impressions"]),
            "position_change": round(this_week["position"] - last_week["position"], 1),
        }
        print(f"    This week: {this_week['clicks']} clicks, {this_week['impressions']} impressions")
    except Exception as e:
        print(f"    Error: {e}")
        results["weekly_trend"] = {}

    # --- Queries with high impressions but low CTR (quick wins) ---
    print("  Identifying quick wins (high impressions, low CTR)...")
    quick_wins = []
    for q in results.get("top_queries", []):
        if q["impressions"] >= 10 and q["ctr"] < 3.0 and q["position"] <= 20:
            quick_wins.append(q)
    quick_wins.sort(key=lambda x: x["impressions"], reverse=True)
    results["quick_wins"] = quick_wins[:10]
    print(f"    {len(quick_wins)} quick win opportunities found")

    # --- Save ---
    os.makedirs(DATA_DIR, exist_ok=True)
    output = {
        "last_updated": datetime.datetime.now().isoformat(),
        "site": SITE_URL,
        "date_range_28d": {"start": start_28, "end": end_date},
        "date_range_7d": {"start": start_7, "end": end_date},
        **results,
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to {OUTPUT_FILE}")
    return output


if __name__ == "__main__":
    run()
