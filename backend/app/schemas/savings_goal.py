from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SavingsGoalBase(BaseModel):
    name: str
    target_amount: float
    target_date: Optional[datetime] = None
    description: Optional[str] = None


class SavingsGoalCreate(SavingsGoalBase):
    pass


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    target_date: Optional[datetime] = None
    description: Optional[str] = None
    is_completed: Optional[bool] = None


class SavingsGoal(SavingsGoalBase):
    id: int
    user_id: int
    current_amount: float
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True
