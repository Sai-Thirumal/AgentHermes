#!/usr/bin/env python3
"""
Spending Tracker CLI — dispatches commands and parses spending messages.
Usage:
  python3 cli.py add "Spent ₹200 on food via UPI — lunch"
  python3 cli.py summary
  python3 cli.py summary --week 2026-W20
  python3 cli.py alerts
  python3 cli.py parse "₹200 food"       (just parse, no save)
  python3 cli.py dashboard-data           (JSON for dashboard)
"""
import json
import sys
import os
from pathlib import Path

TRACKER_DIR = Path(os.path.expanduser("~/.hermes/spending_tracker"))
sys.path.insert(0, str(TRACKER_DIR))

from tracker import add_entry, get_summary, check_budget_alerts, get_dashboard_data
from parser import parse_spending


def cmd_add(message: str):
    """Parse and add a spending entry."""
    parsed = parse_spending(message)
    if parsed is None:
        print(json.dumps({
            "success": False,
            "error": "Could not parse spending from message.",
            "message": message
        }))
        return

    result = add_entry(
        amount=parsed["amount"],
        category=parsed["category"],
        note=parsed["note"],
        payment_method=parsed["payment_method"],
        is_credit_card=parsed["is_credit_card"],
    )

    entry = result["entry"]
    alerts = result["alerts"]

    # Format response
    cat_display = entry["category"].replace("_", " ").title()
    pm_str = f" via {entry['payment_method']}" if entry["payment_method"] else ""
    note_str = f" — {entry['note']}" if entry["note"] else ""
    cc_tag = " 💳" if entry["is_credit_card"] else ""

    response = f"✅ Logged: ₹{entry['amount']:.0f} {cat_display}{pm_str}{note_str}{cc_tag}"

    if alerts:
        response += "\n\n" + "\n".join(a["message"] for a in alerts)

    print(json.dumps({
        "success": True,
        "response": response,
        "entry": entry,
        "alerts": alerts,
    }))


def cmd_summary(week_id: str = None):
    """Get spending summary."""
    summary = get_summary(week_id)
    print(json.dumps({
        "success": True,
        "summary": summary,
    }))


def cmd_alerts():
    """Check all budget alerts."""
    alerts = check_budget_alerts()
    if alerts:
        print(json.dumps({
            "success": True,
            "alerts": alerts,
            "messages": [a["message"] for a in alerts],
        }))
    else:
        print(json.dumps({
            "success": True,
            "alerts": [],
            "messages": [],
            "response": "✅ All budgets on track!",
        }))


def cmd_parse(message: str):
    """Parse a message without saving."""
    parsed = parse_spending(message)
    print(json.dumps({
        "success": parsed is not None,
        "parsed": parsed,
    }))


def cmd_dashboard():
    """Output dashboard data as JSON."""
    data = get_dashboard_data()
    print(json.dumps(data, ensure_ascii=False))


def cmd_weekly_summary():
    """Generate and print the weekly summary (for cron jobs)."""
    summary = get_summary()
    alerts = check_budget_alerts()

    output = summary
    if alerts:
        output += "\n\n⚠️ **Active Alerts:**\n"
        output += "\n".join(f"• {a['message']}" for a in alerts)

    print(output)


def main():
    if len(sys.argv) < 2:
        print("Usage: cli.py <command> [args]")
        print("Commands: add, summary, alerts, parse, dashboard-data, weekly-summary")
        sys.exit(1)

    command = sys.argv[1]
    args = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    if command == "add":
        cmd_add(args)
    elif command == "summary":
        week = None
        for i, arg in enumerate(sys.argv[2:]):
            if arg == "--week" and i + 1 < len(sys.argv[2:]):
                week = sys.argv[i + 3]  # +3 because sys.argv[2:]
                break
        cmd_summary(week)
    elif command == "alerts":
        cmd_alerts()
    elif command == "parse":
        cmd_parse(args)
    elif command == "dashboard-data":
        cmd_dashboard()
    elif command == "weekly-summary":
        cmd_weekly_summary()
    else:
        print(json.dumps({"success": False, "error": f"Unknown command: {command}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
