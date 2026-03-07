from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import Category, CategorizationRule, Transaction


class CategorizationService:
    DEFAULT_CATEGORIES = [
        {"name": "Groceries", "color": "#10B981", "keywords": ["grocery", "walmart", "target", "kroger", "publix", "safeway", "whole foods", "trader joe"]},
        {"name": "Restaurants", "color": "#F59E0B", "keywords": ["restaurant", "mcdonald", "burger", "pizza", "starbucks", "coffee", "cafe", "dining", "doordash", "ubereats"]},
        {"name": "Mortgage", "color": "#EF4444", "keywords": ["mortgage", "rent", "housing", "apartment", "lease"]},
        {"name": "Utilities", "color": "#8B5CF6", "keywords": ["electric", "gas", "water", "internet", "cable", "phone", "utility", "verizon", "att", "comcast"]},
        {"name": "Subscriptions", "color": "#EC4899", "keywords": ["netflix", "spotify", "hulu", "amazon prime", "disney", "subscription", "apple music", "youtube premium"]},
        {"name": "Travel", "color": "#06B6D4", "keywords": ["airline", "hotel", "airbnb", "uber", "lyft", "gas station", "shell", "exxon", "chevron", "rental car"]},
        {"name": "Entertainment", "color": "#F97316", "keywords": ["theater", "cinema", "movie", "concert", "sports", "game", "entertainment", "ticketmaster"]},
        {"name": "Income", "color": "#22C55E", "keywords": ["payroll", "salary", "deposit", "income", "transfer from", "reimbursement"]},
        {"name": "Healthcare", "color": "#DC2626", "keywords": ["pharmacy", "doctor", "hospital", "medical", "cvs", "walgreens", "health", "dental"]},
        {"name": "Shopping", "color": "#A855F7", "keywords": ["amazon", "ebay", "shop", "store", "retail", "best buy", "home depot", "lowes"]},
        {"name": "Transfers", "color": "#6B7280", "keywords": ["transfer", "payment", "check"]},
        {"name": "Uncategorized", "color": "#9CA3AF", "keywords": []},
    ]

    def __init__(self, db: Session):
        self.db = db

    def initialize_default_categories(self, user_id: int) -> List[Category]:
        categories = []
        for cat_data in self.DEFAULT_CATEGORIES:
            category = Category(
                user_id=user_id,
                name=cat_data["name"],
                color=cat_data["color"]
            )
            self.db.add(category)
            self.db.flush()

            for keyword in cat_data["keywords"]:
                rule = CategorizationRule(
                    user_id=user_id,
                    category_id=category.id,
                    keyword=keyword.lower(),
                    priority=0
                )
                self.db.add(rule)

            categories.append(category)

        self.db.commit()
        return categories

    def categorize_transaction(self, user_id: int, merchant: str, description: str) -> Optional[int]:
        text = f"{merchant} {description}".lower()

        rules = self.db.query(CategorizationRule).filter(
            CategorizationRule.user_id == user_id
        ).order_by(CategorizationRule.priority.desc()).all()

        for rule in rules:
            if rule.keyword.lower() in text:
                return rule.category_id

        past_transactions = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.merchant.ilike(f"%{merchant}%"),
            Transaction.category_id.isnot(None)
        ).first()

        if past_transactions:
            return past_transactions.category_id

        uncategorized = self.db.query(Category).filter(
            Category.user_id == user_id,
            Category.name == "Uncategorized"
        ).first()

        return uncategorized.id if uncategorized else None

    def add_rule(self, user_id: int, category_id: int, keyword: str, priority: int = 0) -> CategorizationRule:
        rule = CategorizationRule(
            user_id=user_id,
            category_id=category_id,
            keyword=keyword.lower(),
            priority=priority
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def recategorize_all(self, user_id: int):
        transactions = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.is_manually_categorized == False
        ).all()

        for transaction in transactions:
            category_id = self.categorize_transaction(
                user_id,
                transaction.merchant,
                transaction.description or ""
            )
            if category_id:
                transaction.category_id = category_id

        self.db.commit()
