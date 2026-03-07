from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from sqlalchemy.orm import Session
from app.models import Transaction, Category, Budget, TransactionType


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_spending_by_category(self, user_id: int, start_date: datetime, end_date: datetime) -> List[Dict]:
        results = self.db.query(
            Category.name,
            Category.color,
            func.sum(Transaction.amount).label('total')
        ).join(
            Transaction, Transaction.category_id == Category.id
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).group_by(
            Category.id, Category.name, Category.color
        ).all()

        return [
            {
                "category": row.name,
                "color": row.color,
                "amount": float(row.total),
            }
            for row in results
        ]

    def get_monthly_trends(self, user_id: int, months: int = 6) -> List[Dict]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)

        results = self.db.query(
            extract('year', Transaction.date).label('year'),
            extract('month', Transaction.date).label('month'),
            func.sum(func.case(
                (Transaction.transaction_type == TransactionType.DEBIT, Transaction.amount),
                else_=0
            )).label('expenses'),
            func.sum(func.case(
                (Transaction.transaction_type == TransactionType.CREDIT, Transaction.amount),
                else_=0
            )).label('income')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).group_by(
            extract('year', Transaction.date),
            extract('month', Transaction.date)
        ).order_by(
            'year', 'month'
        ).all()

        return [
            {
                "month": f"{int(row.year)}-{int(row.month):02d}",
                "expenses": float(row.expenses),
                "income": float(row.income),
                "net": float(row.income - row.expenses)
            }
            for row in results
        ]

    def get_budget_progress(self, user_id: int, month: int, year: int) -> List[Dict]:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        budgets = self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.start_date <= end_date,
            (Budget.end_date.is_(None)) | (Budget.end_date >= start_date)
        ).all()

        results = []
        for budget in budgets:
            spent = self.db.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == budget.category_id,
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.date >= start_date,
                Transaction.date < end_date
            ).scalar() or 0

            results.append({
                "category": budget.category.name,
                "budgeted": float(budget.amount),
                "spent": float(spent),
                "remaining": float(budget.amount - spent),
                "percentage": (float(spent) / float(budget.amount) * 100) if budget.amount > 0 else 0
            })

        return results

    def get_top_merchants(self, user_id: int, start_date: datetime, end_date: datetime, limit: int = 10) -> List[Dict]:
        results = self.db.query(
            Transaction.merchant,
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).group_by(
            Transaction.merchant
        ).order_by(
            func.sum(Transaction.amount).desc()
        ).limit(limit).all()

        return [
            {
                "merchant": row.merchant,
                "count": row.count,
                "total": float(row.total),
            }
            for row in results
        ]

    def detect_recurring_transactions(self, user_id: int) -> List[Dict]:
        transactions = self.db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(Transaction.merchant, Transaction.date).all()

        merchant_groups = {}
        for trans in transactions:
            if trans.merchant not in merchant_groups:
                merchant_groups[trans.merchant] = []
            merchant_groups[trans.merchant].append(trans)

        recurring = []
        for merchant, trans_list in merchant_groups.items():
            if len(trans_list) < 3:
                continue

            amounts = [t.amount for t in trans_list]
            avg_amount = sum(amounts) / len(amounts)
            amount_variance = sum((a - avg_amount) ** 2 for a in amounts) / len(amounts)

            if amount_variance < (avg_amount * 0.1) ** 2:
                dates = [t.date for t in trans_list]
                date_diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]

                if date_diffs:
                    avg_interval = sum(date_diffs) / len(date_diffs)

                    if 25 <= avg_interval <= 35:
                        pattern = "monthly"
                    elif 85 <= avg_interval <= 95:
                        pattern = "quarterly"
                    elif 360 <= avg_interval <= 370:
                        pattern = "yearly"
                    else:
                        pattern = f"every {int(avg_interval)} days"

                    recurring.append({
                        "merchant": merchant,
                        "amount": round(avg_amount, 2),
                        "pattern": pattern,
                        "count": len(trans_list)
                    })

        return recurring
