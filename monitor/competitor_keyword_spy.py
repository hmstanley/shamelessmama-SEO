"""
Competitor Keyword Spy for shamelessmamawellness.com

For each real (non-directory) competitor, fetches their sitemap, extracts
keyword targets from URL slugs, then checks how well we cover those keywords
on our own site.

Reads:  dashboard/data/competitors.json, dashboard/data/audit.json
Writes: dashboard/data/competitor_keywords.json

Run: python monitor/competitor_keyword_spy.py
"""

import json
import urllib.request
import xml.etree.ElementTree as ET
import datetime
import time
import os
import re
from urllib.parse import urlparse

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(REPO_ROOT, "dashboard", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "competitor_keywords.json")
TARGET_SITE = "shamelessmamawellness.com"

DIRECTORY_DOMAINS = {
    "psychologytoday.com", "zencare.co", "therapyden.com", "yelp.com",
    "zocdoc.com", "healthgrades.com", "therapistfinder.com", "betterhelp.com",
    "talkspace.com", "goodtherapy.org", "psychology.com", "therapist.com",
    "findatherapist.com", "therapyroute.com",
}

STOP_WORDS = {
    "the", "for", "and", "in", "of", "to", "a", "an", "with", "at", "by",
    "from", "or", "on", "is", "are", "was", "my", "your", "our", "how",
    "what", "why", "when", "where", "who", "get", "help", "find",
}

SKIP_SEGMENTS = {
    "about", "contact", "privacy", "terms", "faq", "team", "staff",
    "sitemap", "feed", "login", "register", "tag", "category", "author",
    "testimonials", "press", "media", "cart", "checkout", "account",
    "search", "404", "home", "index", "page", "fees", "insurance",
    "rates", "billing", "policies", "resources", "newsletter",
}

# Therapist credentials — presence in a slug means it's a staff/bio page
CREDENTIAL_WORDS = {"lmft", "amft", "mft", "phd", "lcsw", "psyd", "asw", "pcc", "lpcc", "md"}

MAX_KEYWORD_WORDS = 6
MAX_PAGES_PER_COMPETITOR = 50
MAX_COMPETITORS = 8


def is_directory(domain):
    return domain in DIRECTORY_DOMAINS


def fetch_sitemap_from_url(sitemap_url):
    """Fetch a single sitemap and return all page URLs found."""
    try:
        req = urllib.request.Request(sitemap_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
        root = ET.fromstring(content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = []
        for url_el in root.findall("sm:url", ns):
            loc = url_el.find("sm:loc", ns)
            if loc is not None:
                urls.append(loc.text.strip())
        return urls
    except Exception:
        return []


def fetch_sitemap_urls(domain):
    """Try common sitemap paths for a domain. Returns list of page URLs."""
    sitemap_paths = [
        "/sitemap.xml", "/sitemap_index.xml",
        "/wp-sitemap.xml", "/page-sitemap.xml",
    ]
    for path in sitemap_paths:
        try:
            url = f"https://{domain}{path}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read()
            root = ET.fromstring(content)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Sitemap index — collect child sitemaps
            child_sitemaps = root.findall("sm:sitemap", ns)
            if child_sitemaps:
                all_urls = []
                for sm in child_sitemaps[:5]:
                    loc = sm.find("sm:loc", ns)
                    if loc is not None:
                        all_urls.extend(fetch_sitemap_from_url(loc.text.strip()))
                if all_urls:
                    return all_urls

            # Regular sitemap
            urls = []
            for url_el in root.findall("sm:url", ns):
                loc = url_el.find("sm:loc", ns)
                if loc is not None:
                    urls.append(loc.text.strip())
            if urls:
                return urls
        except Exception:
            continue
    return []


def slug_to_keyword(url):
    """Convert a URL path into a keyword string. Returns None if not useful."""
    path = urlparse(url).path.rstrip("/")
    if not path or path == "/":
        return None

    segments = [s for s in path.split("/") if s]

    # Skip URLs where any word in any segment matches the skip list
    all_words = []
    for seg in segments:
        all_words.extend(re.split(r"[-_]", seg.lower()))
    if any(w in SKIP_SEGMENTS for w in all_words):
        return None

    # Skip numeric-only segments (pagination, IDs)
    if any(seg.isdigit() for seg in segments):
        return None

    # Use the most specific (last) segment
    slug = segments[-1]

    words = re.split(r"[-_]", slug.lower())

    # Skip if slug contains therapist credentials (staff/bio page)
    if any(w in CREDENTIAL_WORDS for w in words):
        return None

    words = [w for w in words if len(w) >= 3 and w not in STOP_WORDS]

    if len(words) < 2:
        return None

    # Trim to max words (long slugs = blog post titles, not service keywords)
    words = words[:MAX_KEYWORD_WORDS]

    return " ".join(words)


def load_our_pages():
    """Load our page data from audit.json for keyword matching."""
    audit_file = os.path.join(DATA_DIR, "audit.json")
    if not os.path.exists(audit_file):
        return {}
    with open(audit_file) as f:
        audit = json.load(f)
    pages = {}
    for path, data in audit.get("pages", {}).items():
        findings = data.get("findings", {})
        slug_text = path.lower().replace("-", " ").replace("/", " ")
        title = findings.get("title", "").lower()
        description = findings.get("description", "").lower()
        searchable = f"{slug_text} {title} {description}"
        pages[path] = {
            "title": findings.get("title", ""),
            "searchable": searchable,
        }
    return pages


def match_keyword(keyword, our_pages):
    """
    Check how well a competitor keyword is covered by our pages.
    Returns (match_type, page_path, page_title)
    match_type: "full", "partial", or "none"
    """
    kw_words = set(keyword.lower().split()) - STOP_WORDS
    if len(kw_words) < 2:
        return "none", None, None

    best_score = 0.0
    best_page = None
    best_title = None

    for path, data in our_pages.items():
        page_words = set(re.split(r"\W+", data["searchable"]))
        overlap = kw_words & page_words
        score = len(overlap) / len(kw_words)
        if score > best_score:
            best_score = score
            best_page = path
            best_title = data["title"]

    if best_score >= 0.65:
        return "full", best_page, best_title
    elif best_score >= 0.3:
        return "partial", best_page, best_title
    else:
        return "none", None, None


def run():
    comp_file = os.path.join(DATA_DIR, "competitors.json")
    if not os.path.exists(comp_file):
        print("No competitors.json found — run competitor_monitor.py first")
        return

    with open(comp_file) as f:
        comp_data = json.load(f)

    # Count how often each real competitor domain appears across keyword checks
    domain_frequency = {}
    for kw_data in comp_data.get("keywords", []):
        for c in kw_data.get("competitors", []):
            domain = c.get("domain", "")
            if not is_directory(domain) and domain != TARGET_SITE:
                domain_frequency[domain] = domain_frequency.get(domain, 0) + 1

    top_domains = sorted(domain_frequency.items(), key=lambda x: x[1], reverse=True)[:MAX_COMPETITORS]

    print(f"\nCompetitor Keyword Spy — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Analyzing {len(top_domains)} competitors")

    our_pages = load_our_pages()
    print(f"Loaded {len(our_pages)} of our pages for matching\n")

    results = []

    for domain, freq in top_domains:
        print(f"  {domain} (seen in {freq} keyword searches)")

        urls = fetch_sitemap_urls(domain)
        print(f"    {len(urls)} pages in sitemap")

        if not urls:
            results.append({
                "domain": domain,
                "frequency": freq,
                "pages_found": 0,
                "keywords": [],
                "summary": {"total": 0, "gaps": 0, "partial": 0, "covered": 0},
                "note": "No sitemap accessible",
            })
            time.sleep(0.3)
            continue

        # Extract keywords from URLs, deduplicate
        seen_keywords = set()
        keyword_entries = []

        for url in urls[:MAX_PAGES_PER_COMPETITOR]:
            keyword = slug_to_keyword(url)
            if not keyword or keyword in seen_keywords:
                continue
            seen_keywords.add(keyword)

            match_type, match_page, match_title = match_keyword(keyword, our_pages)
            keyword_entries.append({
                "keyword": keyword,
                "source_url": url,
                "our_match": match_type,
                "our_match_page": match_page,
                "our_match_title": match_title,
            })

        # Sort: gaps first, then partial, then covered
        order = {"none": 0, "partial": 1, "full": 2}
        keyword_entries.sort(key=lambda x: order.get(x["our_match"], 0))

        gap_count     = sum(1 for k in keyword_entries if k["our_match"] == "none")
        partial_count = sum(1 for k in keyword_entries if k["our_match"] == "partial")
        full_count    = sum(1 for k in keyword_entries if k["our_match"] == "full")

        print(f"    {len(keyword_entries)} keywords — {gap_count} gaps · {partial_count} partial · {full_count} covered")

        results.append({
            "domain": domain,
            "frequency": freq,
            "pages_found": len(urls),
            "keywords": keyword_entries,
            "summary": {
                "total": len(keyword_entries),
                "gaps": gap_count,
                "partial": partial_count,
                "covered": full_count,
            },
        })
        time.sleep(0.3)

    os.makedirs(DATA_DIR, exist_ok=True)
    output = {
        "last_updated": datetime.datetime.now().isoformat(),
        "competitors": results,
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved competitor_keywords.json")
    return output


if __name__ == "__main__":
    run()
