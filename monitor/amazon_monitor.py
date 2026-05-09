"""
Amazon Orders Monitor
Uses browser-exported cookies + Playwright (headless Chromium) to fetch
order history after JavaScript renders the page.
Writes dashboard/data/amazon_orders.json.

Run: /Users/Will.Coleman/.local/bin/python3.12 monitor/amazon_monitor.py
Re-export cookies from amazon.com/gp/css/order-history using Cookie-Editor when they expire.
"""

import json
import os
import re
import datetime
from playwright.sync_api import sync_playwright

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(SCRIPT_DIR, "..")
DATA_DIR = os.path.join(REPO_ROOT, "dashboard", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "amazon_orders.json")
COOKIES_FILE = os.path.join(REPO_ROOT, ".amazon_cookies.json")

ORDERS_URL = "https://www.amazon.com/gp/css/order-history"


def load_playwright_cookies() -> list:
    """Convert Cookie-Editor JSON format to Playwright cookie format."""
    with open(COOKIES_FILE) as f:
        raw = json.load(f)
    cookies = []
    for c in raw:
        cookie = {
            "name": c["name"],
            "value": c.get("value", ""),
            "domain": c.get("domain", ".amazon.com"),
            "path": c.get("path", "/"),
            "secure": c.get("secure", True),
            "httpOnly": c.get("httpOnly", False),
        }
        if c.get("expirationDate"):
            cookie["expires"] = int(c["expirationDate"])
        ss = c.get("sameSite")
        if ss in ("Strict", "Lax", "None"):
            cookie["sameSite"] = ss
        cookies.append(cookie)
    return cookies


def parse_orders_from_page(page) -> list:
    """Extract order data from the rendered page."""
    orders = []

    order_cards = page.query_selector_all(".order-card, .js-order-card")
    for card in order_cards:
        order = {}

        # Order ID — look for XXX-XXXXXXX-XXXXXXX pattern in the card text
        card_text = card.inner_text()
        id_match = re.search(r'\d{3}-\d{7}-\d{7}', card_text)
        if id_match:
            order["order_id"] = id_match.group()

        # Order date — appears on the line after "ORDER PLACED"
        lines = [l.strip() for l in card_text.split("\n") if l.strip()]
        for i, line in enumerate(lines):
            if "ORDER PLACED" in line.upper() and i + 1 < len(lines):
                order["order_date"] = lines[i + 1]
                break
        if "order_date" not in order:
            for sel in [".order-date-invoice-item", "[class*='order-date']", ".a-color-secondary"]:
                el = card.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    if any(m in text for m in ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]):
                        order["order_date"] = text
                        break

        # Total
        price_match = re.search(r'\$[\d,]+\.\d{2}', card_text)
        if price_match:
            order["grand_total"] = price_match.group()

        # Shipment status
        for keyword in ["Delivered", "Arriving", "Shipped", "Preparing", "Cancelled", "Out for delivery", "Coming"]:
            if keyword.lower() in card_text.lower():
                # Find the line containing the keyword
                for line in card_text.split("\n"):
                    if keyword.lower() in line.lower() and len(line.strip()) < 100:
                        order["status"] = line.strip()
                        break
                if "status" in order:
                    break
        if "status" not in order:
            order["status"] = "Unknown"

        # Delivery date if present
        date_match = re.search(r'(?:Arriving|Delivered|Expected)[^\n]*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^\n]*', card_text, re.IGNORECASE)
        if date_match:
            order["delivery_info"] = date_match.group().strip()

        # Items
        items = []
        for item_el in card.query_selector_all(".yohtmlc-product-title a, [class*='item-title'] a, .a-link-normal[href*='/dp/']"):
            title = item_el.inner_text().strip()
            href = item_el.get_attribute("href") or ""
            if title and len(title) > 3:
                link = href if href.startswith("http") else f"https://www.amazon.com{href}"
                items.append({"title": title, "link": link})
        order["items"] = items

        if order.get("order_id"):
            orders.append(order)

    return orders


def run():
    if not os.path.exists(COOKIES_FILE):
        print(f"ERROR: Cookie file not found at {COOKIES_FILE}")
        return False

    with open(COOKIES_FILE) as f:
        raw = json.load(f)
    if not any(c["name"] == "x-main" for c in raw):
        print("ERROR: x-main cookie missing — re-export cookies from amazon.com/gp/css/order-history")
        return False

    print("Launching headless browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        context.add_cookies(load_playwright_cookies())

        page = context.new_page()
        print(f"Fetching {ORDERS_URL}...")
        page.goto(ORDERS_URL, wait_until="load", timeout=45000)
        page.wait_for_timeout(3000)  # let JS finish rendering orders

        if "signin" in page.url or "ap/signin" in page.url:
            print("ERROR: Redirected to login — cookies have expired. Re-export from amazon.com")
            browser.close()
            return False

        print(f"  Page loaded: {page.url}")
        orders = parse_orders_from_page(page)
        print(f"  Parsed {len(orders)} orders")

        if not orders:
            debug_file = os.path.join(REPO_ROOT, ".amazon_debug.html")
            with open(debug_file, "w") as f:
                f.write(page.content())
            print(f"  No orders parsed — saved debug HTML to {debug_file}")

        browser.close()

    in_transit = [o for o in orders if o.get("status", "").lower() not in ("delivered", "unknown", "cancelled", "")]
    recent_delivered = [o for o in orders if "delivered" in o.get("status", "").lower()][:5]

    output = {
        "generated_at": datetime.datetime.now().isoformat(),
        "date": datetime.date.today().isoformat(),
        "total_fetched": len(orders),
        "in_transit": in_transit,
        "recent_delivered": recent_delivered,
        "all_orders": orders,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved to {OUTPUT_FILE}")
    print(f"  In transit: {len(in_transit)}")
    print(f"  Recently delivered: {len(recent_delivered)}")
    return True


if __name__ == "__main__":
    run()
