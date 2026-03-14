"""
Internal Link Auditor for Shameless Mama Wellness
Crawls blog posts and service pages, identifies missing internal links,
and suggests where to add them to boost SEO.

Run: python monitor/internal_links.py
"""

import json
import urllib.request
import urllib.error
import datetime
import os
import re
import time

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data")
SITE_URL = "https://www.shamelessmamawellness.com"

# Service pages — these should be linked from blog posts
SERVICE_PAGES = {
    "postpartum therapist california": "/postpartum-therapist-california",
    "postpartum depression": "/postpartum-depression-treatment-in-california",
    "postpartum anxiety": "/postpartum-anxiety-therapy-california",
    "birth trauma": "/traumatic-childbirth-therapist-sacramento",
    "emdr": "/emdr-postpartum-therapist-los-angeles",
    "prenatal therapy": "/postpartum-mental-health-therapist-california",
    "nicu": "/nicu-postpartum-therapist-san-francisco",
    "miscarriage": "/miscarriage-loss-postpartum-therapist-california",
    "fertility": "/fertility-therapist-california",
    "cbt": "/cbt-postpartum-therapist-san-francisco",
    "online counseling": "/online-counseling-postpartum-therapist-california",
    "san francisco": "/postpartum-therapy-services-san-francisco",
    "los angeles": "/pregnancy-postpartum-therapist-los-angeles",
    "about marilyn": "/about-marilyn-cross-coleman-postpartum-therapist-california",
    "book a consultation": "/book-an-appointment",
    "free consultation": "/book-an-appointment",
}

# Blog posts to audit (top 20 from sitemap)
BLOG_POSTS_TO_CHECK = [
    "/blog-4-1/postpartum-anxiety-vs-postpartum-depression-understanding-the-differences",
    "/blog-4-1/what-is-postpartum-anxiety-like",
    "/blog-4-1/how-long-does-postpartum-anxiety-last",
    "/blog-4-1/birth-trauma-is-real-heres-how-therapy-can-help-you-heal",
    "/blog-4-1/what-is-birth-trauma-signs-you-might-be-overlooking",
    "/blog-4-1/how-emdr-intensives-help-heal-birth-trauma-faster-than-weekly-therapy",
    "/blog-4-1/healing-the-mother-wound-how-emdr-therapy-supports-moms",
    "/blog-4-1/the-mother-wound-and-ptsd-in-motherhood-what-you-need-to-know",
    "/blog-4-1/generational-trauma-and-the-mother-wound-breaking-the-cycle",
    "/blog-4-1/emdr-for-birth-trauma-what-to-expect-from-a-1-day-intensive",
    "/blog-4-1/why-your-birth-was-traumatic-even-if-your-baby-is-healthy",
    "/blog-4-1/postpartum-therapy-in-california-what-to-expect",
    "/blog-4-1/finding-a-postpartum-therapist-near-you-what-to-look-for-and-what-to-ask",
    "/blog-4-1/healing-old-trauma-that-resurfaces-in-motherhood",
    "/blog-4-1/what-is-a-pmh-c-and-why-it-matters-for-your-mental-health-after-baby",
    "/blog-4-1/not-all-intrusive-thoughts-are-dangerouslets-talk-about-them",
    "/blog-4-1/therapy-for-moms-who-have-it-all-but-feel-lost",
    "/blog-4-1/youre-not-brokenyoure-a-new-mom-signs-you-might-benefit-from-postpartum-therapy",
    "/blog-4-1/i-love-my-baby-but-im-struggling-the-most-common-thoughts-moms-dont-say-out-loud",
    "/blog-4-1/emdr-for-moms-processing-reemerging-childhood-trauma-in-motherhood",
]


def fetch_page_text(path):
    """Fetch a page and return its plain text content and existing links."""
    url = SITE_URL + path
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Extract all internal links
        existing_links = re.findall(
            r'href="(?:https://www\.shamelessmamawellness\.com)?(/[^"]+)"',
            html
        )

        # Extract plain text (strip HTML)
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip().lower()

        return text, existing_links, url

    except Exception as e:
        return "", [], SITE_URL + path


def find_link_opportunities(text, existing_links):
    """
    For each service page keyword, check if:
    1. The keyword appears in the page text
    2. A link to that service page doesn't already exist
    Returns list of (keyword, target_path, context_snippet) tuples
    """
    opportunities = []

    for keyword, target_path in SERVICE_PAGES.items():
        # Skip if already linked
        if any(target_path in link for link in existing_links):
            continue

        # Check if keyword appears in text
        if keyword.lower() in text:
            # Find context snippet
            idx = text.find(keyword.lower())
            start = max(0, idx - 60)
            end = min(len(text), idx + len(keyword) + 80)
            snippet = "..." + text[start:end] + "..."

            opportunities.append({
                "keyword": keyword,
                "target_path": target_path,
                "target_url": SITE_URL + target_path,
                "context": snippet,
            })

    return opportunities


def audit_internal_links():
    """Audit all blog posts for internal linking opportunities."""
    print(f"\n{'='*60}")
    print(f"Internal Link Audit — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    all_results = []
    total_opportunities = 0

    for path in BLOG_POSTS_TO_CHECK:
        print(f"Checking: {path.split('/')[-1][:50]}...")
        text, existing_links, url = fetch_page_text(path)

        if not text:
            print(f"  ⚠️  Couldn't fetch page")
            continue

        opportunities = find_link_opportunities(text, existing_links)
        total_opportunities += len(opportunities)

        if opportunities:
            print(f"  🔗 {len(opportunities)} link opportunities found:")
            for opp in opportunities[:3]:
                print(f"     • Add link on '{opp['keyword']}' → {opp['target_path']}")
        else:
            print(f"  ✅ Well linked")

        all_results.append({
            "path": path,
            "url": url,
            "existing_link_count": len(existing_links),
            "opportunities": opportunities,
            "opportunity_count": len(opportunities),
        })

        time.sleep(1)

    # Sort by opportunity count (most needy first)
    all_results.sort(key=lambda x: x["opportunity_count"], reverse=True)

    # Save results
    os.makedirs(DATA_DIR, exist_ok=True)
    output = {
        "last_audited": datetime.datetime.now().isoformat(),
        "pages_checked": len(all_results),
        "total_link_opportunities": total_opportunities,
        "pages": all_results,
        "priority_pages": [
            {
                "path": r["path"],
                "url": r["url"],
                "opportunities": r["opportunities"][:3],
                "opportunity_count": r["opportunity_count"],
            }
            for r in all_results[:5]
            if r["opportunity_count"] > 0
        ],
    }

    links_file = os.path.join(DATA_DIR, "internal_links.json")
    with open(links_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print(f"AUDIT COMPLETE")
    print(f"  Pages checked:           {len(all_results)}")
    print(f"  Total link opportunities: {total_opportunities}")
    print(f"\nTop priority pages to update:")
    for r in all_results[:3]:
        if r["opportunity_count"] > 0:
            print(f"  • {r['path'].split('/')[-1][:45]} — {r['opportunity_count']} links to add")
    print(f"\nFull results in dashboard. Open dashboard/index.html to review.\n")

    return output


if __name__ == "__main__":
    audit_internal_links()
