import csv
import re
from typing import List, Dict
from datetime import datetime
import PyPDF2
from .base_parser import BankStatementParser


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
        transactions = []

        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)

            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text()

            transaction_pattern = r'(\d{2}/\d{2}/\d{4})\s+([^\$]+)\s+\$?([\d,]+\.\d{2})'

            matches = re.finditer(transaction_pattern, full_text)

            for match in matches:
                date_str = match.group(1)
                description = match.group(2).strip()
                amount_str = match.group(3).replace(',', '')

                is_debit = '-' in full_text[max(0, match.start()-10):match.start()]
                amount = float(amount_str)

                transaction_type = 'debit' if is_debit else 'credit'
                merchant = self._extract_merchant(description)

                transaction = {
                    'date': self._parse_date(date_str),
                    'merchant': merchant,
                    'description': description,
                    'amount': amount,
                    'transaction_type': transaction_type,
                }

                transactions.append(self.normalize_transaction(transaction))

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
