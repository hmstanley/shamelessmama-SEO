"""
SEO Monitor for shamelessmamawellness.com
Checks keyword rankings and saves results to dashboard/data/rankings.json

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

KEYWORDS = [
    "Birth trauma therapist San Francisco",
    "Postpartum therapist San Francisco Bay Area",
    "EMDR therapist moms California",
    "Postpartum depression therapist California",
    "Prenatal therapist San Francisco",
    "EMDR intensive birth trauma",
    "Perinatal mental health therapist California",
    "Birth trauma therapist online California",
    "Postpartum anxiety therapist Bay Area",
    "Mother wound therapist California",
    "Postpartum therapist California",
    "Birth trauma therapist Sacramento",
    "Shameless Mama Wellness",
    "Marilyn Coleman therapist",
]


def _extract_urls_from_html(html, skip_domains):
    """
    Pull every href out of the HTML, decode Yahoo redirects,
    and return deduplicated real URLs in order of appearance.
    """
    seen = set()
    results = []

    # Strategy 1: Yahoo /RU= redirect URLs (most reliable)
    for encoded in re.findall(r'/RU=([^/]+)/RK=', html):
        try:
            url = urllib.parse.unquote(encoded)
            if url.startswith("http") and url not in seen:
                domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
                if domain and not any(s in domain.group(1) for s in skip_domains):
                    seen.add(url)
                    results.append(url)
        except Exception:
            pass

    # Strategy 2: all href= attributes (fallback)
    if not results:
        for url in re.findall(r'href="(https?://[^"]+)"', html):
            try:
                # Skip Yahoo/tracking/ad URLs
                if any(s in url for s in skip_domains):
                    continue
                # Skip Yahoo-internal links
                if "yahoo.com" in url or "yimg.com" in url:
                    continue
                # Skip very short or clearly nav URLs
                if len(url) < 20:
                    continue
                if url not in seen:
                    seen.add(url)
                    results.append(url)
            except Exception:
                pass

    return results


def search_yahoo(keyword, max_results=20):
    """
    Search Yahoo (uses Bing index) and return ranked results.
    Returns list of (position, url, title) tuples.
    """
    encoded = urllib.parse.quote_plus(keyword)
    url = f"https://search.yahoo.com/search?p={encoded}&n=20"

    skip_domains = [
        "yahoo.com", "yimg.com", "oath.com", "verizonmedia.com",
        "doubleclick.net", "googlesyndication.com",
    ]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        urls = _extract_urls_from_html(html, skip_domains)

        results = []
        for i, u in enumerate(urls[:max_results], start=1):
            results.append((i, u, ""))

        if not results:
            print(f"  ⚠️  No results parsed for '{keyword}' — Yahoo may have changed layout")

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


def check_rankings():
    """Check all keyword rankings and return results dict."""
    print(f"\n{'='*60}")
    print(f"SEO Ranking Check — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Target: {TARGET_SITE}")
    print(f"{'='*60}\n")

    results = {}

    for keyword in KEYWORDS:
        print(f"Checking: {keyword}...")
        search_results = search_yahoo(keyword)
        position, url, title = find_ranking(keyword, search_results)

        if position:
            status = "✅" if position <= 3 else "🟡" if position <= 10 else "🔴"
            print(f"  {status} Position #{position}: {url}")
        else:
            print(f"  ❌ Not found in top {len(search_results)} results")

        results[keyword] = {
            "position": position,
            "url": url,
            "title": title,
            "checked_at": datetime.datetime.now().isoformat(),
            "total_results_checked": len(search_results),
        }

        time.sleep(2)  # Be polite — don't hammer search engines

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
    results = check_rankings()
    save_results(results)
    print_summary(results)
    print("\nDone! Open dashboard/index.html in your browser to see the full report.\n")
