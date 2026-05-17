#!/usr/bin/env python3
"""
Spending Parser — converts natural language messages into structured spending entries.
Handles formats like:
  - "Spent ₹200 on food via UPI — lunch"
  - "₹200 food UPI — lunch"
  - "200 rs on food via credit card for dinner"
  - "spent 200 on Uber via credit card"
"""
import re
import json
from pathlib import Path
from typing import Optional

TRACKER_DIR = Path(__file__).parent
CONFIG_PATH = TRACKER_DIR / "config.json"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def parse_spending(message: str) -> Optional[dict]:
    """
    Parse a spending message. Returns None if it doesn't look like a spending entry.
    Returns dict with: amount, category, payment_method, note, is_credit_card
    """
    msg = message.strip()

    # Try to extract amount first (supports ₹, Rs, rs, INR, plain number)
    amount = None
    amount_match = re.search(
        r'(?:₹|Rs\.?\s*|INR\s*)?(\d+(?:[,.]?\d{1,2})?)\s*(?:rs|rupees?)?',
        msg, re.IGNORECASE
    )
    if amount_match:
        amount_str = amount_match.group(1).replace(",", "")
        try:
            amount = float(amount_str)
        except ValueError:
            pass

    if amount is None:
        # Try simpler: just find a number
        num_match = re.search(r'\b(\d+)\b', msg)
        if num_match:
            try:
                amount = float(num_match.group(1))
            except ValueError:
                pass

    if amount is None or amount <= 0:
        return None

    # Detect credit card payment
    is_credit_card = bool(re.search(
        r'(credit\s*card|creditcard|cc\b)',
        msg, re.IGNORECASE
    ))

    # Detect payment method
    payment_methods = [
        ("upi", ["upi", "gpay", "google pay", "phonepe", "paytm"]),
        ("credit_card", ["credit card", "creditcard", "cc"]),
        ("debit_card", ["debit card", "debitcard"]),
        ("cash", ["cash", "hard cash"]),
        ("netbanking", ["netbanking", "net banking", "bank transfer", "imps", "neft", "rtgs"]),
    ]
    payment_method = ""
    for method, keywords in payment_methods:
        for kw in keywords:
            if re.search(rf'\b{re.escape(kw)}\b', msg, re.IGNORECASE):
                payment_method = method
                break
        if payment_method:
            break

    if not payment_method:
        # Try to find "via X" or "by X" pattern
        via_match = re.search(r'(?:via|by|using)\s+(\w+(?:\s+\w+)?)', msg, re.IGNORECASE)
        if via_match:
            payment_method = via_match.group(1).strip().lower()

    # Detect category
    config = load_config()
    category = None
    msg_lower = msg.lower()

    # Score each category by keyword matches
    scores = {}
    for cat_name, cat_config in config["categories"].items():
        score = 0
        for kw in cat_config.get("keywords", []):
            if kw.lower() in msg_lower:
                # Full word match scores higher
                if re.search(rf'\b{re.escape(kw.lower())}\b', msg_lower):
                    score += 3
                else:
                    score += 1
        scores[cat_name] = score

    # Pick highest scoring category
    if scores:
        max_score = max(scores.values())
        if max_score > 0:
            category = max(scores, key=scores.get)

    if category is None:
        category = "miscellaneous"

    # Extract note (anything after — or - or : or for, but not payment info)
    note = ""
    note_patterns = [
        r'—\s*(.+)$',       # em dash
        r'--\s*(.+)$',      # double dash
        r'-\s*([^-].+)$',   # single dash (not followed by another dash)
        r':\s*(.+)$',       # colon
        r'\bfor\s+(.+)$',   # "for X"
    ]
    for pattern in note_patterns:
        note_match = re.search(pattern, msg, re.IGNORECASE)
        if note_match:
            raw_note = note_match.group(1).strip()
            # Remove payment info from note
            raw_note = re.sub(r'via\s+\S+', '', raw_note, flags=re.IGNORECASE).strip()
            raw_note = re.sub(r'by\s+\S+', '', raw_note, flags=re.IGNORECASE).strip()
            if raw_note:
                note = raw_note
            break

    # If message is just "spent X on Y" where Y isn't a category, use as note
    if not note:
        on_match = re.search(r'\bon\s+([a-zA-Z].+?)(?:\s+(?:via|by|using|with)\s+|$)', msg, re.IGNORECASE)
        if on_match:
            potential_note = on_match.group(1).strip()
            # Check if it's a known category keyword
            is_cat = False
            for cat_config in config["categories"].values():
                for kw in cat_config.get("keywords", []):
                    if kw.lower() == potential_note.lower():
                        is_cat = True
                        break
                if is_cat:
                    break
            if not is_cat:
                note = potential_note

    # If credit card, note can include what was bought
    if is_credit_card and not note:
        # Try to extract what was purchased
        what_match = re.search(r'(?:for|on)\s+([a-zA-Z].+?)(?:\s+(?:via|by|using|with|rs\.?|₹)\s+|$)', msg, re.IGNORECASE)
        if what_match:
            note = what_match.group(1).strip().rstrip(".").rstrip()

    return {
        "amount": amount,
        "category": category,
        "payment_method": payment_method,
        "note": note,
        "is_credit_card": is_credit_card,
    }


def is_spending_message(message: str) -> bool:
    """Quick check if a message looks like a spending entry."""
    result = parse_spending(message)
    return result is not None


if __name__ == "__main__":
    # Quick test
    tests = [
        "Spent ₹200 on food via UPI — lunch",
        "₹500 food UPI — Zomato order",
        "200 rs on transport via cash",
        "spent 1500 on shopping via credit card — new shoes",
        "Uber ride ₹350 by UPI",
        "paid 1200 for electricity bill via netbanking",
        "500 on Netflix via credit card",
        "just a random message",
        "movie tickets 600 via UPI",
        "spent 300 on lunch at the cafe by cash",
    ]
    for t in tests:
        result = parse_spending(t)
        if result:
            print(f"✓ {t}")
            print(f"  → {result}")
        else:
            print(f"✗ {t} — not a spending message")
