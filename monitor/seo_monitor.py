"""
SEO Monitor for shamelessmamawellness.com
Checks keyword rankings via Serper.dev (Google results) and saves to dashboard/data/rankings.json

API key: stored in .serperAPI at the repo root (never committed to git)

Run: python monitor/seo_monitor.py
"""

import json
import urllib.request
import urllib.parse
import datetime
import time
import os
import re

TARGET_SITE = "shamelessmamawellness.com"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data")
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")

_kw_file = os.path.join(REPO_ROOT, "config", "keywords.json")
with open(_kw_file) as _f:
    KEYWORDS = json.load(_f)["rankings"]


def load_serper_key():
    """Load Serper API key from .serperAPI file or environment variable."""
    # Try file first
    key_file = os.path.join(REPO_ROOT, ".serperAPI")
    if os.path.exists(key_file):
        with open(key_file) as f:
            key = f.read().strip()
            if key:
                return key

    # Fall back to environment variable
    key = os.environ.get("SERPER_API_KEY", "")
    if key:
        return key

    return None


def search_google(keyword, api_key, max_results=20):
    """
    Search Google via Serper.dev API and return ranked results.
    Returns list of (position, url, title) tuples.
    """
    payload = json.dumps({
        "q": keyword,
        "num": max_results,
        "gl": "us",
        "hl": "en",
    }).encode()

    req = urllib.request.Request(
        "https://google.serper.dev/search",
        data=payload,
        headers={
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)

        results = []
        # Organic results
        for item in data.get("organic", []):
            position = item.get("position", len(results) + 1)
            url = item.get("link", "")
            title = item.get("title", "")
            if url:
                results.append((position, url, title))

        return results

    except Exception as e:
        print(f"  Search error for '{keyword}': {e}")
        return []


def find_ranking(keyword, results):
    """Find position of target site in results. Returns None if not found."""
    for position, url, title in results:
        if TARGET_SITE in url:
            return position, url, title
    return None, None, None


def check_rankings(api_key):
    """Check all keyword rankings and return results dict."""
    print(f"\n{'='*60}")
    print(f"SEO Ranking Check — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Target: {TARGET_SITE}")
    print(f"Source: Google (via Serper.dev)")
    print(f"{'='*60}\n")

    results = {}

    for keyword in KEYWORDS:
        print(f"Checking: {keyword}...")
        search_results = search_google(keyword, api_key)
        position, url, title = find_ranking(keyword, search_results)

        if position:
            status = "✅" if position <= 3 else "🟡" if position <= 10 else "🔴"
            print(f"  {status} Position #{position}: {url}")
            if title:
                print(f"     \"{title}\"")
        else:
            print(f"  ❌ Not found in top {len(search_results)} results")

        results[keyword] = {
            "position": position,
            "url": url,
            "title": title,
            "checked_at": datetime.datetime.now().isoformat(),
            "total_results_checked": len(search_results),
        }

        time.sleep(0.5)  # Small delay to be polite

    return results


def load_history():
    """Load historical ranking data."""
    history_file = os.path.join(DATA_DIR, "rankings_history.json")
    if os.path.exists(history_file):
        with open(history_file) as f:
            return json.load(f)
    return []


def save_results(results):
    """Save results to JSON files for the dashboard."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Current rankings
    rankings_file = os.path.join(DATA_DIR, "rankings.json")
    output = {
        "last_updated": datetime.datetime.now().isoformat(),
        "site": TARGET_SITE,
        "source": "Google via Serper.dev",
        "rankings": results,
    }
    with open(rankings_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n✅ Rankings saved to {rankings_file}")

    # Append to history
    history = load_history()
    history.append({
        "date": datetime.date.today().isoformat(),
        "rankings": {k: v["position"] for k, v in results.items()},
    })
    # Keep last 90 days
    history = history[-90:]
    history_file = os.path.join(DATA_DIR, "rankings_history.json")
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)
    print(f"✅ History updated ({len(history)} days recorded)")


def print_summary(results):
    """Print a clean summary."""
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    top3 = [(k, v) for k, v in results.items() if v["position"] and v["position"] <= 3]
    top10 = [(k, v) for k, v in results.items() if v["position"] and 3 < v["position"] <= 10]
    not_found = [(k, v) for k, v in results.items() if not v["position"]]

    print(f"\n🏆 TOP 3 ({len(top3)} keywords):")
    for k, v in sorted(top3, key=lambda x: x[1]["position"]):
        print(f"   #{v['position']} — {k}")

    print(f"\n✅ TOP 10 ({len(top10)} keywords):")
    for k, v in sorted(top10, key=lambda x: x[1]["position"]):
        print(f"   #{v['position']} — {k}")

    print(f"\n❌ NOT IN TOP 20 ({len(not_found)} keywords):")
    for k, v in not_found:
        print(f"   — {k}")


if __name__ == "__main__":
    api_key = load_serper_key()
    if not api_key:
        print("❌ No Serper API key found.")
        print("   Create a file called .serperAPI in the repo root with your key.")
        print("   Get a free key at https://serper.dev (2,500 searches/month free)")
        exit(1)

    results = check_rankings(api_key)
    save_results(results)
    print_summary(results)
    print("\nDone! Open dashboard/index.html in your browser to see the full report.\n")
