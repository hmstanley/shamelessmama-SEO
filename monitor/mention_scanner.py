"""
Unlinked Mention Scanner for Shameless Mama Wellness
Finds web mentions of Marilyn or the practice that don't link back to the site.
These are "link reclamation" opportunities — email the author and ask for a link.

Run: python monitor/mention_scanner.py
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import datetime
import os
import re
import time

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data")
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")

SITE_DOMAIN = "shamelessmamawellness.com"


def load_serper_key():
    """Load Serper API key from .serperAPI file or environment variable."""
    key_file = os.path.join(REPO_ROOT, ".serperAPI")
    if os.path.exists(key_file):
        with open(key_file) as f:
            key = f.read().strip()
            if key:
                return key
    return os.environ.get("SERPER_API_KEY", "")

# Search queries to find mentions
MENTION_QUERIES = [
    '"Marilyn Coleman" therapist',
    '"Shameless Mama Wellness"',
    '"Marilyn Cross Coleman"',
    '"shamelessmamawellness.com"',
]

# Domains to skip (these are directories/aggregators, not editorial mentions)
SKIP_DOMAINS = [
    "shamelessmamawellness.com",
    "psychologytoday.com",
    "healthgrades.com",
    "google.com",
    "bing.com",
    "yahoo.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "yelp.com",
    "zocdoc.com",
]


def search_mentions(query, api_key, max_results=10):
    """Search Google via Serper.dev for mentions and return result URLs."""
    payload = json.dumps({
        "q": query,
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
        for item in data.get("organic", []):
            url = item.get("link", "")
            if url:
                results.append(url)

        return results[:max_results]

    except Exception as e:
        print(f"  Search error: {e}")
        return []


def check_page_for_link(url):
    """
    Fetch a page and check if it links back to the target site.
    Returns (has_link, mention_text_snippet)
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Check if page links to our site
        has_link = SITE_DOMAIN in html

        # Find snippet where name is mentioned
        snippet = ""
        for term in ["Marilyn Coleman", "Shameless Mama", "shamelessmama"]:
            idx = html.find(term)
            if idx > -1:
                start = max(0, idx - 100)
                end = min(len(html), idx + 200)
                raw_snippet = html[start:end]
                # Strip HTML tags from snippet
                snippet = re.sub(r"<[^>]+>", "", raw_snippet).strip()
                snippet = re.sub(r"\s+", " ", snippet)
                break

        return has_link, snippet

    except Exception:
        return None, ""  # Couldn't fetch


def get_domain(url):
    """Extract domain from URL."""
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return match.group(1) if match else ""


def load_known_links():
    """Load previously found linked mentions to avoid re-alerting."""
    known_file = os.path.join(DATA_DIR, "known_linked_mentions.json")
    if os.path.exists(known_file):
        with open(known_file) as f:
            return set(json.load(f))
    return set()


def save_known_links(known):
    """Save updated set of known linked mentions."""
    os.makedirs(DATA_DIR, exist_ok=True)
    known_file = os.path.join(DATA_DIR, "known_linked_mentions.json")
    with open(known_file, "w") as f:
        json.dump(list(known), f)


def run():
    """Main entry point."""
    print(f"\n{'='*60}")
    print(f"Mention Scanner — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Looking for: mentions of Marilyn / Shameless Mama Wellness")
    print(f"{'='*60}\n")

    api_key = load_serper_key()
    if not api_key:
        print("❌ No Serper API key found.")
        print("   Create a file called .serperAPI in the repo root with your key.")
        return {}

    known_linked = load_known_links()
    all_mentions = []
    unlinked_opportunities = []

    for query in MENTION_QUERIES:
        print(f"Searching: {query}")
        urls = search_mentions(query, api_key)
        print(f"  Found {len(urls)} results\n")

        for url in urls:
            domain = get_domain(url)

            # Skip known irrelevant domains
            if any(skip in domain for skip in SKIP_DOMAINS):
                continue

            # Skip if we've already confirmed this page links to us
            if url in known_linked:
                continue

            print(f"  Checking: {domain}...")
            has_link, snippet = check_page_for_link(url)

            if has_link is None:
                print(f"    ⚠️  Couldn't access page")
                continue

            mention = {
                "url": url,
                "domain": domain,
                "has_link": has_link,
                "snippet": snippet[:200] if snippet else "",
                "query": query,
                "found_at": datetime.datetime.now().isoformat(),
            }
            all_mentions.append(mention)

            if has_link:
                print(f"    ✅ Links back to site — great!")
                known_linked.add(url)
            else:
                print(f"    🔗 Mentions Marilyn but NO link — outreach opportunity!")
                unlinked_opportunities.append(mention)

            time.sleep(1.5)

    # Save known links
    save_known_links(known_linked)

    # Generate outreach email drafts for unlinked mentions
    outreach_drafts = []
    for opp in unlinked_opportunities:
        draft = generate_outreach_email(opp)
        outreach_drafts.append({**opp, "outreach_email": draft})

    # Save results
    os.makedirs(DATA_DIR, exist_ok=True)
    output = {
        "last_scanned": datetime.datetime.now().isoformat(),
        "total_mentions_found": len(all_mentions),
        "linked_mentions": len([m for m in all_mentions if m.get("has_link")]),
        "unlinked_opportunities": len(unlinked_opportunities),
        "opportunities": outreach_drafts,
    }

    mentions_file = os.path.join(DATA_DIR, "mentions.json")
    with open(mentions_file, "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"SCAN COMPLETE")
    print(f"  Total mentions found:   {len(all_mentions)}")
    print(f"  Already linking to you: {len([m for m in all_mentions if m.get('has_link')])}")
    print(f"  Link opportunities:     {len(unlinked_opportunities)}")

    if unlinked_opportunities:
        print(f"\n🔗 UNLINKED MENTIONS — send these outreach emails:")
        for opp in unlinked_opportunities:
            print(f"   • {opp['domain']} — {opp['url'][:60]}...")

    print(f"\nResults saved. Open dashboard to see outreach emails ready to send.\n")

    return output


def generate_outreach_email(mention):
    """Generate a polite outreach email to request a link."""
    domain = mention["domain"]
    page_url = mention["url"]

    return f"""Subject: Thank you for mentioning Shameless Mama Wellness

Hi there,

I came across your article at {page_url} and wanted to say thank you for mentioning my practice, Shameless Mama Wellness.

I wanted to reach out to see if you'd be open to adding a link to my website (https://www.shamelessmamawellness.com) where my name is mentioned. This helps readers find more information and is a small change that makes a big difference for my practice.

Completely understand if that's not possible — either way, thank you for the mention!

Warm regards,
Marilyn Coleman, LCSW, PMH-C
Shameless Mama Wellness
https://www.shamelessmamawellness.com
415.320.6842
"""


if __name__ == "__main__":
    run()
