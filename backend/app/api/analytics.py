from typing import List, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models import User
from app.api.deps import get_current_user
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/spending-by-category")
def get_spending_by_category(
    start_date: datetime = None,
    end_date: datetime = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not start_date:
        start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = datetime.now()

    analytics_service = AnalyticsService(db)
    data = analytics_service.get_spending_by_category(current_user.id, start_date, end_date)

    return {"data": data}


@router.get("/monthly-trends")
def get_monthly_trends(
    months: int = 6,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analytics_service = AnalyticsService(db)
    data = analytics_service.get_monthly_trends(current_user.id, months)

    return {"data": data}


@router.get("/budget-progress")
def get_budget_progress(
    month: int = None,
    year: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not month:
        month = datetime.now().month
    if not year:
        year = datetime.now().year

    analytics_service = AnalyticsService(db)
    data = analytics_service.get_budget_progress(current_user.id, month, year)

    return {"data": data}


@router.get("/top-merchants")
def get_top_merchants(
    start_date: datetime = None,
    end_date: datetime = None,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not start_date:
        start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = datetime.now()

    analytics_service = AnalyticsService(db)
    data = analytics_service.get_top_merchants(current_user.id, start_date, end_date, limit)

    return {"data": data}


@router.get("/recurring-transactions")
def get_recurring_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analytics_service = AnalyticsService(db)
    data = analytics_service.detect_recurring_transactions(current_user.id)

    return {"data": data}


@router.get("/dashboard")
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analytics_service = AnalyticsService(db)

    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    spending_by_category = analytics_service.get_spending_by_category(
        current_user.id, start_of_month, now
    )

    monthly_trends = analytics_service.get_monthly_trends(current_user.id, 6)

    budget_progress = analytics_service.get_budget_progress(
        current_user.id, now.month, now.year
    )

    top_merchants = analytics_service.get_top_merchants(
        current_user.id, start_of_month, now, 5
    )

    total_spent = sum(cat["amount"] for cat in spending_by_category)
    total_budgeted = sum(budget["budgeted"] for budget in budget_progress)

    return {
        "summary": {
            "total_spent_this_month": total_spent,
            "total_budgeted": total_budgeted,
            "budget_remaining": total_budgeted - total_spent,
        },
        "spending_by_category": spending_by_category,
        "monthly_trends": monthly_trends,
        "budget_progress": budget_progress,
        "top_merchants": top_merchants,
    }
