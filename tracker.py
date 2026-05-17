#!/usr/bin/env python3
"""
Spending Tracker Core — data operations, budget checks, queries.
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

TRACKER_DIR = Path(os.path.expanduser("~/.hermes/spending_tracker"))
CONFIG_PATH = TRACKER_DIR / "config.json"
DATA_PATH = TRACKER_DIR / "data.json"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_data() -> dict:
    if DATA_PATH.exists():
        with open(DATA_PATH) as f:
            return json.load(f)
    return {"entries": []}


def save_data(data: dict):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_entry(amount: float, category: str, note: str = "", payment_method: str = "",
              is_credit_card: bool = False) -> dict:
    """Add a spending entry. Returns the entry and any alerts triggered."""
    config = load_config()
    data = load_data()

    entry = {
        "id": len(data["entries"]) + 1,
        "amount": amount,
        "category": category,
        "note": note,
        "payment_method": payment_method,
        "is_credit_card": is_credit_card,
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "week": get_current_week_id(),
    }
    data["entries"].append(entry)
    save_data(data)

    alerts = check_budget_alerts(config, data)
    return {"entry": entry, "alerts": alerts}


def get_current_week_id() -> str:
    """Return ISO week identifier like '2026-W20'."""
    now = datetime.now()
    return now.strftime("%G-W%V")


def get_week_start() -> datetime:
    """Get start of current week (Monday)."""
    today = datetime.now().date()
    return today - timedelta(days=today.weekday())


def get_week_end() -> datetime:
    """Get end of current week (Sunday)."""
    return get_week_start() + timedelta(days=6)


def get_entries_in_week(week_id: str = None, is_credit_card: bool = None) -> list:
    """Get all entries for a given week. Defaults to current week."""
    if week_id is None:
        week_id = get_current_week_id()
    data = load_data()
    entries = [e for e in data["entries"] if e.get("week") == week_id]
    if is_credit_card is not None:
        entries = [e for e in entries if e.get("is_credit_card") == is_credit_card]
    return entries


def get_all_entries(is_credit_card: bool = None) -> list:
    data = load_data()
    entries = data["entries"]
    if is_credit_card is not None:
        entries = [e for e in entries if e.get("is_credit_card") == is_credit_card]
    return entries


def get_category_total(category: str, week_id: str = None, is_credit_card: bool = None) -> float:
    """Get total spending for a category in a given week."""
    entries = get_entries_in_week(week_id, is_credit_card=is_credit_card)
    return sum(e["amount"] for e in entries if e["category"] == category)


def get_weekly_total(week_id: str = None, is_credit_card: bool = None) -> float:
    """Get total spending for a given week."""
    entries = get_entries_in_week(week_id, is_credit_card=is_credit_card)
    return sum(e["amount"] for e in entries)


def check_budget_alerts(config: dict = None, data: dict = None) -> list:
    """Check all budget limits and return triggered alerts."""
    if config is None:
        config = load_config()
    if data is None:
        data = load_data()

    alerts = []
    week_id = get_current_week_id()
    weekly_budget = config["weekly_budget"]
    warning_pct = config["alert_thresholds"]["warning"]
    critical_pct = config["alert_thresholds"]["critical"]

    # Regular spending (non-credit-card)
    regular_entries = get_entries_in_week(week_id, is_credit_card=False)
    regular_total = sum(e["amount"] for e in regular_entries)

    # Overall weekly
    if weekly_budget:
        if regular_total >= weekly_budget * critical_pct:
            alerts.append({
                "type": "critical",
                "scope": "overall",
                "message": f"🚨 CRITICAL: You've hit {regular_total:.0f}/{weekly_budget} (100%+) of your weekly budget!",
                "spent": regular_total,
                "limit": weekly_budget,
                "pct": round(regular_total / weekly_budget * 100)
            })
        elif regular_total >= weekly_budget * warning_pct:
            alerts.append({
                "type": "warning",
                "scope": "overall",
                "message": f"⚠️ Heads up: ₹{regular_total:.0f}/{weekly_budget} spent this week ({round(regular_total/weekly_budget*100)}%). Slow down!",
                "spent": regular_total,
                "limit": weekly_budget,
                "pct": round(regular_total / weekly_budget * 100)
            })

    # Per-category
    for cat_name, cat_config in config["categories"].items():
        cat_limit = cat_config.get("weekly_limit")
        if cat_limit is None:
            continue
        cat_total = sum(e["amount"] for e in regular_entries if e["category"] == cat_name)
        if cat_total >= cat_limit * critical_pct:
            alerts.append({
                "type": "critical",
                "scope": cat_name,
                "message": f"🚨 {cat_name.replace('_', ' ').title()}: ₹{cat_total:.0f}/{cat_limit} limit reached!",
                "spent": cat_total,
                "limit": cat_limit,
                "pct": round(cat_total / cat_limit * 100)
            })
        elif cat_total >= cat_limit * warning_pct:
            alerts.append({
                "type": "warning",
                "scope": cat_name,
                "message": f"⚠️ {cat_name.replace('_', ' ').title()}: ₹{cat_total:.0f}/{cat_limit} ({round(cat_total/cat_limit*100)}%)",
                "spent": cat_total,
                "limit": cat_limit,
                "pct": round(cat_total / cat_limit * 100)
            })

    # Credit card
    cc_entries = get_entries_in_week(week_id, is_credit_card=True)
    cc_total = sum(e["amount"] for e in cc_entries)
    if cc_total > 0:
        # No limit on credit card, just track
        pass

    return alerts


def get_summary(week_id: str = None) -> str:
    """Generate a human-readable spending summary."""
    if week_id is None:
        week_id = get_current_week_id()
    config = load_config()

    regular_total = get_weekly_total(week_id, is_credit_card=False)
    cc_total = get_weekly_total(week_id, is_credit_card=True)
    weekly_budget = config["weekly_budget"]

    lines = []
    week_start = get_week_start().strftime("%b %d")
    week_end = get_week_end().strftime("%b %d")

    # Overall
    remaining = weekly_budget - regular_total
    pct = round(regular_total / weekly_budget * 100) if weekly_budget else 0
    status_emoji = "🟢" if pct < 50 else "🟡" if pct < 80 else "🔴"

    lines.append(f"📊 **Spending Summary** — {week_start} → {week_end}")
    lines.append(f"")
    lines.append(f"{status_emoji} **Total:** ₹{regular_total:.0f} / ₹{weekly_budget} ({pct}%)")
    lines.append(f"   Remaining: ₹{remaining:.0f}")
    lines.append(f"")

    # Category breakdown
    lines.append(f"📂 **By Category:**")
    for cat_name, cat_config in config["categories"].items():
        cat_total = get_category_total(cat_name, week_id, is_credit_card=False)
        cat_limit = cat_config.get("weekly_limit")
        bar = _progress_bar(cat_total, cat_limit or weekly_budget, 12)
        limit_str = f"/ ₹{cat_limit:.0f}" if cat_limit else ""
        label = cat_name.replace("_", " ").title()
        lines.append(f"   {bar} {label}: ₹{cat_total:.0f}{limit_str}")

    # Credit card
    if cc_total > 0:
        lines.append(f"")
        lines.append(f"💳 **Credit Card:** ₹{cc_total:.0f} (separate)")

    # Recent entries
    entries = get_all_entries(is_credit_card=False)
    recent = entries[-5:]
    if recent:
        lines.append(f"")
        lines.append(f"🕐 **Recent:**")
        for e in reversed(recent):
            note_suffix = f" — {e['note']}" if e.get("note") else ""
            pm_suffix = f" via {e['payment_method']}" if e.get("payment_method") else ""
            cat_label = e['category'].replace('_', ' ').title()
            lines.append(f"   • ₹{e['amount']:.0f} {cat_label}{pm_suffix}{note_suffix}")

    # Credit card recent
    cc_recent = [e for e in entries if e.get("is_credit_card")][-3:]
    if cc_recent:
        lines.append(f"")
        lines.append(f"💳 **Recent Credit Card:**")
        for e in reversed(cc_recent):
            note_suffix = f" — {e['note']}" if e.get("note") else ""
            cc_label = e['category'].replace('_', ' ').title()
            lines.append(f"   • ₹{e['amount']:.0f} {cc_label}{note_suffix}")

    return "\n".join(lines)


def _progress_bar(current: float, limit: float, width: int = 10) -> str:
    """Draw a mini progress bar."""
    if limit == 0:
        return "█" * width
    filled = min(int(current / limit * width), width)
    bar = "▓" * filled + "░" * (width - filled)
    return bar


def get_dashboard_data() -> dict:
    """Return all data needed for the web dashboard."""
    config = load_config()
    data = load_data()
    entries = data["entries"]

    # Current week breakdown
    week_id = get_current_week_id()
    weekly_regular = get_entries_in_week(week_id, is_credit_card=False)
    weekly_cc = get_entries_in_week(week_id, is_credit_card=True)

    # Category totals for current week
    categories = []
    for cat_name in config["categories"]:
        total = sum(e["amount"] for e in weekly_regular if e["category"] == cat_name)
        categories.append({
            "name": cat_name.replace("_", " ").title(),
            "total": total,
            "limit": config["categories"][cat_name].get("weekly_limit"),
        })

    # Weekly history (last 8 weeks)
    weekly_history = []
    for i in range(7, -1, -1):
        d = datetime.now().date() - timedelta(weeks=i)
        wk = d.strftime("%G-W%V")
        wk_label = f"Week {int(d.strftime('%V'))}"
        reg = sum(e["amount"] for e in entries if e.get("week") == wk and not e.get("is_credit_card"))
        cc = sum(e["amount"] for e in entries if e.get("week") == wk and e.get("is_credit_card"))
        weekly_history.append({
            "week": wk_label,
            "regular": reg,
            "credit_card": cc,
            "limit": config["weekly_budget"],
        })

    # Daily spending (last 14 days)
    daily_spending = []
    for i in range(13, -1, -1):
        date = (datetime.now().date() - timedelta(days=i)).isoformat()
        reg = sum(e["amount"] for e in entries if e.get("date") == date and not e.get("is_credit_card"))
        cc = sum(e["amount"] for e in entries if e.get("date") == date and e.get("is_credit_card"))
        daily_spending.append({"date": date, "regular": reg, "credit_card": cc})

    # Payment method breakdown
    payment_methods = {}
    for e in entries:
        pm = e.get("payment_method", "unknown")
        if pm:
            payment_methods[pm] = payment_methods.get(pm, 0) + e["amount"]

    return {
        "week_id": week_id,
        "week_start": get_week_start().isoformat(),
        "week_end": get_week_end().isoformat(),
        "weekly_budget": config["weekly_budget"],
        "weekly_regular_total": sum(e["amount"] for e in weekly_regular),
        "weekly_cc_total": sum(e["amount"] for e in weekly_cc),
        "total_entries": len(entries),
        "categories": categories,
        "weekly_history": weekly_history,
        "daily_spending": daily_spending,
        "payment_methods": payment_methods,
        "entries": sorted(entries, key=lambda e: e["timestamp"], reverse=True),
    }


if __name__ == "__main__":
    # Quick test
    print(get_summary())
