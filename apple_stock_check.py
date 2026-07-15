#!/usr/bin/env python3
"""
Apple Stock Alert Script — outputs JSON to stdout when items are in stock.
OpenClaw wrapper handles Discord delivery via message tool.

Alert logic:
- First time seen in stock  → alert immediately
- Still in stock after 7 days → re-alert (stock reminder)
- Back in stock after being OOS → re-alert
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

STATE_PATH = Path("/data/skills/apple_stock_state.json") if Path("/data/skills").exists() else Path("/docker/openclaw-3scs/data/skills/apple_stock_state.json")

# Re-alert after this many seconds if item is still in stock
REENABLE_AFTER_SECS = 7 * 24 * 3600  # 7 days

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="ignore"), resp.geturl()
    except Exception as e:
        print(f"[fetch] error: {e}", file=sys.stderr)
        return "", ""

def load_state():
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except:
        return {}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def check_mac_mini_refurb():
    """Check Apple refurb page for M4/M4 Pro Mac mini with 24GB+"""
    html, final_url = fetch("https://www.apple.com/shop/refurbished/mac/mac-mini")
    if not html or "mac-mini" not in final_url:
        return []

    hits = []
    seen = set()
    pattern = re.compile(
        r"(Refurbished[^<]{0,300}Mac mini[^<]{0,300}M4[^<]{0,600}?)"
        r"[\s\S]{0,4000}?\$\s*([0-9][0-9,]{2,4})\.\d{2}",
        re.IGNORECASE,
    )

    for m in pattern.finditer(html):
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
        price_str = m.group(2).replace(",", "")
        key = f"macmini|{title}|{price_str}"

        if key in seen:
            continue
        seen.add(key)

        if not re.search(r"\bM4\b", title, re.IGNORECASE):
            continue

        mem_match = re.search(r"(\d+)GB", title, re.IGNORECASE)
        if not mem_match or int(mem_match.group(1)) < 24:
            continue

        hits.append({
            "title": title[:160],
            "price": f"${price_str}",
            "url": "https://www.apple.com/shop/refurbished/mac/mac-mini",
            "key": key,
            "emoji": "🟢"
        })

    return hits


def check_aqara_lock():
    """Check Apple Store product page for Aqara Smart Lock U400 stock"""
    url = "https://www.apple.com/shop/product/hs3z2zm/a/aqara-smart-lock-u400-deluxe-kit-shadow-black"
    html, _ = fetch(url)
    if not html:
        return []

    # "Sold Out" button = out of stock.
    # Do NOT match generic "unavailable" text (Apple uses it for store-pickup messages).
    sold_out_button = bool(re.search(r'<button[^>]*>\s*Sold Out', html, re.IGNORECASE))
    if sold_out_button:
        return []

    # "Add to Bag" button present = in stock.
    in_stock = bool(re.search(r'add.?to.?bag', html, re.IGNORECASE))
    if not in_stock:
        return []

    # Extract price
    price_match = re.search(r"\$\s*([0-9][0-9,]{2,4}\.\d{2})", html)
    price = f"${price_match.group(1)}" if price_match else "See link"

    return [{
        "title": "Aqara Smart Lock U400 Deluxe Kit - Shadow Black",
        "price": price,
        "url": url,
        "key": "aqara|u400|shadow-black",
        "emoji": "🔒"
    }]


def main():
    all_hits = []
    all_hits.extend(check_mac_mini_refurb())
    all_hits.extend(check_aqara_lock())

    previous = load_state()
    current_keys = {h["key"]: h for h in all_hits}
    now = time.time()

    alerts = []
    for key, hit in current_keys.items():
        prev = previous.get(key)
        if prev is None:
            # First time ever seeing this item → alert
            alerts.append(hit)
        elif prev.get("available", True) is False:
            # Was OOS before → back in stock → re-alert
            alerts.append(hit)
        elif prev.get("last_alert_at", 0) + REENABLE_AFTER_SECS <= now:
            # Has been in stock for > 7 days without re-alert → re-alert
            alerts.append(hit)
        # else: still in stock, within 7-day window → skip

    # Build new state
    new_state = {}
    for key, hit in current_keys.items():
        prev = previous.get(key, {})
        new_state[key] = {
            **hit,
            "available": True,
            "last_alert_at": now if key in [a["key"] for a in alerts] else prev.get("last_alert_at", 0),
        }

    # Carry forward items that are no longer in stock (mark unavailable)
    for key in previous:
        if key not in new_state:
            # Item is OOS now — keep in state briefly to detect "back in stock"
            # Mark as unavailable so next time it comes in stock we re-alert
            new_state[key] = {**previous[key], "available": False}

    save_state(new_state)

    if alerts:
        print("STOCK_ALERT:")
        print(json.dumps(alerts, indent=2))


if __name__ == "__main__":
    main()
