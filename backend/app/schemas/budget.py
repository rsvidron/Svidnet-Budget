from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BudgetBase(BaseModel):
    category_id: int
    amount: float
    period: str = "monthly"
    start_date: datetime
    end_date: Optional[datetime] = None


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    amount: Optional[float] = None
    period: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class Budget(BudgetBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
