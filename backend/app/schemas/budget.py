from pydantic import BaseModel, field_validator
from typing import Optional, Union
from datetime import datetime, date


def _parse_date(v: Union[str, datetime, date]) -> datetime:
    if v is None or (isinstance(v, str) and not v.strip()):
        raise ValueError("Date is required")
    if isinstance(v, datetime):
        return v
    if isinstance(v, date) and not isinstance(v, datetime):
        return datetime(v.year, v.month, v.day, 0, 0, 0)
    if isinstance(v, str):
        v = v.strip()
        if "T" in v or " " in v:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return datetime.fromisoformat(v + "T00:00:00")
    raise ValueError("Invalid date or datetime")


class BudgetBase(BaseModel):
    category_id: int
    amount: float
    period: str = "monthly"
    start_date: datetime
    end_date: Optional[datetime] = None

    @field_validator("start_date", mode="before")
    @classmethod
    def parse_start_date(cls, v):
        return _parse_date(v) if v is not None else v

    @field_validator("end_date", mode="before")
    @classmethod
    def parse_end_date(cls, v):
        return _parse_date(v) if v is not None else None


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    amount: Optional[float] = None
    period: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_optional_date(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return _parse_date(v)


class Budget(BudgetBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
