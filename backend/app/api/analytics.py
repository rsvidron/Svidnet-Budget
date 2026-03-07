from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models import User
from app.api.deps import get_current_user
from app.services.analytics_service import AnalyticsService, _parse_types

router = APIRouter()


def _parse_dates(start_str: Optional[str], end_str: Optional[str], preset: Optional[str]):
    now = datetime.now()
    today = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    if preset == "this_month":
        s = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        e = today
    elif preset == "last_3_months":
        s = (now - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)
        e = today
    elif preset == "last_6_months":
        s = (now - timedelta(days=180)).replace(hour=0, minute=0, second=0, microsecond=0)
        e = today
    elif preset == "last_year":
        s = (now - timedelta(days=365)).replace(hour=0, minute=0, second=0, microsecond=0)
        e = today
    else:
        if start_str:
            try:
                s = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            except Exception:
                s = (now - timedelta(days=30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            s = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if end_str:
            try:
                e = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except Exception:
                e = today
        else:
            e = today
    return s, e


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
    start_date: Optional[str] = Query(None, description="ISO date for custom range"),
    end_date: Optional[str] = Query(None, description="ISO date for custom range"),
    preset: Optional[str] = Query(None, description="this_month, last_3_months, last_6_months, last_year"),
    category_ids: Optional[str] = Query(None, description="Comma-separated category IDs"),
    category_exclude: bool = Query(False, description="If true, exclude selected categories"),
    transaction_types: Optional[str] = Query(None, description="Comma-separated: debit, credit, transfer"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analytics_service = AnalyticsService(db)
    start_dt, end_dt = _parse_dates(start_date, end_date, preset)
    cat_ids = None
    if category_ids and category_ids.strip():
        try:
            cat_ids = [int(x.strip()) for x in category_ids.split(",") if x.strip()]
        except ValueError:
            cat_ids = None
    types = _parse_types(
        [x.strip() for x in transaction_types.split(",")] if transaction_types else None
    )

    summary = analytics_service.get_summary_metrics(
        current_user.id, start_dt, end_dt, cat_ids, category_exclude, types
    )
    category_breakdown = analytics_service.get_category_breakdown(
        current_user.id, start_dt, end_dt, cat_ids, category_exclude, 15
    )
    largest_transactions = analytics_service.get_largest_transactions(
        current_user.id, start_dt, end_dt, cat_ids, category_exclude, 20
    )
    merchant_analysis = analytics_service.get_merchant_analysis(
        current_user.id, start_dt, end_dt, cat_ids, category_exclude, 10
    )
    monthly_trends = analytics_service.get_monthly_trends_filtered(
        current_user.id, start_dt, end_dt, cat_ids, category_exclude
    )
    category_trends = analytics_service.get_category_trends_over_time(
        current_user.id, start_dt, end_dt, 5
    )
    now = datetime.now()
    budget_progress = analytics_service.get_budget_progress(
        current_user.id, now.month, now.year
    )
    insights = analytics_service.get_insights(current_user.id, start_dt, end_dt)

    return {
        "filters": {
            "start_date": start_dt.isoformat() if hasattr(start_dt, "isoformat") else str(start_dt),
            "end_date": end_dt.isoformat() if hasattr(end_dt, "isoformat") else str(end_dt),
            "preset": preset,
            "category_ids": cat_ids,
            "category_exclude": category_exclude,
            "transaction_types": transaction_types,
        },
        "summary": summary,
        "category_breakdown": category_breakdown,
        "largest_transactions": largest_transactions,
        "merchant_analysis": merchant_analysis,
        "monthly_trends": monthly_trends,
        "category_trends": sorted(category_trends, key=lambda x: x["month"]) if category_trends else [],
        "budget_progress": budget_progress,
        "insights": insights,
        "spending_by_category": category_breakdown,
        "top_merchants": [{"merchant": m["merchant"], "count": m["count"], "total": m["total"]} for m in merchant_analysis],
    }
