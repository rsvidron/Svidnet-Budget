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


def _extract_tables_pdfplumber(file_path: str) -> List[List[List[str]]]:
    """Extract tables from each page. Returns list of tables, each table is list of rows (list of cells)."""
    all_tables = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)
    return all_tables


def _extract_text_pypdf2(file_path: str) -> str:
    """Extract text using PyPDF2 as fallback."""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return "\n".join(
            (p.extract_text() or "") for p in reader.pages
        )


def _infer_statement_year(text: str) -> int:
    """Infer statement year from PDF text (e.g. 'January 2025', '01/2025', 'Statement Period')."""
    import time
    current_year = time.gmtime().tm_year
    # Statement Period: 01/01/2025 - 01/31/2025
    m = re.search(r"Statement\s+Period[:\s]+\d{1,2}/\d{1,2}/(\d{4})", text, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"\d{1,2}/\d{1,2}/(\d{4})", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", text, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"\d{1,2}/(\d{4})\b", text)
    if m:
        return int(m.group(1))
    return current_year


# Section headers for bank statement format (Deposits, Debit Card, Online Deductions)
SECTION_DEPOSITS = re.compile(
    r"Deposits\s+and\s+Other\s+Additions(?:\s*-?\s*continued)?",
    re.I,
)
SECTION_DEBIT_CARD = re.compile(
    r"Banking\s*/\s*Debit\s+Card\s+Withdrawals\s+and\s+Purchases(?:\s*-?\s*continued)?",
    re.I,
)
SECTION_ONLINE_DEDUCTIONS = re.compile(
    r"Online\s+and\s+Electronic\s+Banking\s+Deductions(?:\s*-?\s*continued)?",
    re.I,
)
# One line item: MM/DD  amount  description (amount may have comma: 2,115.64; optional $)
SECTION_ROW_PATTERN = re.compile(r"^(\d{2}/\d{2})\s+\$?([\d,]+\.\d{2})\s+(.*)$", re.M)


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

    def _parse_pdf_from_tables(self, file_path: str) -> List[Dict]:
        """Parse transactions from PDF tables (one row per transaction)."""
        tables = _extract_tables_pdfplumber(file_path)
        if not tables:
            return []

        transactions = []
        date_pattern = re.compile(r"(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})")
        amount_pattern = re.compile(r"[\$]?\s*-?\(?([\d,]+\.\d{2})\)?")
        header_like = {"date", "description", "amount", "debit", "credit", "balance", "posting", "transaction", "details"}

        for table in tables:
            if not table:
                continue
            rows = [[str(c or "").strip() for c in row] for row in table if row]
            if not rows:
                continue

            # Detect header row and column roles
            date_col = desc_col = amount_col = None
            start_row = 0
            for idx, row in enumerate(rows):
                for col, cell in enumerate(row):
                    if not cell:
                        continue
                    lower = cell.lower()
                    if "date" in lower or "posting" in lower:
                        date_col = col
                    if "description" in lower or "detail" in lower or "merchant" in lower or "payee" in lower:
                        desc_col = col
                    if "amount" in lower or "debit" in lower or "credit" in lower:
                        amount_col = col
                if date_col is not None or amount_col is not None:
                    start_row = idx + 1
                    break

            # If we found header, use column indices
            if date_col is not None or amount_col is not None:
                for row in rows[start_row:]:
                    if not row:
                        continue
                    date_str = None
                    amount_val = None
                    description = ""
                    for col, cell in enumerate(row):
                        if col >= len(row):
                            break
                        cell = row[col] if col < len(row) else ""
                        if not cell:
                            continue
                        if date_col is not None and col == date_col:
                            dm = date_pattern.search(cell)
                            if dm:
                                date_str = dm.group(1)
                        elif amount_col is not None and col == amount_col:
                            am = amount_pattern.search(cell)
                            if am:
                                try:
                                    amount_val = float(am.group(1).replace(",", ""))
                                except ValueError:
                                    pass
                        elif desc_col is not None and col == desc_col:
                            description = cell
                        elif date_col is None and date_pattern.search(cell):
                            date_str = date_pattern.search(cell).group(1)
                        elif amount_col is None and amount_pattern.search(cell):
                            try:
                                amount_val = float(amount_pattern.search(cell).group(1).replace(",", ""))
                            except (ValueError, AttributeError):
                                pass
                        elif not description and cell.lower() not in header_like:
                            description = cell if not description else description + " " + cell
                    if date_str and amount_val is not None and (description or any(row)):
                        if not description:
                            description = " ".join(c for c in row if c and c != date_str)
                        t_type = "credit" if amount_val < 0 or "(" in " ".join(row) else "debit"
                        transactions.append(
                            self.normalize_transaction({
                                "date": self._parse_date(date_str),
                                "merchant": self._extract_merchant(description),
                                "description": description,
                                "amount": abs(amount_val),
                                "transaction_type": t_type,
                            })
                        )
                continue

            # No header: infer from each row (date in one cell, amount in another, rest = description)
            for row in rows:
                if not row or not any(row):
                    continue
                date_str = None
                amount_val = None
                desc_parts = []
                for cell in row:
                    if not cell:
                        continue
                    dm = date_pattern.search(cell)
                    am = amount_pattern.search(cell)
                    if dm and not date_str:
                        date_str = dm.group(1)
                    elif am and amount_val is None:
                        try:
                            amount_val = float(am.group(1).replace(",", ""))
                        except ValueError:
                            pass
                    if not dm and not am and cell.lower() not in header_like:
                        desc_parts.append(cell)
                if date_str and amount_val is not None:
                    description = " ".join(desc_parts) if desc_parts else " ".join(c for c in row if c and c != date_str)
                    if description.lower() in header_like:
                        continue
                    t_type = "credit" if amount_val < 0 or any("(" in c for c in row) else "debit"
                    transactions.append(
                        self.normalize_transaction({
                            "date": self._parse_date(date_str),
                            "merchant": self._extract_merchant(description),
                            "description": description or "Transaction",
                            "amount": abs(amount_val),
                            "transaction_type": t_type,
                        })
                    )

        return transactions

    def _parse_pdf_from_text(self, file_path: str) -> List[Dict]:
        """Parse transactions from extracted text (line-by-line and date-chunk)."""
        full_text = _extract_text_pdfplumber(file_path)
        if not full_text or not full_text.strip():
            full_text = _extract_text_pypdf2(file_path)
        if not full_text or not full_text.strip():
            return []

        transactions = []
        seen = set()

        def add(date_str: str, description: str, amount: float, transaction_type: str) -> None:
            key = (date_str, (description or "")[:50], round(amount, 2))
            if key in seen:
                return
            seen.add(key)
            desc = (description or "").strip() or "Transaction"
            transactions.append(
                self.normalize_transaction({
                    "date": self._parse_date(date_str),
                    "merchant": self._extract_merchant(desc),
                    "description": desc,
                    "amount": abs(amount),
                    "transaction_type": transaction_type,
                })
            )

        # Normalize spaces but keep newlines
        full_text = re.sub(r"[ \t]+", " ", full_text)
        lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

        # --- Strategy 1: Split entire text by date pattern, then each chunk = one transaction ---
        # This catches "01/01/2024 DESC1 10.00 01/02/2024 DESC2 20.00" with no newlines
        date_re = re.compile(r"(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})")
        amount_re = re.compile(r"[\$]?\s*-?\(?([\d,]+\.\d{2})\)?\s*")
        chunks = date_re.split(full_text)
        # chunks[0] may be preamble, then [date1, text1, date2, text2, ...]
        for i in range(1, len(chunks) - 1, 2):
            if i + 1 >= len(chunks):
                break
            date_str = chunks[i].strip()
            block = chunks[i + 1].strip()
            if not date_str or not block:
                continue
            # Last number with 2 decimals in block is usually the amount
            amounts = amount_re.findall(block)
            if not amounts:
                continue
            amount_str = amounts[-1].replace(",", "")
            try:
                amount = float(amount_str)
            except ValueError:
                continue
            # Description = text before the last amount
            desc_block = amount_re.sub("", block)
            # Remove trailing amount text
            for _ in range(len(amounts) - 1):
                desc_block = amount_re.sub("", desc_block, count=1)
            description = " ".join(desc_block.split()).strip()
            if len(description) < 2:
                description = block[:80]
            is_credit = "(" in block or "-" in block
            add(date_str, description, amount, "credit" if is_credit else "debit")

        # --- Strategy 2: Every line that starts with date and contains an amount ---
        line_date_re = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})\s+(.+)$")
        line_amount_re = re.compile(r"[\$]?\s*-?\(?([\d,]+\.\d{2})\)?\s*$")
        skip_words = {"date", "description", "amount", "balance", "debit", "credit", "posting", "transaction"}
        for line in lines:
            m = line_date_re.match(line)
            if not m:
                continue
            date_str, rest = m.group(1), m.group(2).strip()
            am = line_amount_re.search(rest)
            if not am:
                continue
            amount_str = am.group(1).replace(",", "")
            try:
                amount = float(amount_str)
            except ValueError:
                continue
            description = line_amount_re.sub("", rest).strip()
            if not description or description.lower() in skip_words:
                continue
            is_credit = "(" in rest or rest.rstrip().endswith("-")
            add(date_str, description, amount, "credit" if is_credit else "debit")

        # --- Strategy 3: Global regex for date + ... + amount (multiline) ---
        for regex in (
            r"(\d{1,2}/\d{1,2}/\d{4})\s+([^\$\(\n]+?)\s+\$?([\d,]+\.\d{2})\s*",
            r"(\d{4}-\d{2}-\d{2})\s+([^\$\(\n]+?)\s+\$?([\d,]+\.\d{2})\s*",
            r"(\d{1,2}/\d{1,2}/\d{4})\s+(.+?)\s+\(([\d,]+\.\d{2})\)",
        ):
            for m in re.finditer(regex, full_text):
                date_str = m.group(1)
                amount_str = m.group(3).replace(",", "")
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue
                desc = m.group(2).strip()
                if not desc or desc.lower() in skip_words:
                    continue
                t_type = "credit" if "(" in m.group(0) else "debit"
                add(date_str, desc, amount, t_type)

        return transactions

    def _parse_pdf_sectioned(self, file_path: str) -> List[Dict]:
        """Parse PDF with 'Deposits and Other Additions', 'Banking/Debit Card Withdrawals', 'Online and Electronic Banking Deductions' sections."""
        full_text = _extract_text_pdfplumber(file_path)
        if not full_text or not full_text.strip():
            full_text = _extract_text_pypdf2(file_path)
        if not full_text:
            return []

        # Check if this looks like the sectioned bank format
        if not (
            SECTION_DEPOSITS.search(full_text)
            or SECTION_DEBIT_CARD.search(full_text)
            or SECTION_ONLINE_DEDUCTIONS.search(full_text)
        ):
            return []

        year = _infer_statement_year(full_text)
        transactions = []

        def parse_section_block(block: str, transaction_type: str) -> None:
            block = re.sub(r"[ \t]+", " ", block)
            lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
            current = None  # { date_str, amount, description }
            for line in lines:
                # Skip section header / column header lines
                if re.match(r"^(Date|Amount|Description)\s*$", line, re.I) or re.match(
                    r"^Date\s+Amount\s+Description\s*$", line, re.I
                ):
                    continue
                # Skip footer / summary lines
                if re.match(r"^There\s+(were|are)\s+\d+", line, re.I):
                    continue
                if re.match(r"^\d+\s+(other|Banking|Debit|POS)\s+", line, re.I):
                    continue
                m = SECTION_ROW_PATTERN.match(line)
                if m:
                    if current:
                        # Save previous
                        dt = self._parse_date(f"{current['date_str']}/{year}")
                        transactions.append(
                            self.normalize_transaction({
                                "date": dt,
                                "merchant": self._extract_merchant(current["description"]),
                                "description": current["description"],
                                "amount": current["amount"],
                                "transaction_type": current["transaction_type"],
                            })
                        )
                    current = {
                        "date_str": m.group(1),
                        "amount": float(m.group(2).replace(",", "")),
                        "description": m.group(3).strip(),
                        "transaction_type": transaction_type,
                    }
                else:
                    # Continuation of previous description (wrapped line)
                    if current and line and not re.match(r"^\d{2}/\d{2}\s+[\d,]+\.\d{2}", line):
                        current["description"] = (current["description"] + " " + line).strip()
            if current:
                dt = self._parse_date(f"{current['date_str']}/{year}")
                transactions.append(
                    self.normalize_transaction({
                        "date": dt,
                        "merchant": self._extract_merchant(current["description"]),
                        "description": current["description"],
                        "amount": current["amount"],
                        "transaction_type": current["transaction_type"],
                    })
                )

        # Split by section headers and parse each block
        section_pattern = re.compile(
            r"(Deposits\s+and\s+Other\s+Additions(?:\s*-?\s*continued)?"
            r"|Banking\s*/\s*Debit\s+Card\s+Withdrawals\s+and\s+Purchases(?:\s*-?\s*continued)?"
            r"|Online\s+and\s+Electronic\s+Banking\s+Deductions(?:\s*-?\s*continued)?)",
            re.I,
        )
        parts = section_pattern.split(full_text)
        # parts: [preamble, "Deposits...", content, "Banking...", content, ...]
        i = 1
        while i < len(parts) - 1:
            section_name = parts[i].strip()
            content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            i += 2
            # Trim content until next section (or end)
            next_section = section_pattern.search(content)
            if next_section:
                content = content[: next_section.start()]
            if SECTION_DEPOSITS.match(section_name):
                parse_section_block(content, "credit")
            elif SECTION_DEBIT_CARD.match(section_name) or SECTION_ONLINE_DEDUCTIONS.match(section_name):
                parse_section_block(content, "debit")
        transactions.sort(key=lambda t: t["date"])
        return transactions

    def parse_pdf(self, file_path: str) -> List[Dict]:
        # 1) Try sectioned format first (Deposits / Debit Card / Online Deductions)
        sectioned = self._parse_pdf_sectioned(file_path)
        if sectioned:
            return sectioned

        # 2) Try tables (many bank statements are tabular)
        from_tables = self._parse_pdf_from_tables(file_path)
        if from_tables:
            from_tables.sort(key=lambda t: t["date"])
            return from_tables

        # 3) Parse from raw text (line + date-chunk strategies)
        from_text = self._parse_pdf_from_text(file_path)
        from_text.sort(key=lambda t: t["date"])
        return from_text

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
