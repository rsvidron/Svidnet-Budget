"""
Parser for bank account activity CSV export format.

Supports two variants:
  - Spend: Transaction Date, Transaction Description, Amount, Category, Balance
  - Savings: Transaction Date, Transaction Description, Amount, Balance (no Category)
"""
import csv
import re
from typing import List, Dict
from datetime import datetime


def parse_account_activity_csv(file_path: str, default_category: str = None) -> List[Dict]:
    """
    Parse CSV with columns: Transaction Date, Transaction Description, Amount, [Category], Balance.
    If Category column is missing (savings format), use default_category (e.g. "Savings").
    Returns list of transaction dicts with: date, merchant, description, amount, transaction_type, category_name.
    Skips PENDING rows.
    """
    has_category_column = _csv_has_category_column(file_path)
    default_cat = (default_category or "Savings").strip() if default_category else "Savings"

    transactions = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = (row.get("Transaction Date") or row.get("transaction date") or "").strip()
            description = (row.get("Transaction Description") or row.get("transaction description") or "").strip()
            amount_str = (row.get("Amount") or row.get("amount") or "0").strip()
            category_name = (row.get("Category") or row.get("category") or "").strip()
            if not has_category_column:
                category_name = default_cat

            # Skip PENDING rows
            if date_str.upper().startswith("PENDING") or (category_name and category_name.upper() == "PENDING"):
                continue
            if not date_str:
                continue

            # Parse amount: "- $100.89" or "+ $91.06" or "100.89"
            amount_str = amount_str.replace("$", "").replace(",", "").strip()
            sign = 1
            if amount_str.startswith("-"):
                sign = -1
                amount_str = amount_str[1:].strip()
            elif amount_str.startswith("+"):
                amount_str = amount_str[1:].strip()
            try:
                amount = float(amount_str) * sign
            except ValueError:
                continue
            transaction_type = "credit" if amount > 0 else "debit"
            amount_abs = abs(amount)

            # Parse date: 2026-03-06 or similar
            dt = _parse_date(date_str)
            merchant = _extract_merchant(description)

            transactions.append({
                "date": dt,
                "merchant": merchant,
                "description": description,
                "amount": amount_abs,
                "transaction_type": transaction_type,
                "category_name": category_name or None,
            })
    return transactions


def _parse_date(date_str: str) -> datetime:
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return datetime.now()


def _extract_merchant(description: str) -> str:
    if not description:
        return "Unknown"
    description = description.upper().strip()
    patterns = [
        r"^([A-Z0-9\s&.\'-]+?)(?:\s+#\d+|\s+\d{10,})",
        r"^([A-Z0-9\s&.\'-]+?)(?:\s+[A-Z]{2}\s*$)",
        r"^([A-Z0-9\s&.\'-]+)",
    ]
    for pattern in patterns:
        match = re.match(pattern, description)
        if match:
            merchant = match.group(1).strip()
            merchant = re.sub(r"\s{2,}", " ", merchant)
            return merchant[:50] if len(merchant) > 50 else merchant
    return description[:50]


def _csv_has_category_column(file_path: str) -> bool:
    """Return True if the CSV header includes a Category column (spend format)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            first = f.readline()
        lower = first.lower()
        return "category" in lower
    except Exception:
        return False


def is_account_activity_csv(file_path: str) -> bool:
    """
    Return True if the CSV is account-activity format (spend or savings).
    Spend: Transaction Date, Transaction Description, Amount, Category, Balance.
    Savings: Transaction Date, Transaction Description, Amount, Balance (no Category).
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            first = f.readline()
        lower = first.lower()
        has_date = "transaction date" in lower
        has_amount = "amount" in lower
        has_desc = "transaction description" in lower
        return has_date and has_amount and has_desc
    except Exception:
        return False
