from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.transaction import TransactionType


class TransactionBase(BaseModel):
    date: datetime
    merchant: str
    description: Optional[str] = None
    amount: float
    transaction_type: TransactionType
    category_id: Optional[int] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    merchant: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    category_id: Optional[int] = None


class Transaction(TransactionBase):
    id: int
    user_id: int
    is_recurring: bool
    recurring_pattern: Optional[str] = None
    is_manually_categorized: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category_id: Optional[int] = None
    merchant: Optional[str] = None
    transaction_type: Optional[TransactionType] = None
