from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.account import AccountType


class AccountBase(BaseModel):
    name: str
    account_type: AccountType = AccountType.OTHER
    institution: Optional[str] = None


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    account_type: Optional[AccountType] = None
    institution: Optional[str] = None


class Account(AccountBase):
    id: int
    user_id: int
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AccountWithStats(Account):
    transaction_count: int = 0
    balance: float = 0.0
