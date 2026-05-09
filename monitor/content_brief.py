"""
Content Brief Generator for Shameless Mama Wellness
Analyzes competitor content gaps and generates ready-to-use blog post briefs.
Marilyn (or an AI) can use these briefs to write the next blog post quickly.

Run: python monitor/content_brief.py

Output: drafts/blog_briefs/YYYY-MM-DD-brief-[keyword].md
"""

import json
import urllib.request
import urllib.parse
import datetime
import os
import re
import time
import sys
sys.path.insert(0, os.path.dirname(__file__))
from credits_tracker import track_usage, print_status as print_credit_status

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "config.json")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data")
BRIEFS_DIR = os.path.join(os.path.dirname(__file__), "..", "drafts", "blog_briefs")

SITE_URL = "https://www.shamelessmamawellness.com"

# Marilyn's existing blog topics (from sitemap — to avoid duplication)
EXISTING_TOPICS = [
    "postpartum anxiety vs postpartum depression",
    "what is postpartum anxiety like",
    "how long does postpartum anxiety last",
    "how can i calm postpartum anxiety",
    "can my anxiety affect my baby",
    "postpartum therapy california",
    "finding a postpartum therapist near you",
    "healing old trauma in motherhood",
    "emdr therapy for moms",
    "the mother wound",
    "generational trauma mother wound",
    "birth trauma is real",
    "emdr intensives for birth trauma",
    "what is birth trauma",
    "traumatic childbirth therapy",
    "returning to work after baby",
    "when to call a therapist new mom",
    "rainbow baby",
    "miscarriage grief",
    "NICU mental health",
    "postpartum intrusive thoughts",
]

# High-value keyword opportunities not yet covered
KEYWORD_OPPORTUNITIES = [
    "how to find a perinatal mental health therapist",
    "EMDR vs CBT for postpartum depression",
    "postpartum rage what it is",
    "birth trauma vs PTSD difference",
    "partner support postpartum depression",
    "breastfeeding anxiety therapy",
    "postpartum OCD signs",
    "secondary infertility grief",
    "NICU parent mental health",
    "postpartum depression in adoptive mothers",
    "birth trauma checklist signs",
    "EMDR intensive vs weekly therapy",
    "what is PMH-C certification",
    "perinatal mental health California insurance",
    "postpartum depression dads partners",
    "fertility treatment anxiety therapy",
    "pregnancy after loss anxiety",
    "postpartum psychosis warning signs",
    "birth plan disappointment processing",
    "C-section birth trauma",
]

MARILYN_VOICE_GUIDE = """
Writing style for Marilyn Coleman's blog:
- Warm, direct, and compassionate — like talking to a trusted friend who happens to be an expert
- Uses "you" to speak directly to the reader (new moms)
- Validates feelings before offering information ("What you're feeling is real and valid...")
- Avoids jargon — explains clinical terms in plain language
- Includes personal warmth — she genuinely cares about her clients
- San Francisco Bay Area focus but serves all of California
- Credentials to weave in naturally: LCSW, PMH-C, EMDR trained
- End every post with a gentle CTA: book a free consultation
"""


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def fetch_competitor_content(keyword):
    """Find what top-ranking pages cover for a keyword."""
    encoded = urllib.parse.quote_plus(keyword)
    url = f"https://search.yahoo.com/search?p={encoded}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
    }

    competitor_info = []
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Extract top result titles and URLs
        title_pattern = r'<div class="compTitle[^"]*".*?<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(title_pattern, html, re.DOTALL)

        for url_found, title in matches[:5]:
            title = re.sub(r"<[^>]+>", "", title).strip()
            if url_found.startswith("http") and "yahoo.com" not in url_found:
                competitor_info.append({"url": url_found, "title": title})

    except Exception as e:
        pass

    return competitor_info


def generate_brief_with_ai(keyword, competitors, api_key):
    """Use Claude to generate a full blog post brief."""
    competitor_titles = "\n".join(
        [f"- {c['title']} ({c['url'][:50]}...)" for c in competitors[:5]]
    )

    prompt = f"""Generate a detailed blog post brief for Marilyn Coleman, a postpartum and birth trauma therapist in California.

Target keyword: "{keyword}"

Top competing articles for this keyword:
{competitor_titles if competitor_titles else "(no competitor data available)"}

Marilyn's existing blog covers: postpartum anxiety, postpartum depression, birth trauma, EMDR, the mother wound, miscarriage, and NICU parenting.

Writing style guide:
{MARILYN_VOICE_GUIDE}

Create a blog post brief with:

1. **Recommended Title** (SEO-optimized, 55-65 characters, includes keyword)
2. **Meta Description** (150-155 characters, compelling, includes keyword)
3. **Target Reader** (who is this for, what are they feeling/searching)
4. **Word Count Target** (800-1500 words recommended)
5. **Outline** (H2 and H3 headers — cover what competitors miss, add Marilyn's unique clinical perspective)
6. **Key Points to Cover** (bullet list of must-include information)
7. **Marilyn's Unique Angle** (what she can say that generic sites can't — her clinical expertise, EMDR specialty, personal warmth)
8. **Internal Links to Add** (which of her existing service pages to link to naturally)
9. **Call to Action** (how to end the post)
10. **Related Keywords to Weave In** (3-5 secondary keywords)

Be specific and practical — this brief should let Marilyn (or an AI) write the post immediately."""

    try:
        payload = json.dumps({
            "model": "claude-opus-4-5",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}]
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            result = json.load(resp)

        # Track token usage for credit monitoring
        usage = result.get("usage", {})
        credit_info = track_usage(
            script_name="content_brief.py",
            model=result.get("model", "claude-opus-4-5"),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )
        if credit_info["low_balance"]:
            print(f"  ⚠️  Low credits: ~${credit_info['estimated_remaining']:.2f} remaining "
                  f"(auto-renew will fire soon)")

        return result["content"][0]["text"]

    except Exception as e:
        return f"""[AI brief generation not available — add anthropic_api_key to config.json]

Manual brief for: {keyword}

Suggested outline:
- What is {keyword}? (definition in plain language)
- Signs and symptoms to watch for
- How it affects new mothers specifically
- When to seek professional help
- How therapy (especially EMDR) can help
- Marilyn's approach / what to expect
- CTA: Book a free consultation
"""


def generate_basic_brief(keyword):
    """Generate a basic brief without AI (fallback)."""
    return f"""# Blog Brief: {keyword}

**Target Keyword:** {keyword}

**Recommended Title Options:**
- "{keyword.title()} — What Every New Mom Should Know"
- "Understanding {keyword.title()}: A Therapist's Guide"
- "{keyword.title()}: Signs, Causes, and How to Get Help"

**Word Count:** 900-1,200 words

**Outline:**
## What is {keyword}?
(Plain language definition, normalize the experience)

## Signs You Might Be Experiencing This
(Concrete, relatable symptoms — validate the reader)

## Why This Happens to New Moms
(Compassionate explanation of causes)

## How Long Does This Last?
(Reassurance + realistic timeline)

## When Should I Seek Help?
(Clear guidance, lower the barrier to reaching out)

## How Therapy — Especially EMDR — Can Help
(Marilyn's unique angle, explain the approach briefly)

## You Don't Have to Go Through This Alone
(Warm CTA: Book a free consultation at shamelessmamawellness.com)

**Internal Links to Add:**
- Link "EMDR therapy" → /emdr-postpartum-therapist-los-angeles
- Link "postpartum therapist" → /postpartum-therapist-california
- Link "free consultation" → /book-an-appointment

**Keywords to Weave In:**
- postpartum therapist California
- EMDR for moms
- perinatal mental health
- birth trauma therapist
- San Francisco Bay Area therapist
"""


def save_brief(keyword, brief_content):
    """Save a blog brief to the drafts folder."""
    os.makedirs(BRIEFS_DIR, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    safe_keyword = re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-")[:50]
    filename = f"{date_str}-brief-{safe_keyword}.md"
    filepath = os.path.join(BRIEFS_DIR, filename)

    with open(filepath, "w") as f:
        f.write(f"# Blog Brief\n")
        f.write(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(brief_content)

    return filepath


def run(num_briefs=3):
    """Generate briefs for the top N keyword opportunities."""
    print(f"\n{'='*60}")
    print(f"Content Brief Generator — {datetime.datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*60}\n")

    config = load_config()
    api_key = config.get("anthropic_api_key", "")
    use_ai = api_key and not api_key.startswith("sk-ant-...")

    if use_ai:
        print("✅ AI brief generation enabled\n")
    else:
        print("ℹ️  Generating basic briefs (add anthropic_api_key to config.json for AI briefs)\n")

    briefs_generated = []

    for i, keyword in enumerate(KEYWORD_OPPORTUNITIES[:num_briefs]):
        print(f"[{i+1}/{num_briefs}] Generating brief for: {keyword}")

        # Get competitor context
        print(f"  Fetching competitor data...")
        competitors = fetch_competitor_content(keyword)
        print(f"  Found {len(competitors)} competitor articles")

        # Generate brief
        if use_ai:
            print(f"  Generating AI brief...")
            brief = generate_brief_with_ai(keyword, competitors, api_key)
        else:
            brief = generate_basic_brief(keyword)

        # Save
        filepath = save_brief(keyword, brief)
        print(f"  ✅ Saved: {os.path.basename(filepath)}\n")

        briefs_generated.append({
            "keyword": keyword,
            "filename": os.path.basename(filepath),
            "competitors_found": len(competitors),
            "ai_generated": use_ai,
        })

        time.sleep(2)  # Rate limiting

    # Save summary for dashboard
    os.makedirs(DATA_DIR, exist_ok=True)
    summary = {
        "last_generated": datetime.datetime.now().isoformat(),
        "briefs_ready": len(briefs_generated),
        "briefs": briefs_generated,
        "total_opportunities": len(KEYWORD_OPPORTUNITIES),
    }
    with open(os.path.join(DATA_DIR, "content_briefs.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(f"{'='*60}")
    print(f"DONE — {len(briefs_generated)} blog briefs ready")
    print(f"Find them in: drafts/blog_briefs/")
    print(f"{len(KEYWORD_OPPORTUNITIES) - num_briefs} more opportunities waiting for next run")
    print(f"{'='*60}\n")

    if use_ai:
        print_credit_status()

    return briefs_generated


if __name__ == "__main__":
    run(num_briefs=3)
