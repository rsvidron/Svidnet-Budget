from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime


class BankStatementParser(ABC):
    @abstractmethod
    def parse_csv(self, file_path: str) -> List[Dict]:
        pass

    @abstractmethod
    def parse_pdf(self, file_path: str) -> List[Dict]:
        pass

    def normalize_transaction(self, raw_transaction: Dict) -> Dict:
        return {
            "date": raw_transaction.get("date"),
            "merchant": raw_transaction.get("merchant", "").strip(),
            "description": raw_transaction.get("description", "").strip(),
            "amount": abs(float(raw_transaction.get("amount", 0))),
            "transaction_type": raw_transaction.get("transaction_type"),
        }
