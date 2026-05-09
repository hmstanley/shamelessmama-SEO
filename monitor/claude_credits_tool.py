"""
title: Claude API Credits
author: HomeAI
description: Reports Claude API credit balance and usage. Use when asked about API credits, spending, remaining balance, or auto-renew status.
version: 1.0.0
"""

import json
import os
from pydantic import BaseModel


CREDITS_FILE = "/Users/Will.Coleman/shamelessmama-SEO/dashboard/data/credits.json"


class Tools:
    def __init__(self):
        pass

    def check_claude_credits(self) -> str:
        """
        Check the current Claude API credit balance and usage for this billing period.
        Use this when the user asks about API credits, credit balance, token usage,
        how much has been spent, whether auto-renew is close, or anything about
        Claude API costs.

        :return: Formatted credit status report
        """
        if not os.path.exists(CREDITS_FILE):
            return (
                "No credit data on file yet. Credits are tracked automatically each time "
                "the Mac runs content_brief.py and makes a Claude API call. "
                "Run the daily SEO scripts to populate this data."
            )

        try:
            with open(CREDITS_FILE) as f:
                raw = json.load(f)
        except Exception as e:
            return f"Could not read credits file: {e}"

        spent      = raw.get("total_cost_usd", 0.0)
        starting   = raw.get("starting_balance", 50.0)
        remaining  = round(starting - spent, 4)
        warn_below = raw.get("warn_below", 5.0)
        auto_renew = raw.get("auto_renew_amount", 50.0)
        period_start = raw.get("period_start", "unknown")
        call_count = len(raw.get("usage_log", []))
        pct_used   = round(spent / starting * 100, 1) if starting else 0
        in_tok     = raw.get("total_input_tokens", 0)
        out_tok    = raw.get("total_output_tokens", 0)
        low        = remaining < warn_below

        bar_filled = min(10, int(pct_used / 10))
        bar    = "█" * bar_filled + "░" * (10 - bar_filled)
        status = "⚠️ LOW — auto-renew will fire soon" if low else "✅ OK"

        lines = [
            "## 💳 Claude API Credit Status",
            "",
            "| | |",
            "|---|---|",
            f"| Period start | {period_start} |",
            f"| Starting balance | ${starting:.2f} |",
            f"| Spent this period | ${spent:.4f} ({pct_used}%)  `{bar}` |",
            f"| **Estimated remaining** | **${remaining:.4f}** |",
            f"| Auto-renew amount | ${auto_renew:.2f} |",
            f"| Status | {status} |",
            f"| API calls logged | {call_count} |",
            f"| Tokens used | {in_tok:,} in / {out_tok:,} out |",
        ]

        if low:
            lines += [
                "",
                f"> ⚠️ **Balance is below ${warn_below:.2f}.** "
                f"Auto-renew will add ${auto_renew:.2f} back to your account soon. "
                f"After it fires, reset the tracker on the Mac: "
                f"`python3 monitor/credits_tracker.py reset`",
            ]

        return "\n".join(lines)
