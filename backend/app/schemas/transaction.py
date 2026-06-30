from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.transaction import TransactionType


class TransactionBase(BaseModel):
    date: datetime
    merchant: str
    description: Optional[str] = None
    amount: float
    transaction_type: TransactionType
    category_id: Optional[int] = None
    account_id: Optional[int] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    merchant: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None


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
    account_id: Optional[int] = None
    merchant: Optional[str] = None
    transaction_type: Optional[TransactionType] = None


class BulkUpdateRequest(BaseModel):
    ids: List[int]
    category_id: Optional[int] = None
    account_id: Optional[int] = None


class BulkUpdateByMerchantRequest(BaseModel):
    merchant: str
    normalized: bool = False
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    filter_account_id: Optional[int] = None


class MerchantGroup(BaseModel):
    merchant: str
    normalized_key: str
    variants: List[str] = []
    count: int
    total_debit: float
    total_credit: float
    first_date: datetime
    last_date: datetime
    category_ids: List[int]
    account_ids: List[int]


class CategoryGroup(BaseModel):
    category_id: Optional[int] = None
    category_name: str
    count: int
    total_debit: float
    total_credit: float
    first_date: datetime
    last_date: datetime
    top_merchants: List[str]
    account_ids: List[int]
