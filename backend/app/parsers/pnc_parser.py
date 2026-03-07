import csv
import re
from typing import List, Dict
from datetime import datetime

import PyPDF2
import pdfplumber
from .base_parser import BankStatementParser


def _extract_text_pdfplumber(file_path: str) -> str:
    """Extract text using pdfplumber (often better for bank statements)."""
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


def _extract_text_pypdf2(file_path: str) -> str:
    """Extract text using PyPDF2 as fallback."""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return "\n".join(
            (p.extract_text() or "") for p in reader.pages
        )


class PNCParser(BankStatementParser):
    def parse_csv(self, file_path: str) -> List[Dict]:
        transactions = []

        with open(file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)

            for row in csv_reader:
                date_str = row.get('Date') or row.get('Transaction Date') or row.get('date')
                description = row.get('Description') or row.get('description') or ''
                amount_str = row.get('Amount') or row.get('amount') or '0'

                amount = float(amount_str.replace('$', '').replace(',', '').strip())

                transaction_type = 'credit' if amount > 0 else 'debit'

                merchant = self._extract_merchant(description)

                transaction = {
                    'date': self._parse_date(date_str),
                    'merchant': merchant,
                    'description': description,
                    'amount': abs(amount),
                    'transaction_type': transaction_type,
                }

                transactions.append(self.normalize_transaction(transaction))

        return transactions

    def parse_pdf(self, file_path: str) -> List[Dict]:
        # Try pdfplumber first (better for many bank PDFs), then PyPDF2
        full_text = _extract_text_pdfplumber(file_path)
        if not full_text or not full_text.strip():
            full_text = _extract_text_pypdf2(file_path)
        if not full_text or not full_text.strip():
            return []

        # Normalize: collapse multiple spaces and keep newlines for line-based parsing
        full_text = re.sub(r"[ \t]+", " ", full_text)
        lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

        transactions = []
        seen = set()  # (date_str, desc_snippet, amount) to avoid duplicates

        def add_transaction(date_str: str, description: str, amount: float, transaction_type: str) -> None:
            key = (date_str, description[:40], amount)
            if key in seen:
                return
            seen.add(key)
            merchant = self._extract_merchant(description)
            dt = self._parse_date(date_str)
            transactions.append(
                self.normalize_transaction({
                    "date": dt,
                    "merchant": merchant,
                    "description": description,
                    "amount": abs(amount),
                    "transaction_type": transaction_type,
                })
            )

        # Pattern 1: PNC-style — MM/DD/YYYY  Description  $1,234.56 or (1,234.56)
        for m in re.finditer(
            r"(\d{1,2}/\d{1,2}/\d{4})\s+([^\$\(]+?)\s+\$?([\d,]+\.\d{2})\s*$",
            full_text,
            re.MULTILINE,
        ):
            date_str, desc, amount_str = m.group(1), m.group(2).strip(), m.group(3).replace(",", "")
            add_transaction(date_str, desc, float(amount_str), "debit")

        # Pattern 2: Amount in parentheses = credit (negative amount)
        for m in re.finditer(
            r"(\d{1,2}/\d{1,2}/\d{4})\s+([^\$]+?)\s+\(([\d,]+\.\d{2})\)",
            full_text,
        ):
            date_str, desc, amount_str = m.group(1), m.group(2).strip(), m.group(3).replace(",", "")
            add_transaction(date_str, desc, float(amount_str), "credit")

        # Pattern 3: $ amount at end, optional minus for debit
        for m in re.finditer(
            r"(\d{1,2}/\d{1,2}/\d{4})\s+(.+?)\s+\$?\s*-?([\d,]+\.\d{2})\s*",
            full_text,
        ):
            date_str, desc, amount_str = m.group(1), m.group(2).strip(), m.group(3).replace(",", "")
            raw = m.group(0)
            is_credit = "(" in raw or raw.strip().endswith("-")
            t_type = "credit" if is_credit else "debit"
            add_transaction(date_str, desc, float(amount_str), t_type)

        # Pattern 4: YYYY-MM-DD style (e.g. 2024-01-15)
        for m in re.finditer(
            r"(\d{4}-\d{2}-\d{2})\s+([^\$\(]+?)\s+\$?([\d,]+\.\d{2})\s*",
            full_text,
        ):
            date_str, desc, amount_str = m.group(1), m.group(2).strip(), m.group(3).replace(",", "")
            add_transaction(date_str, desc, float(amount_str), "debit")

        # Pattern 5: Line-by-line — date at start, amount at end (last number with 2 decimals)
        date_re = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})\s+(.+)$")
        amount_re = re.compile(r"[\$]?\s*-?([\d,]+\.\d{2})\s*$")
        skip_words = {"date", "description", "amount", "balance", "debit", "credit"}
        for line in lines:
            dm = date_re.match(line)
            if not dm:
                continue
            date_str, rest = dm.group(1), dm.group(2).strip()
            am = amount_re.search(rest)
            if not am:
                continue
            amount_str = am.group(1).replace(",", "")
            description = amount_re.sub("", rest).strip()
            if not description or len(description) < 2:
                continue
            if description.lower() in skip_words:
                continue
            is_credit = "(" in rest or rest.strip().endswith("-")
            t_type = "credit" if is_credit else "debit"
            add_transaction(date_str, description, float(amount_str), t_type)

        # Sort by date ascending (oldest first)
        transactions.sort(key=lambda t: t["date"])
        return transactions

    def _parse_date(self, date_str: str) -> datetime:
        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y']:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return datetime.now()

    def _extract_merchant(self, description: str) -> str:
        description = description.upper().strip()

        patterns = [
            r'^([A-Z0-9\s&\.\']+?)(?:\s+#\d+|\s+\d{10,})',
            r'^([A-Z0-9\s&\.\']+?)(?:\s+[A-Z]{2}\s*$)',
            r'^([A-Z0-9\s&\.\']+)',
        ]

        for pattern in patterns:
            match = re.match(pattern, description)
            if match:
                merchant = match.group(1).strip()
                merchant = re.sub(r'\s{2,}', ' ', merchant)
                return merchant

        return description[:50]
