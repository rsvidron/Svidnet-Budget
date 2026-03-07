from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, extract, case, and_
from sqlalchemy.orm import Session
from sqlalchemy.sql import cast
from app.models import Transaction, Category, Budget, TransactionType


def _parse_types(types: Optional[List[str]]) -> Optional[List[TransactionType]]:
    if not types:
        return None
    out = []
    for t in types:
        t = (t or "").strip().lower()
        if t == "debit":
            out.append(TransactionType.DEBIT)
        elif t == "credit":
            out.append(TransactionType.CREDIT)
        elif t == "transfer":
            out.append(TransactionType.TRANSFER)
    return out if out else None


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def _filter_query(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        category_ids: Optional[List[int]] = None,
        category_exclude: bool = False,
        transaction_types: Optional[List[TransactionType]] = None,
    ):
        """Build common filter for transaction queries."""
        q = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        if category_ids is not None:
            if category_exclude:
                q = q.filter(
                    (Transaction.category_id.is_(None)) | (~Transaction.category_id.in_(category_ids))
                )
            else:
                q = q.filter(Transaction.category_id.in_(category_ids))
        if transaction_types is not None:
            q = q.filter(Transaction.transaction_type.in_(transaction_types))
        return q

    def get_summary_metrics(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        category_ids: Optional[List[int]] = None,
        category_exclude: bool = False,
        transaction_types: Optional[List[TransactionType]] = None,
    ) -> Dict:
        """Total spending, income, net, avg monthly, largest expense, count; with previous period comparison."""
        types = transaction_types or [TransactionType.DEBIT, TransactionType.CREDIT, TransactionType.TRANSFER]
        period_days = (end_date - start_date).days or 1
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days)

        def _totals(s, e):
            base = self._filter_query(user_id, s, e, category_ids, category_exclude, types)
            expenses = self._filter_query(user_id, s, e, category_ids, category_exclude, types).filter(
                Transaction.transaction_type == TransactionType.DEBIT
            ).with_entities(func.coalesce(func.sum(Transaction.amount), 0)).scalar() or 0
            income = self._filter_query(user_id, s, e, category_ids, category_exclude, types).filter(
                Transaction.transaction_type == TransactionType.CREDIT
            ).with_entities(func.coalesce(func.sum(Transaction.amount), 0)).scalar() or 0
            cnt = self._filter_query(user_id, s, e, category_ids, category_exclude, types).count()
            largest_row = self._filter_query(user_id, s, e, category_ids, category_exclude, types).filter(
                Transaction.transaction_type == TransactionType.DEBIT
            ).order_by(Transaction.amount.desc()).with_entities(Transaction.amount).first()
            largest = float(largest_row[0]) if largest_row and largest_row[0] is not None else 0
            return float(expenses), float(income), cnt, largest

        exp, inc, cnt, largest = _totals(start_date, end_date)
        prev_exp, prev_inc, prev_cnt, _ = _totals(prev_start, prev_end)
        months = max(period_days / 30.0, 1 / 30.0)
        prev_months = max(period_days / 30.0, 1 / 30.0)

        def _pct(current, previous):
            if previous == 0:
                return (100.0 if current > 0 else 0.0)
            return round((current - previous) / previous * 100, 1)

        return {
            "total_spending": round(exp, 2),
            "total_income": round(inc, 2),
            "net_cash_flow": round(inc - exp, 2),
            "average_monthly_spending": round(exp / months, 2),
            "largest_single_expense": round(largest, 2),
            "transaction_count": cnt,
            "previous_period": {
                "total_spending": round(prev_exp, 2),
                "total_income": round(prev_inc, 2),
                "net_cash_flow": round(prev_inc - prev_exp, 2),
                "transaction_count": prev_cnt,
            },
            "change_vs_previous": {
                "total_spending_pct": _pct(exp, prev_exp),
                "total_income_pct": _pct(inc, prev_inc),
                "net_cash_flow_pct": _pct(inc - exp, prev_inc - prev_exp) if (prev_inc - prev_exp) != 0 else 0,
                "transaction_count_pct": _pct(cnt, prev_cnt) if prev_cnt else 0,
            },
        }

    def get_category_breakdown(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        category_ids: Optional[List[int]] = None,
        category_exclude: bool = False,
        limit: int = 15,
    ) -> List[Dict]:
        """Spending by category with total, pct, and change vs previous period."""
        period_days = (end_date - start_date).days or 1
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days)

        q = self.db.query(
            Category.id,
            Category.name,
            Category.color,
            func.sum(Transaction.amount).label("total"),
        ).join(Transaction, Transaction.category_id == Category.id).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        if category_ids is not None:
            if category_exclude:
                q = q.filter(~Category.id.in_(category_ids))
            else:
                q = q.filter(Category.id.in_(category_ids))
        q = q.group_by(Category.id, Category.name, Category.color).order_by(func.sum(Transaction.amount).desc())
        rows = q.limit(limit).all()
        total = sum(float(r.total) for r in rows)
        prev_totals = {}
        for r in rows:
            prev = self.db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == r.id,
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.date >= prev_start,
                Transaction.date <= prev_end,
            ).scalar() or 0
            prev_totals[r.id] = float(prev)
        return [
            {
                "category_id": r.id,
                "category": r.name,
                "color": r.color,
                "amount": round(float(r.total), 2),
                "pct_of_total": round(float(r.total) / total * 100, 1) if total > 0 else 0,
                "change_vs_previous_pct": round(
                    (float(r.total) - prev_totals[r.id]) / prev_totals[r.id] * 100, 1
                ) if prev_totals[r.id] else (100.0 if float(r.total) > 0 else 0.0),
            }
            for r in rows
        ]

    def get_largest_transactions(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        category_ids: Optional[List[int]] = None,
        category_exclude: bool = False,
        limit: int = 20,
    ) -> List[Dict]:
        """Largest debit transactions (date, merchant, category, amount)."""
        q = (
            self.db.query(Transaction, Category.name.label("category_name"))
            .outerjoin(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.DEBIT,
                Transaction.date >= start_date,
                Transaction.date <= end_date,
            )
        )
        if category_ids is not None:
            if category_exclude:
                q = q.filter(
                    (Transaction.category_id.is_(None)) | (~Transaction.category_id.in_(category_ids))
                )
            else:
                q = q.filter(Transaction.category_id.in_(category_ids))
        rows = q.order_by(Transaction.amount.desc()).limit(limit).all()
        out = []
        for row in rows:
            t = row[0]
            cat_name = row[1] if len(row) > 1 else "Uncategorized"
            out.append({
                "id": t.id,
                "date": t.date.isoformat() if hasattr(t.date, "isoformat") else str(t.date),
                "merchant": t.merchant,
                "category": cat_name or "Uncategorized",
                "amount": round(float(t.amount), 2),
            })
        return out

    def get_merchant_analysis(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        category_ids: Optional[List[int]] = None,
        category_exclude: bool = False,
        limit: int = 10,
    ) -> List[Dict]:
        """Top merchants: total, count, average transaction amount."""
        q = self.db.query(
            Transaction.merchant,
            func.count(Transaction.id).label("count"),
            func.sum(Transaction.amount).label("total"),
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        if category_ids is not None:
            if category_exclude:
                q = q.filter(
                    (Transaction.category_id.is_(None)) | (~Transaction.category_id.in_(category_ids))
                )
            else:
                q = q.filter(Transaction.category_id.in_(category_ids))
        rows = q.group_by(Transaction.merchant).order_by(func.sum(Transaction.amount).desc()).limit(limit).all()
        return [
            {
                "merchant": r.merchant,
                "count": r.count,
                "total": round(float(r.total), 2),
                "average": round(float(r.total) / r.count, 2) if r.count else 0,
            }
            for r in rows
        ]

    def get_monthly_trends_filtered(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        category_ids: Optional[List[int]] = None,
        category_exclude: bool = False,
    ) -> List[Dict]:
        """Monthly aggregates: income, expenses, net."""
        q = self.db.query(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            func.sum(case(
                (Transaction.transaction_type == TransactionType.DEBIT, Transaction.amount),
                else_=0,
            )).label("expenses"),
            func.sum(case(
                (Transaction.transaction_type == TransactionType.CREDIT, Transaction.amount),
                else_=0,
            )).label("income"),
        ).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        if category_ids is not None:
            if category_exclude:
                q = q.filter(
                    (Transaction.category_id.is_(None)) | (~Transaction.category_id.in_(category_ids))
                )
            else:
                q = q.filter(Transaction.category_id.in_(category_ids))
        rows = q.group_by(extract("year", Transaction.date), extract("month", Transaction.date)).order_by("year", "month").all()
        return [
            {
                "month": f"{int(row.year)}-{int(row.month):02d}",
                "expenses": round(float(row.expenses), 2),
                "income": round(float(row.income), 2),
                "net": round(float(row.income - row.expenses), 2),
            }
            for row in rows
        ]

    def get_category_trends_over_time(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        top_n: int = 5,
    ) -> List[Dict]:
        """Time series of top spending categories by month."""
        cat_totals = self.db.query(
            Transaction.category_id,
            func.sum(Transaction.amount).label("total"),
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        ).group_by(Transaction.category_id).order_by(func.sum(Transaction.amount).desc()).limit(top_n).all()
        cat_ids = [r.category_id for r in cat_totals if r.category_id]
        if not cat_ids:
            return []
        cat_names = {c.id: c.name for c in self.db.query(Category).filter(Category.id.in_(cat_ids)).all()}
        months_q = self.db.query(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            Transaction.category_id,
            func.sum(Transaction.amount).label("total"),
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.category_id.in_(cat_ids),
        ).group_by(extract("year", Transaction.date), extract("month", Transaction.date), Transaction.category_id).order_by("year", "month").all()
        by_month = {}
        for row in months_q:
            key = f"{int(row.year)}-{int(row.month):02d}"
            if key not in by_month:
                by_month[key] = {"month": key}
            by_month[key][cat_names.get(row.category_id, "Other")] = round(float(row.total), 2)
        for key in by_month:
            for cid in cat_ids:
                name = cat_names.get(cid)
                if name and name not in by_month[key]:
                    by_month[key][name] = 0
        return [by_month[k] for k in sorted(by_month.keys())]

    def get_insights(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict]:
        """Automated insights: spending changes, top categories, largest expense."""
        period_days = (end_date - start_date).days or 1
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=period_days)
        insights = []
        cat_now = self.get_spending_by_category(user_id, start_date, end_date)
        cat_prev = self.get_spending_by_category(user_id, prev_start, prev_end)
        prev_by_name = {c["category"]: c["amount"] for c in cat_prev}
        for c in cat_now:
            prev = prev_by_name.get(c["category"], 0)
            if prev > 0 and c["amount"] != prev:
                pct = round((c["amount"] - prev) / prev * 100)
                if abs(pct) >= 10:
                    insights.append({
                        "type": "category_change",
                        "text": f"{c['category']} spending {'increased' if pct > 0 else 'decreased'} {abs(pct)}% compared to previous period.",
                    })
        total_sub = sum(c["amount"] for c in cat_now if "ubscription" in c["category"] or "Subscription" in c["category"])
        if total_sub > 0:
            insights.append({"type": "subscriptions", "text": f"Subscriptions cost ${total_sub:.0f} this period."})
        largest = self.db.query(Transaction.merchant, Transaction.amount, Category.name).join(
            Category, Transaction.category_id == Category.id, isouter=True
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        ).order_by(Transaction.amount.desc()).first()
        if largest:
            merchant, amount, cat_name = largest[0], largest[1], (largest[2] or "Uncategorized")
            insights.append({
                "type": "largest_expense",
                "text": f"Your largest expense was ${amount:,.0f} for {cat_name} ({merchant}).",
            })
        return insights[:10]

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
            func.sum(case(
                (Transaction.transaction_type == TransactionType.DEBIT, Transaction.amount),
                else_=0
            )).label('expenses'),
            func.sum(case(
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
