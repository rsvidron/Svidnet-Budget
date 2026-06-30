from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.core.database import get_db
from app.models import User, Account, Transaction, AccountType
from app.models.transaction import TransactionType
from app.schemas.account import (
    Account as AccountSchema,
    AccountCreate,
    AccountUpdate,
    AccountWithStats,
)
from app.api.deps import get_current_user

router = APIRouter()


def get_or_create_account(
    db: Session,
    user_id: int,
    name: str,
    account_type: AccountType = AccountType.OTHER,
    institution: Optional[str] = None,
    is_default: bool = False,
) -> Account:
    """Find an account by case-insensitive name for the user, or create one."""
    name = (name or "").strip() or "Default"
    existing = (
        db.query(Account)
        .filter(Account.user_id == user_id, func.lower(Account.name) == name.lower())
        .first()
    )
    if existing:
        return existing
    account = Account(
        user_id=user_id,
        name=name,
        account_type=account_type,
        institution=institution,
        is_default=is_default,
    )
    db.add(account)
    db.flush()
    return account


@router.get("/", response_model=List[AccountWithStats])
def list_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Account,
            func.count(Transaction.id).label("txn_count"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.transaction_type == TransactionType.CREDIT, Transaction.amount),
                        else_=-Transaction.amount,
                    )
                ),
                0.0,
            ).label("balance"),
        )
        .outerjoin(Transaction, Transaction.account_id == Account.id)
        .filter(Account.user_id == current_user.id)
        .group_by(Account.id)
        .order_by(Account.is_default.desc(), Account.name.asc())
        .all()
    )

    result = []
    for account, txn_count, balance in rows:
        item = AccountWithStats.model_validate(account, from_attributes=True)
        item.transaction_count = int(txn_count or 0)
        item.balance = round(float(balance or 0.0), 2)
        result.append(item)
    return result


@router.post("/", response_model=AccountSchema, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account name is required",
        )

    existing = (
        db.query(Account)
        .filter(Account.user_id == current_user.id, func.lower(Account.name) == name.lower())
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this name already exists",
        )

    has_any = db.query(Account).filter(Account.user_id == current_user.id).first() is not None
    account = Account(
        user_id=current_user.id,
        name=name,
        account_type=payload.account_type,
        institution=payload.institution,
        is_default=not has_any,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=AccountSchema)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = (
        db.query(Account)
        .filter(Account.id == account_id, Account.user_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        new_name = (data["name"] or "").strip()
        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account name cannot be empty",
            )
        clash = (
            db.query(Account)
            .filter(
                Account.user_id == current_user.id,
                Account.id != account_id,
                func.lower(Account.name) == new_name.lower(),
            )
            .first()
        )
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another account already uses this name",
            )
        data["name"] = new_name

    for k, v in data.items():
        setattr(account, k, v)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}")
def delete_account(
    account_id: int,
    reassign_to: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = (
        db.query(Account)
        .filter(Account.id == account_id, Account.user_id == current_user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    total = db.query(Account).filter(Account.user_id == current_user.id).count()
    txn_count = (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id, Transaction.account_id == account_id)
        .count()
    )

    if txn_count > 0:
        if reassign_to is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account has {txn_count} transactions. Provide reassign_to=<account_id> to move them.",
            )
        target = (
            db.query(Account)
            .filter(Account.id == reassign_to, Account.user_id == current_user.id)
            .first()
        )
        if not target or target.id == account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reassign_to must reference a different account you own",
            )
        db.query(Transaction).filter(
            Transaction.user_id == current_user.id,
            Transaction.account_id == account_id,
        ).update({"account_id": target.id}, synchronize_session=False)
    elif total <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your last account",
        )

    was_default = account.is_default
    db.delete(account)
    db.flush()

    if was_default:
        replacement = (
            db.query(Account)
            .filter(Account.user_id == current_user.id)
            .order_by(Account.created_at.asc())
            .first()
        )
        if replacement:
            replacement.is_default = True

    db.commit()
    return {"message": "Account deleted", "reassigned_transactions": txn_count}
