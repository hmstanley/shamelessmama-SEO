"""
Quoted / HARO Monitor for Shameless Mama Wellness
Reads Quoted digest emails, finds relevant journalist queries,
and drafts expert quote responses Marilyn can review and send.

Setup:
  1. Forward your Quoted digest emails to a Gmail account
  2. Set GMAIL_EMAIL and GMAIL_APP_PASSWORD in config.json
  3. Set ANTHROPIC_API_KEY in config.json (for AI draft generation)

Run: python monitor/quoted_monitor.py

Output: dashboard/data/quoted_opportunities.json + draft responses
"""

import json
import imaplib
import email
import email.header
import datetime
import os
import re
import urllib.request

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "config.json")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data")
DRAFTS_DIR = os.path.join(os.path.dirname(__file__), "..", "drafts", "quoted")

# Keywords that indicate a relevant Quoted query for Marilyn
RELEVANT_KEYWORDS = [
    "postpartum", "birth trauma", "maternal", "perinatal", "prenatal",
    "pregnancy", "new mom", "new mother", "motherhood", "breastfeeding",
    "postpartum depression", "postpartum anxiety", "EMDR", "trauma therapist",
    "mental health", "therapist", "LCSW", "counselor", "anxiety", "depression",
    "baby blues", "birth experience", "NICU", "miscarriage", "fertility",
    "mother wound", "parenting", "infant", "newborn", "mom",
]

MARILYN_BIO = """
Marilyn Cross Coleman, LCSW, PMH-C is a licensed clinical social worker and
Perinatal Mental Health Certified (PMH-C) therapist specializing in postpartum
depression, postpartum anxiety, birth trauma, and EMDR therapy for mothers.
She serves clients in the San Francisco Bay Area, Sacramento, Los Angeles, and
throughout California via online therapy. Her practice, Shameless Mama Wellness,
provides boutique postpartum and perinatal mental health treatment.
Website: https://www.shamelessmamawellness.com
"""


def load_config():
    """Load configuration from config.json."""
    if not os.path.exists(CONFIG_FILE):
        print("⚠️  config.json not found. Creating template...")
        template = {
            "gmail_email": "your-email@gmail.com",
            "gmail_app_password": "your-16-char-app-password",
            "anthropic_api_key": "sk-ant-...",
            "quoted_sender": "query@quoted.com",
            "notify_email": "marilyn@shamelessmamawellness.com"
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(template, f, indent=2)
        print(f"Created {CONFIG_FILE} — please fill in your credentials.")
        return None
    with open(CONFIG_FILE) as f:
        return json.load(f)


def fetch_quoted_emails(config, days_back=1):
    """Connect to Gmail via IMAP and fetch recent Quoted digest emails."""
    print("Connecting to Gmail...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(config["gmail_email"], config["gmail_app_password"])
        mail.select("inbox")

        # Search for Quoted emails from the last N days
        since_date = (datetime.datetime.now() - datetime.timedelta(days=days_back))
        date_str = since_date.strftime("%d-%b-%Y")

        quoted_sender = config.get("quoted_sender", "query@quoted.com")
        _, message_ids = mail.search(
            None,
            f'(FROM "{quoted_sender}" SINCE "{date_str}")'
        )

        emails = []
        for msg_id in message_ids[0].split():
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            # Get text content
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            emails.append({
                "subject": str(email.header.make_header(email.header.decode_header(msg["Subject"]))),
                "date": msg["Date"],
                "body": body,
            })

        mail.logout()
        print(f"Found {len(emails)} Quoted email(s) from the last {days_back} day(s)")
        return emails

    except Exception as e:
        print(f"❌ Gmail connection failed: {e}")
        print("   Check your Gmail App Password in config.json")
        print("   (Settings → Security → 2-Step Verification → App Passwords)")
        return []


def parse_queries(email_body):
    """
    Extract individual journalist queries from a Quoted digest email.
    Returns list of query dicts with subject, category, deadline, details, email.
    """
    queries = []

    # Quoted typically separates queries with lines of dashes or double newlines
    # Each query has a subject, category, deadline, and journalist email
    blocks = re.split(r"\n[-=]{20,}\n|\n\n\n+", email_body)

    for block in blocks:
        block = block.strip()
        if len(block) < 50:
            continue

        query = {}

        # Extract subject/title (usually first non-empty line)
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if lines:
            query["title"] = lines[0]

        # Extract category
        cat_match = re.search(r"Category:\s*(.+)", block, re.IGNORECASE)
        query["category"] = cat_match.group(1).strip() if cat_match else "Unknown"

        # Extract deadline
        dead_match = re.search(r"Deadline:\s*(.+)", block, re.IGNORECASE)
        query["deadline"] = dead_match.group(1).strip() if dead_match else "Check email"

        # Extract journalist email
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", block)
        query["journalist_email"] = email_match.group(0) if email_match else ""

        # Full query text
        query["full_text"] = block
        query["relevance_score"] = score_relevance(block)
        query["is_relevant"] = query["relevance_score"] > 0

        if query.get("title"):
            queries.append(query)

    return queries


def score_relevance(text):
    """Score how relevant a query is to Marilyn's expertise. Higher = more relevant."""
    text_lower = text.lower()
    score = 0
    matched = []

    for keyword in RELEVANT_KEYWORDS:
        if keyword.lower() in text_lower:
            score += 1
            matched.append(keyword)

    return score


def draft_response(query, api_key):
    """Use Claude API to draft a response for a relevant query."""
    if not api_key or api_key.startswith("sk-ant-..."):
        return "[AI drafting not configured — add anthropic_api_key to config.json]"

    prompt = f"""You are helping Marilyn Coleman draft an expert quote response for a journalist query on Quoted (formerly HARO).

About Marilyn:
{MARILYN_BIO}

The journalist query is:
{query['full_text']}

Write a professional expert response that:
1. Directly answers the journalist's question with specific, useful information
2. Draws on Marilyn's expertise in postpartum mental health, birth trauma, and EMDR
3. Sounds warm and human — not robotic or overly clinical
4. Is 150-250 words (journalists prefer concise, quotable responses)
5. Ends with Marilyn's credentials: Marilyn Cross Coleman, LCSW, PMH-C | Shameless Mama Wellness | shamelessmamawellness.com

Write only the response text — no preamble, no "Here is a draft:" header."""

    try:
        payload = json.dumps({
            "model": "claude-opus-4-5",
            "max_tokens": 600,
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
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.load(resp)
            return result["content"][0]["text"]

    except Exception as e:
        return f"[Draft generation failed: {e}]"


def save_opportunity(query, draft, index):
    """Save an opportunity and its draft to the drafts folder."""
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    filename = f"{date_str}-opportunity-{index+1:02d}.md"
    filepath = os.path.join(DRAFTS_DIR, filename)

    content = f"""# Quoted Opportunity #{index+1}
Date: {date_str}
Relevance Score: {query['relevance_score']}/10
Journalist Email: {query.get('journalist_email', 'Not found')}
Deadline: {query.get('deadline', 'Check email')}
Category: {query.get('category', 'Unknown')}

---

## Journalist Query

{query['full_text']}

---

## Draft Response (Review and Edit Before Sending)

{draft}

---

## How to Send

1. Review the draft above — edit anything that doesn't sound like you
2. Add any personal story or specific example that fits
3. Email it to: {query.get('journalist_email', '[check original email]')}
4. Subject line: Re: {query.get('title', 'Your Query')}
5. If published, ask for a link to shamelessmamawellness.com

"""
    with open(filepath, "w") as f:
        f.write(content)
    return filepath


def run():
    """Main entry point."""
    print(f"\n{'='*60}")
    print(f"Quoted Monitor — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    config = load_config()
    if not config:
        return

    # Check if credentials are filled in
    if "your-email" in config.get("gmail_email", ""):
        print("⚠️  Gmail credentials not configured yet.")
        print("   Edit config.json with your Gmail address and App Password.")
        print("   See docs/quoted-setup.md for instructions.\n")

        # Demo mode — show what it would do
        print("DEMO MODE — showing sample output:\n")
        demo_query = {
            "title": "Expert quotes needed: Postpartum depression symptoms first-time moms",
            "category": "Health & Wellness",
            "deadline": "Tomorrow 5pm EST",
            "journalist_email": "journalist@example.com",
            "full_text": "I'm writing an article for a major parenting publication about postpartum depression in first-time mothers. Looking for quotes from licensed therapists or mental health professionals who specialize in maternal mental health. Questions: What are the most overlooked symptoms? How do you know when to seek help? What's the first step?",
            "relevance_score": 8,
            "is_relevant": True,
        }
        print(f"Found opportunity: {demo_query['title']}")
        print(f"Relevance: {demo_query['relevance_score']}/10 ⭐")
        print(f"Deadline: {demo_query['deadline']}")
        print("\n(With credentials configured, a draft response would be generated automatically)")
        return

    emails = fetch_quoted_emails(config, days_back=1)
    if not emails:
        print("No new Quoted emails found today.")
        # Save empty results
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(os.path.join(DATA_DIR, "quoted_opportunities.json"), "w") as f:
            json.dump({"last_checked": datetime.datetime.now().isoformat(), "opportunities": []}, f)
        return

    all_opportunities = []
    draft_count = 0

    for email_data in emails:
        print(f"Processing: {email_data['subject']}")
        queries = parse_queries(email_data["body"])
        relevant = [q for q in queries if q["is_relevant"]]
        print(f"  Found {len(queries)} queries, {len(relevant)} relevant to Marilyn\n")

        for i, query in enumerate(sorted(relevant, key=lambda q: q["relevance_score"], reverse=True)):
            print(f"  📌 [{query['relevance_score']}/10] {query['title']}")
            print(f"     Deadline: {query.get('deadline', '?')}")

            # Generate draft
            print(f"     Drafting response...")
            draft = draft_response(query, config.get("anthropic_api_key", ""))

            # Save draft file
            filepath = save_opportunity(query, draft, draft_count)
            print(f"     ✅ Draft saved: {os.path.basename(filepath)}\n")

            all_opportunities.append({
                **query,
                "draft_file": os.path.basename(filepath),
                "drafted_at": datetime.datetime.now().isoformat(),
            })
            draft_count += 1

    # Save JSON for dashboard
    os.makedirs(DATA_DIR, exist_ok=True)
    output = {
        "last_checked": datetime.datetime.now().isoformat(),
        "opportunities_found": len(all_opportunities),
        "opportunities": all_opportunities[:10],  # Top 10 for dashboard
    }
    with open(os.path.join(DATA_DIR, "quoted_opportunities.json"), "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print(f"DONE — {draft_count} draft responses created")
    print(f"Find your drafts in: drafts/quoted/")
    print(f"Review each one, edit to sound like you, then send!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()
