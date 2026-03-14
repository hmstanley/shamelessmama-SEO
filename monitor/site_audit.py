"""
Site Audit for shamelessmamawellness.com
Checks technical SEO health: schema, meta tags, page speed signals, directory listings.

Run: python monitor/site_audit.py
"""

import json
import urllib.request
import urllib.error
import datetime
import os
import re

SITE_URL = "https://www.shamelessmamawellness.com"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data")

PAGES_TO_CHECK = [
    "/",
    "/about-marilyn-cross-coleman-postpartum-therapist-california",
    "/traumatic-childbirth-therapist-sacramento",
    "/postpartum-depression-treatment-in-california",
    "/postpartum-anxiety-therapy-california",
    "/emdr-postpartum-therapist-los-angeles",
    "/nicu-postpartum-therapist-san-francisco",
]

DIRECTORY_URLS = {
    "Psychology Today": "https://www.psychologytoday.com/us/therapists/marilyn-cross-coleman-san-francisco-ca/1309990",
    "Healthgrades": "https://www.healthgrades.com/search?what=Marilyn+Coleman+therapist+California",
    "Zencare": "https://zencare.co/provider/therapist/marilyn-coleman",
}


def fetch_page(url, timeout=15):
    """Fetch a page and return HTML, status code, and response time."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
    }
    start = datetime.datetime.now()
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            elapsed = (datetime.datetime.now() - start).total_seconds()
            return html, resp.status, elapsed
    except urllib.error.HTTPError as e:
        elapsed = (datetime.datetime.now() - start).total_seconds()
        return "", e.code, elapsed
    except Exception as e:
        return "", 0, 0


def check_meta(html):
    """Extract and evaluate key meta tags."""
    issues = []
    findings = {}

    # Title
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else ""
    findings["title"] = title
    if not title:
        issues.append("❌ Missing page title")
    elif len(title) > 65:
        issues.append(f"⚠️ Title too long ({len(title)} chars) — aim for under 60")
    elif len(title) < 30:
        issues.append(f"⚠️ Title very short ({len(title)} chars) — add more detail")

    # Meta description
    desc_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE
    )
    if not desc_match:
        desc_match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
            html, re.IGNORECASE
        )
    desc = desc_match.group(1).strip() if desc_match else ""
    findings["description"] = desc
    if not desc:
        issues.append("❌ Missing meta description")
    elif len(desc) > 160:
        issues.append(f"⚠️ Meta description too long ({len(desc)} chars) — aim for under 155")

    # H1
    h1_matches = re.findall(r"<h1[^>]*>([^<]+)</h1>", html, re.IGNORECASE)
    findings["h1_tags"] = [h.strip() for h in h1_matches]
    if not h1_matches:
        issues.append("❌ No H1 tag found")
    elif len(h1_matches) > 2:
        issues.append(f"⚠️ Multiple H1 tags ({len(h1_matches)}) — aim for one primary H1")

    return findings, issues


def check_schema(html):
    """Check structured data (schema.org JSON-LD)."""
    issues = []
    findings = {}

    schemas = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )

    parsed = []
    for s in schemas:
        try:
            parsed.append(json.loads(s.strip()))
        except Exception:
            issues.append("⚠️ Schema JSON parse error — malformed structured data")

    findings["schema_count"] = len(parsed)
    findings["schema_types"] = [s.get("@type", "unknown") for s in parsed]

    # Check LocalBusiness schema specifically
    for schema in parsed:
        if schema.get("@type") == "LocalBusiness":
            address = schema.get("address", "")
            findings["local_business_address"] = address
            if isinstance(address, str) and "Los Angeles" in address:
                issues.append(
                    "🔴 LocalBusiness schema has 'Los Angeles' as city — "
                    "should be San Francisco for Bay Area searches"
                )
            same_as = schema.get("sameAs", [])
            findings["same_as_links"] = same_as
            if not same_as:
                issues.append(
                    "⚠️ LocalBusiness schema has empty sameAs — "
                    "add links to Psychology Today, Google Business Profile, etc."
                )

        if schema.get("@type") == "Organization":
            same_as = schema.get("sameAs", [])
            if not same_as:
                issues.append(
                    "⚠️ Organization schema has empty sameAs — "
                    "add links to your social profiles and directory listings"
                )

    if not parsed:
        issues.append("⚠️ No structured data (schema.org) found on this page")

    return findings, issues


def check_page_speed_signals(html, load_time):
    """Check basic page speed signals."""
    issues = []

    if load_time > 3.0:
        issues.append(f"🔴 Page slow to load ({load_time:.1f}s) — aim for under 2s")
    elif load_time > 2.0:
        issues.append(f"⚠️ Page load time ({load_time:.1f}s) — aim for under 2s")

    # Count images without alt text
    img_tags = re.findall(r"<img[^>]+>", html, re.IGNORECASE)
    no_alt = sum(1 for img in img_tags if "alt=" not in img.lower())
    if no_alt > 0:
        issues.append(f"⚠️ {no_alt} images missing alt text — add descriptions for accessibility and SEO")

    return issues


def audit_page(path):
    """Audit a single page."""
    url = SITE_URL + path
    html, status, load_time = fetch_page(url)

    result = {
        "url": url,
        "status": status,
        "load_time_seconds": round(load_time, 2),
        "issues": [],
        "findings": {},
    }

    if status != 200:
        result["issues"].append(f"❌ Page returned HTTP {status}")
        return result

    meta_findings, meta_issues = check_meta(html)
    schema_findings, schema_issues = check_schema(html)
    speed_issues = check_page_speed_signals(html, load_time)

    result["findings"].update(meta_findings)
    result["findings"].update(schema_findings)
    result["issues"] = meta_issues + schema_issues + speed_issues

    return result


def check_directories():
    """Check if directory profiles are reachable."""
    results = {}
    for name, url in DIRECTORY_URLS.items():
        _, status, _ = fetch_page(url)
        results[name] = {
            "url": url,
            "status": status,
            "reachable": status == 200,
        }
    return results


def run_audit():
    """Run full site audit."""
    print(f"\n{'='*60}")
    print(f"Site Audit — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Target: {SITE_URL}")
    print(f"{'='*60}\n")

    all_results = {}
    total_issues = []

    for path in PAGES_TO_CHECK:
        print(f"Auditing: {SITE_URL + path}")
        result = audit_page(path)
        all_results[path] = result

        if result["issues"]:
            for issue in result["issues"]:
                print(f"  {issue}")
                total_issues.append({"page": path, "issue": issue})
        else:
            print(f"  ✅ No issues found ({result['load_time_seconds']}s)")

    print(f"\nChecking directory listings...")
    directories = check_directories()
    for name, info in directories.items():
        status = "✅" if info["reachable"] else "⚠️"
        print(f"  {status} {name}: {info['url']}")

    # Save results
    os.makedirs(DATA_DIR, exist_ok=True)
    output = {
        "last_updated": datetime.datetime.now().isoformat(),
        "site": SITE_URL,
        "pages": all_results,
        "directories": directories,
        "total_issues": total_issues,
        "issue_count": len(total_issues),
    }
    audit_file = os.path.join(DATA_DIR, "audit.json")
    with open(audit_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print(f"AUDIT COMPLETE — {len(total_issues)} issues found")
    print(f"{'='*60}")
    print(f"Results saved to {audit_file}")
    print("Open dashboard/index.html to see the full report.\n")

    return output


if __name__ == "__main__":
    run_audit()
