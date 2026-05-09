"""
iCloud Email Monitor for Will Coleman
Connects via IMAP (read-only) and writes a digest to dashboard/data/email_digest.json.

Run: python monitor/email_monitor.py
"""

import imaplib
import email
from email.header import decode_header
import json
import os
import datetime

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
CONFIG_FILE = os.path.join(REPO_ROOT, "config.json")
DATA_DIR = os.path.join(REPO_ROOT, "dashboard", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "email_digest.json")

IMAP_HOST = "imap.mail.me.com"
IMAP_PORT = 993
MAX_EMAILS = 20  # fetch most recent N unread emails


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


def decode_str(value):
    """Decode encoded email headers cleanly."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, encoding in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(encoding or "utf-8", errors="ignore"))
        else:
            decoded.append(part)
    return " ".join(decoded).strip()


def get_body(msg):
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="ignore"
                    )[:500]  # first 500 chars is enough for digest
                except Exception:
                    return ""
    else:
        try:
            return msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="ignore"
            )[:500]
        except Exception:
            return ""
    return ""


def run():
    config = load_config()
    email_addr = config.get("icloud_email")
    password = config.get("icloud_app_password")

    if not email_addr or not password:
        print("No iCloud credentials in config.json")
        return

    print(f"\nEmail Monitor — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Connecting to {IMAP_HOST}...")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(email_addr, password)
        print("✅ Connected")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    results = {
        "generated_at": datetime.datetime.now().isoformat(),
        "account": email_addr,
        "unread_count": 0,
        "emails": [],
        "folders_checked": [],
    }

    try:
        mail.select("INBOX")
        results["folders_checked"].append("INBOX")

        # Search for unseen emails
        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            print("Could not search inbox")
            return

        email_ids = data[0].split() if data[0] else []
        results["unread_count"] = len(email_ids)
        print(f"Found {len(email_ids)} unread emails")

        # Fetch most recent MAX_EMAILS
        recent_ids = email_ids[-MAX_EMAILS:]
        print(f"Fetching {len(recent_ids)} of {len(email_ids)} emails...")

        for eid in reversed(recent_ids):  # newest first
            try:
                # BODY.PEEK[] avoids marking emails as read; iCloud sends unsolicited
                # FLAGS responses mixed into msg_data, so search all items for the tuple.
                status, msg_data = mail.fetch(eid, "(BODY.PEEK[])")
                if status != "OK" or not msg_data:
                    print(f"  FETCH failed for {eid}: status={status}")
                    continue

                raw = next((item[1] for item in msg_data if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], bytes)), None)
                if raw is None:
                    print(f"  FETCH no body found for {eid}: {msg_data!r}")
                    continue

                msg = email.message_from_bytes(raw)
            except Exception as fetch_err:
                print(f"  Skipping message {eid}: {type(fetch_err).__name__}: {fetch_err}")
                continue

            subject = decode_str(msg.get("Subject", "(no subject)"))
            sender  = decode_str(msg.get("From", ""))
            date    = decode_str(msg.get("Date", ""))
            body    = get_body(msg).strip()

            results["emails"].append({
                "id": eid.decode() if isinstance(eid, bytes) else str(eid),
                "subject": subject,
                "from": sender,
                "date": date,
                "preview": body[:300] if body else "",
            })

    except Exception as e:
        print(f"Error reading emails: {e}")
    finally:
        mail.logout()

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Digest saved — {results['unread_count']} unread, {len(results['emails'])} fetched")
    print(f"   Output: {OUTPUT_FILE}")
    return results


if __name__ == "__main__":
    run()
