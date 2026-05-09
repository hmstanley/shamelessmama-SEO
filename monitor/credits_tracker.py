"""
Claude API Credits Tracker for Shameless Mama SEO
Tracks token usage from each API call and estimates remaining balance.

The Anthropic API doesn't expose a balance endpoint, but every response
includes input_tokens and output_tokens — we accumulate those locally.

Usage:
    from credits_tracker import track_usage, get_status, print_status

    # After a successful Claude API call:
    track_usage("content_brief.py", "claude-opus-4-5", input_tokens=800, output_tokens=1200)

    # At end of a daily run:
    print_status()
"""

import json
import os
import datetime

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR = os.path.join(REPO_ROOT, "dashboard", "data")
CREDITS_FILE = os.path.join(DATA_DIR, "credits.json")

# ── Pricing table (USD per million tokens) ──────────────────────────────────
# Source: console.anthropic.com/settings/billing — update if pricing changes
PRICING = {
    "claude-opus-4-6":            {"input": 15.00, "output": 75.00},
    "claude-opus-4-5":            {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6":          {"input":  3.00, "output": 15.00},
    "claude-sonnet-3-7":          {"input":  3.00, "output": 15.00},
    "claude-sonnet-3-5":          {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5-20251001":  {"input":  0.80, "output":  4.00},
    "claude-haiku-3-5":           {"input":  0.80, "output":  4.00},
    "_default":                   {"input":  3.00, "output": 15.00},
}

# ── Defaults (edit these to match your Anthropic billing settings) ───────────
DEFAULT_STATE = {
    "starting_balance": 50.00,      # your Anthropic credit balance after auto-renew
    "auto_renew_amount": 50.00,     # what auto-renew tops you back up to
    "warn_below": 5.00,             # warn when estimated remaining drops below this
    "period_start": None,           # ISO date string — set on first use
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_cost_usd": 0.0,
    "last_auto_renew": None,        # ISO date of last time you manually reset (after auto-renew)
    "usage_log": [],                # list of individual call records
}


def _load():
    if os.path.exists(CREDITS_FILE):
        with open(CREDITS_FILE) as f:
            return json.load(f)
    state = dict(DEFAULT_STATE)
    state["period_start"] = datetime.date.today().isoformat()
    return state


def _save(state):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CREDITS_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _cost_for(model, input_tokens, output_tokens):
    pricing = PRICING.get(model, PRICING["_default"])
    return (input_tokens / 1_000_000 * pricing["input"]) + \
           (output_tokens / 1_000_000 * pricing["output"])


def track_usage(script_name, model, input_tokens, output_tokens):
    """
    Record one Claude API call. Call this immediately after a successful response.

    Args:
        script_name: e.g. "content_brief.py"
        model:       e.g. "claude-opus-4-5"
        input_tokens:  from response["usage"]["input_tokens"]
        output_tokens: from response["usage"]["output_tokens"]

    Returns:
        dict with keys: cost, total_cost_usd, estimated_remaining, low_balance (bool)
    """
    state = _load()
    cost = _cost_for(model, input_tokens, output_tokens)

    state["total_input_tokens"] += input_tokens
    state["total_output_tokens"] += output_tokens
    state["total_cost_usd"] = round(state["total_cost_usd"] + cost, 6)

    # Keep the log trimmed to the last 500 entries to avoid bloat
    state["usage_log"].append({
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "script": script_name,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    })
    if len(state["usage_log"]) > 500:
        state["usage_log"] = state["usage_log"][-500:]

    _save(state)

    estimated_remaining = round(state["starting_balance"] - state["total_cost_usd"], 4)
    return {
        "cost": round(cost, 6),
        "total_cost_usd": state["total_cost_usd"],
        "estimated_remaining": estimated_remaining,
        "low_balance": estimated_remaining < state["warn_below"],
    }


def reset_period(new_balance=None):
    """
    Call this after an auto-renew fires (or when you add credits manually).
    Resets the running totals so the tracker starts fresh against the new balance.

    Args:
        new_balance: new starting balance in USD (defaults to auto_renew_amount)
    """
    state = _load()
    if new_balance is not None:
        state["starting_balance"] = new_balance
    else:
        state["starting_balance"] = state["auto_renew_amount"]
    state["total_input_tokens"] = 0
    state["total_output_tokens"] = 0
    state["total_cost_usd"] = 0.0
    state["period_start"] = datetime.date.today().isoformat()
    state["last_auto_renew"] = datetime.date.today().isoformat()
    state["usage_log"] = []
    _save(state)
    print(f"Credits tracker reset — new balance: ${state['starting_balance']:.2f}")


def get_status():
    """Return a dict summarising the current credit status."""
    state = _load()
    spent = state["total_cost_usd"]
    remaining = round(state["starting_balance"] - spent, 4)
    warn = state.get("warn_below", 5.00)
    renew_amount = state.get("auto_renew_amount", 50.00)
    pct_used = round(spent / state["starting_balance"] * 100, 1) if state["starting_balance"] else 0

    return {
        "starting_balance": state["starting_balance"],
        "total_spent": round(spent, 4),
        "estimated_remaining": remaining,
        "auto_renew_amount": renew_amount,
        "warn_below": warn,
        "period_start": state.get("period_start"),
        "last_auto_renew": state.get("last_auto_renew"),
        "total_input_tokens": state["total_input_tokens"],
        "total_output_tokens": state["total_output_tokens"],
        "pct_used": pct_used,
        "low_balance": remaining < warn,
        "call_count": len(state.get("usage_log", [])),
    }


def print_status():
    """Print a human-readable credit status block to stdout."""
    s = get_status()
    bar_filled = int(s["pct_used"] / 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)

    print("\n" + "=" * 50)
    print("  Claude API Credit Status")
    print("=" * 50)
    print(f"  Balance:    ${s['starting_balance']:.2f}  (since {s['period_start'] or 'unknown'})")
    print(f"  Spent:      ${s['total_spent']:.4f}  ({s['pct_used']}%)  [{bar}]")
    print(f"  Remaining:  ${s['estimated_remaining']:.4f}")
    print(f"  API calls:  {s['call_count']}  ({s['total_input_tokens']:,} in / {s['total_output_tokens']:,} out tokens)")
    print(f"  Auto-renew: ${s['auto_renew_amount']:.2f} when balance hits $0")

    if s["low_balance"]:
        print()
        print(f"  ⚠️  LOW BALANCE — ${s['estimated_remaining']:.2f} remaining")
        print(f"  Auto-renew will fire soon (adds ${s['auto_renew_amount']:.2f}).")
        print(f"  Run `python monitor/credits_tracker.py reset` after it fires.")

    print("=" * 50)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        amount = float(sys.argv[2]) if len(sys.argv) > 2 else None
        reset_period(amount)
    else:
        print_status()
