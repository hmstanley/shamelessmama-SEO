"""
Competitor Monitor for shamelessmamawellness.com
For each tracked keyword, finds top organic results, compares positions to Marilyn's site,
generates authority-based difficulty ratings, and produces a keyword gap report with
actionable recommendations.

Reads:  .serperAPI (repo root), ~/.openpagerank-api-key
Writes: dashboard/data/competitors.json, dashboard/data/keyword_gap.json

Run: python monitor/competitor_monitor.py
"""

import json
import urllib.request
import urllib.parse
import datetime
import time
import os

TARGET_SITE = "shamelessmamawellness.com"
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(REPO_ROOT, "dashboard", "data")
SERPER_KEY_FILE = os.path.join(REPO_ROOT, ".serperAPI")
OPR_KEY_FILE = os.path.expanduser("~/.openpagerank-api-key")
OUTPUT_FILE = os.path.join(DATA_DIR, "competitors.json")
GAP_FILE = os.path.join(DATA_DIR, "keyword_gap.json")

KEYWORDS = [
    "birth trauma therapist San Francisco",
    "postpartum therapist San Francisco Bay Area",
    "EMDR therapist moms California",
    "postpartum depression therapist California",
    "prenatal therapist San Francisco",
    "perinatal mental health therapist California",
    "birth trauma therapist online California",
    "postpartum anxiety therapist Bay Area",
    "mother wound therapist California",
]

DIRECTORY_DOMAINS = {
    "psychologytoday.com", "zencare.co", "therapyden.com", "yelp.com",
    "zocdoc.com", "healthgrades.com", "therapistfinder.com", "betterhelp.com",
    "talkspace.com", "goodtherapy.org", "psychology.com", "therapist.com",
    "findatherapist.com", "therapyroute.com",
}

SLUG_STOP_WORDS = {
    "the", "for", "and", "therapist", "therapy", "san", "california",
    "area", "bay", "online", "near", "with", "francisco",
}


def load_key(path):
    if os.path.exists(path):
        key = open(path).read().strip()
        if key:
            return key
    return None


def get_organic_results(keyword, serper_key, num=10):
    """Fetch top N organic results from Google via Serper.
    Returns dict with keys: results, paa, related."""
    payload = json.dumps({
        "q": keyword,
        "num": num,
        "gl": "us",
        "hl": "en",
    }).encode()
    req = urllib.request.Request(
        "https://google.serper.dev/search",
        data=payload,
        headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
        results = []
        for item in data.get("organic", [])[:num]:
            link = item.get("link", "")
            domain = link.replace("https://", "").replace("http://", "").split("/")[0]
            domain = domain.lstrip("www.")
            results.append({
                "position": item.get("position"),
                "title": item.get("title", ""),
                "url": link,
                "domain": domain,
                "snippet": item.get("snippet", ""),
                "is_target": TARGET_SITE in link,
            })
        paa = [
            {"question": p.get("question", ""), "snippet": p.get("snippet", "")}
            for p in data.get("peopleAlsoAsk", [])
        ]
        related = [r.get("query", "") for r in data.get("relatedSearches", [])]
        return {"results": results, "paa": paa, "related": related}
    except Exception as e:
        print(f"    Serper error: {e}")
        return {"results": [], "paa": [], "related": []}


def get_authority_scores(domains, opr_key):
    """Fetch Open PageRank scores for a list of domains. Returns dict of domain -> {score, rank}."""
    params = "&".join(f"domains[]={urllib.parse.quote(d)}" for d in domains)
    url = f"https://openpagerank.com/api/v1.0/getPageRank?{params}"
    req = urllib.request.Request(url, headers={"API-OPR": opr_key})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
        scores = {}
        for item in data.get("response", []):
            domain = item.get("domain", "")
            scores[domain] = {
                "score": round(item.get("page_rank_decimal", 0), 1),
                "rank": item.get("rank"),
            }
        return scores
    except Exception as e:
        print(f"    Open PageRank error: {e}")
        return {}


def difficulty_label(target_score, competitor_score):
    if competitor_score is None:
        return "Unknown"
    gap = competitor_score - (target_score or 0)
    if gap <= 0:
        return "Beatable now"
    elif gap <= 1.5:
        return "Competitive"
    elif gap <= 3:
        return "Hard"
    else:
        return "Dominant"


def difficulty_explanation(label):
    explanations = {
        "Beatable now": "Their authority is similar to yours — better content and local SEO can win here.",
        "Competitive": "They have a slight edge in authority, but consistent blogging and local citations can close the gap in 3–6 months.",
        "Hard": "They have significantly more websites linking to them. Focus on content quality and patience — this takes 6–12 months.",
        "Dominant": "This competitor has built authority over many years. Don't ignore the keyword, but don't count on outranking them soon — focus on long-tail variations instead.",
        "Unknown": "No authority data available for this site.",
    }
    return explanations.get(label, "")


def is_directory(domain):
    return domain in DIRECTORY_DOMAINS


def slug_has_keyword_match(url, keyword):
    """Return True if the URL path contains 2+ meaningful keyword words."""
    path = "/" + "/".join(url.replace("https://", "").replace("http://", "").split("/")[1:])
    path = path.lower().replace("-", " ").replace("/", " ")
    words = [w for w in keyword.lower().split() if w not in SLUG_STOP_WORDS and len(w) > 3]
    matches = sum(1 for w in words if w in path)
    return matches >= 2


def generate_action(keyword, our_position, top_competitor, paa):
    """Return (action, action_detail) explaining exactly what to do."""
    domain = top_competitor.get("domain", "")
    url = top_competitor.get("url", "")
    comp_pos = top_competitor.get("position", "?")

    if is_directory(domain):
        if "psychologytoday" in domain:
            return (
                "Directory result — ensure your Psychology Today profile is fully complete",
                f"{domain} ranks #{comp_pos}. Your PT listing exists — verify all specialties, photos, and bio fields are fully filled out.",
            )
        if "zencare" in domain:
            return (
                "Directory gap — you have no Zencare profile",
                f"{domain} ranks #{comp_pos} for this term. Zencare is a top therapist directory and you have no listing there.",
            )
        return (
            f"Directory result — verify your listing on {domain}",
            f"{domain} ranks #{comp_pos}. Make sure your profile is complete and active.",
        )

    if slug_has_keyword_match(url, keyword):
        slug_part = "/" + "/".join(url.replace("https://", "").replace("http://", "").split("/")[1:])
        return (
            "Create a dedicated page targeting this keyword",
            f"{domain} ranks #{comp_pos} with a page built for this exact term ({slug_part[:60]}). You have no equivalent page — create one.",
        )

    if paa:
        first_q = paa[0].get("question", "")
        return (
            f'Add an FAQ section answering: "{first_q}"',
            f"{domain} ranks #{comp_pos}. Answering this question directly on your page (clear heading + 2–3 sentence answer) can earn the People Also Ask placement.",
        )

    if our_position and our_position <= 10:
        return (
            "Strengthen your existing page — update title tag and expand content depth",
            f"You rank #{our_position}, {domain} ranks #{comp_pos}. More comprehensive content and a rewritten title/meta description can close this gap.",
        )

    return (
        "Create or expand content targeting this keyword",
        f"{domain} ranks #{comp_pos}. You are not in the top 10. Create a page that directly addresses this search intent.",
    )


def run():
    serper_key = load_key(SERPER_KEY_FILE)
    opr_key = load_key(OPR_KEY_FILE)

    if not serper_key:
        print("No Serper API key found at .serperAPI")
        return {}
    if not opr_key:
        print(f"No Open PageRank key found at {OPR_KEY_FILE}")
        return {}

    print(f"\nCompetitor Monitor — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Fetching authority score for {TARGET_SITE}...")
    target_scores = get_authority_scores([TARGET_SITE], opr_key)
    target_score = target_scores.get(TARGET_SITE, {}).get("score")
    print(f"  {TARGET_SITE}: {target_score}/10" if target_score else f"  {TARGET_SITE}: score unavailable")

    keyword_results = []
    gaps = []
    improvements = []
    wins = []
    discovered_map = {}  # keyword/question -> {source, from_keyword}

    for keyword in KEYWORDS:
        print(f"\n  Keyword: {keyword}")
        serp = get_organic_results(keyword, serper_key)
        results = serp["results"]
        paa = serp["paa"]
        related = serp["related"]

        # Collect keyword discovery candidates from PAA and related searches
        for p in paa:
            q = p.get("question", "").strip()
            if q and q not in discovered_map:
                discovered_map[q] = {"source": "paa", "from_keyword": keyword}
        for r in related:
            if r and r not in discovered_map:
                discovered_map[r] = {"source": "related", "from_keyword": keyword}

        if not results:
            keyword_results.append({"keyword": keyword, "competitors": [], "target_position": None})
            time.sleep(0.5)
            continue

        target_position = next((r["position"] for r in results if r["is_target"]), None)
        competitors = [r for r in results if not r["is_target"]]

        # Fetch authority scores for all competitor domains in one call
        domains = list({r["domain"] for r in competitors})
        scores = get_authority_scores(domains, opr_key)

        enriched = []
        for r in competitors:
            comp_score = scores.get(r["domain"], {}).get("score")
            label = difficulty_label(target_score, comp_score)
            enriched.append({
                "position": r["position"],
                "title": r["title"],
                "url": r["url"],
                "domain": r["domain"],
                "snippet": r["snippet"],
                "authority_score": comp_score,
                "difficulty": label,
                "difficulty_explanation": difficulty_explanation(label),
                "is_directory": is_directory(r["domain"]),
            })
            print(f"    #{r['position']} {r['domain']} — authority {comp_score}/10 — {label}")

        if target_position:
            print(f"    Marilyn ranks #{target_position} for this keyword")
        else:
            print(f"    Marilyn not in top 10 for this keyword")

        keyword_results.append({
            "keyword": keyword,
            "target_position": target_position,
            "competitors": enriched,
        })

        # Gap analysis — classify keyword and generate action
        if not enriched:
            time.sleep(0.5)
            continue

        # Prefer a real site over a directory as the benchmark competitor
        real_comps = [c for c in enriched if not c["is_directory"]]
        top_competitor = sorted(real_comps, key=lambda c: c["position"])[0] if real_comps else sorted(enriched, key=lambda c: c["position"])[0]

        if target_position is None:
            classification = "gap"
        elif target_position < top_competitor["position"]:
            classification = "win"
        else:
            classification = "improvement"

        action, action_detail = generate_action(keyword, target_position, top_competitor, paa)

        entry = {
            "keyword": keyword,
            "our_position": target_position,
            "classification": classification,
            "top_competitor": {
                "domain": top_competitor["domain"],
                "position": top_competitor["position"],
                "url": top_competitor["url"],
                "title": top_competitor["title"],
                "is_directory": is_directory(top_competitor["domain"]),
            },
            "serp_has_paa": len(paa) > 0,
            "paa_questions": [p["question"] for p in paa[:3]],
            "action": action,
            "action_detail": action_detail,
        }

        if classification == "gap":
            gaps.append(entry)
        elif classification == "improvement":
            improvements.append(entry)
        else:
            wins.append(entry)

        time.sleep(0.5)

    os.makedirs(DATA_DIR, exist_ok=True)

    # Write competitors.json (existing format, unchanged)
    output = {
        "last_updated": datetime.datetime.now().isoformat(),
        "target_site": TARGET_SITE,
        "target_authority_score": target_score,
        "keywords": keyword_results,
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved competitors.json")

    # Write keyword_gap.json — filter out keywords already in our tracked list
    tracked_lower = {k.lower() for k in KEYWORDS}
    discovered = [
        {"keyword": kw, "source": meta["source"], "from_keyword": meta["from_keyword"]}
        for kw, meta in discovered_map.items()
        if kw.lower() not in tracked_lower
    ]

    gap_output = {
        "last_updated": datetime.datetime.now().isoformat(),
        "summary": {
            "gap_count": len(gaps),
            "improvement_count": len(improvements),
            "win_count": len(wins),
            "discovered_keywords_count": len(discovered),
        },
        "gaps": gaps,
        "improvements": improvements,
        "wins": wins,
        "discovered_keywords": discovered[:25],
    }
    with open(GAP_FILE, "w") as f:
        json.dump(gap_output, f, indent=2)
    print(f"Saved keyword_gap.json")

    return output


if __name__ == "__main__":
    run()
