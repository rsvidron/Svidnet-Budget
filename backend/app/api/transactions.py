from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime
import os
from app.core.database import get_db
from app.core.config import settings
from app.models import User, Transaction, Category, Account, AccountType
from app.models.transaction import TransactionType
from app.schemas.transaction import (
    Transaction as TransactionSchema,
    TransactionCreate,
    TransactionUpdate,
    TransactionFilter,
    BulkUpdateRequest,
    BulkUpdateByMerchantRequest,
    MerchantGroup,
    CategoryGroup,
)
from app.api.deps import get_current_user
from app.api.accounts import get_or_create_account
from app.parsers import PNCParser
from app.parsers.account_activity_parser import (
    parse_account_activity_csv,
    is_account_activity_csv,
)
from app.services.categorization_service import CategorizationService

router = APIRouter()

# Default colors for auto-created categories (from CSV)
DEFAULT_CATEGORY_COLORS = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
    "#EC4899", "#06B6D4", "#84CC16", "#F97316", "#6366F1",
]


def _get_or_create_category(db: Session, user_id: int, name: Optional[str]) -> Optional[int]:
    """Get existing category by name (case-insensitive) or create one. Returns category_id or None."""
    if not name or not name.strip():
        return None
    name = name.strip()
    existing = (
        db.query(Category)
        .filter(Category.user_id == user_id, func.lower(Category.name) == name.lower())
        .first()
    )
    if existing:
        return existing.id
    color = DEFAULT_CATEGORY_COLORS[hash(name) % len(DEFAULT_CATEGORY_COLORS)]
    category = Category(user_id=user_id, name=name, color=color)
    db.add(category)
    db.flush()
    return category.id


def _transaction_duplicate_key(trans) -> tuple:
    """Normalized key for duplicate check: (date_only, merchant_lower_stripped, amount_rounded)."""
    if hasattr(trans, "date"):
        d = trans.date.date() if hasattr(trans.date, "date") else trans.date
    else:
        d = trans["date"]
        if hasattr(d, "date"):
            d = d.date()
    merchant = (trans.get("merchant") if isinstance(trans, dict) else trans.merchant) or ""
    merchant = str(merchant).strip().lower()[:200]
    amount = trans.get("amount") if isinstance(trans, dict) else trans.amount
    amount = round(float(amount), 2)
    return (d, merchant, amount)


def _existing_transaction_keys(db: Session, user_id: int, min_date, max_date) -> set:
    """Return set of (date, merchant, amount) for existing transactions in the date range."""
    q = (
        db.query(
            func.date(Transaction.date).label("d"),
            func.lower(func.trim(Transaction.merchant)).label("m"),
            Transaction.amount,
        )
        .filter(Transaction.user_id == user_id)
        .filter(func.date(Transaction.date) >= min_date)
        .filter(func.date(Transaction.date) <= max_date)
    )
    return set((row.d, (row.m or "")[:200], round(float(row.amount), 2)) for row in q.all())


def _infer_account_for_upload(file_name: str, file_ext: str, file_path: str) -> tuple[str, AccountType]:
    """Pick an account name + type based on the file. Lightweight heuristics."""
    name_lc = (file_name or "").lower()
    if file_ext == ".csv" and is_account_activity_csv(file_path):
        # Savings export has no Category column; the parser already knows. Re-detect cheaply.
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                header = f.readline().lower()
            if "category" not in header:
                return ("PNC Savings", AccountType.SAVINGS)
        except Exception:
            pass
        return ("PNC Checking", AccountType.CHECKING)
    if file_ext == ".pdf":
        if "savings" in name_lc:
            return ("PNC Savings", AccountType.SAVINGS)
        if "credit" in name_lc or "card" in name_lc:
            return ("PNC Credit Card", AccountType.CREDIT)
        return ("PNC Checking", AccountType.CHECKING)
    # Generic CSV: fall back to checking
    return ("PNC Checking", AccountType.CHECKING)


@router.get("/", response_model=List[TransactionSchema])
def get_transactions(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category_id: Optional[str] = None,
    account_id: Optional[str] = None,
    merchant: Optional[str] = None,
    sort_by: Optional[str] = "date",
    sort_order: Optional[str] = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if category_id and category_id.strip():
        try:
            cat_id = int(category_id)
            query = query.filter(Transaction.category_id == cat_id)
        except ValueError:
            pass  # Ignore invalid category_id
    if account_id and account_id.strip():
        try:
            acc_id = int(account_id)
            query = query.filter(Transaction.account_id == acc_id)
        except ValueError:
            pass
    if merchant and merchant.strip():
        query = query.filter(Transaction.merchant.ilike(f"%{merchant}%"))

    # Apply sorting
    sort_column_map = {
        "date": Transaction.date,
        "merchant": Transaction.merchant,
        "category": Transaction.category_id,
        "amount": Transaction.amount,
        "type": Transaction.transaction_type,
        "description": Transaction.description,
        "account": Transaction.account_id,
    }

    sort_column = sort_column_map.get(sort_by, Transaction.date)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    transactions = query.offset(skip).limit(limit).all()
    return transactions


@router.get("/merchants", response_model=List[MerchantGroup])
def get_merchant_groups(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category_id: Optional[str] = None,
    account_id: Optional[str] = None,
    merchant: Optional[str] = None,
    sort_by: Optional[str] = "total_spend",
    sort_order: Optional[str] = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate transactions by normalized merchant name. Honors filters."""
    q = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    if category_id and category_id.strip():
        try:
            q = q.filter(Transaction.category_id == int(category_id))
        except ValueError:
            pass
    if account_id and account_id.strip():
        try:
            q = q.filter(Transaction.account_id == int(account_id))
        except ValueError:
            pass
    if merchant and merchant.strip():
        q = q.filter(Transaction.merchant.ilike(f"%{merchant.strip()}%"))

    rows = q.all()
    if not rows:
        return []

    # Aggregate in Python — group counts are small (hundreds, not millions) and
    # keeps category_ids/account_ids collection cross-dialect simple.
    groups: dict[str, dict] = {}
    for t in rows:
        key = (t.merchant or "").strip()
        display = key or "Unknown"
        norm = display.lower()
        g = groups.get(norm)
        if g is None:
            g = {
                "merchant": display,
                "count": 0,
                "total_debit": 0.0,
                "total_credit": 0.0,
                "first_date": t.date,
                "last_date": t.date,
                "category_ids": set(),
                "account_ids": set(),
            }
            groups[norm] = g
        g["count"] += 1
        amt = float(t.amount or 0.0)
        if t.transaction_type == TransactionType.CREDIT:
            g["total_credit"] += amt
        else:
            g["total_debit"] += amt
        if t.date < g["first_date"]:
            g["first_date"] = t.date
        if t.date > g["last_date"]:
            g["last_date"] = t.date
        if t.category_id is not None:
            g["category_ids"].add(t.category_id)
        if t.account_id is not None:
            g["account_ids"].add(t.account_id)

    items = []
    for g in groups.values():
        items.append(MerchantGroup(
            merchant=g["merchant"],
            count=g["count"],
            total_debit=round(g["total_debit"], 2),
            total_credit=round(g["total_credit"], 2),
            first_date=g["first_date"],
            last_date=g["last_date"],
            category_ids=sorted(g["category_ids"]),
            account_ids=sorted(g["account_ids"]),
        ))

    reverse = (sort_order or "desc").lower() != "asc"
    sort_key_map = {
        "merchant": lambda x: x.merchant.lower(),
        "count": lambda x: x.count,
        "total_spend": lambda x: x.total_debit,
        "total_income": lambda x: x.total_credit,
        "last_date": lambda x: x.last_date,
        "first_date": lambda x: x.first_date,
    }
    items.sort(key=sort_key_map.get(sort_by, sort_key_map["total_spend"]), reverse=reverse)
    return items


@router.get("/categories", response_model=List[CategoryGroup])
def get_category_groups(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category_id: Optional[str] = None,
    account_id: Optional[str] = None,
    merchant: Optional[str] = None,
    sort_by: Optional[str] = "total_spend",
    sort_order: Optional[str] = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate transactions by category. Honors filters; mirrors /merchants."""
    q = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    if category_id and category_id.strip():
        try:
            q = q.filter(Transaction.category_id == int(category_id))
        except ValueError:
            pass
    if account_id and account_id.strip():
        try:
            q = q.filter(Transaction.account_id == int(account_id))
        except ValueError:
            pass
    if merchant and merchant.strip():
        q = q.filter(Transaction.merchant.ilike(f"%{merchant.strip()}%"))

    rows = q.all()
    if not rows:
        return []

    # Pre-fetch category names for the user so the response is self-describing.
    cats = (
        db.query(Category)
        .filter(Category.user_id == current_user.id)
        .all()
    )
    cat_name_by_id = {c.id: c.name for c in cats}

    groups: dict = {}
    # Use -1 as the bucket key for uncategorized so it survives dict lookup.
    UNCATEGORIZED = -1
    for t in rows:
        key = t.category_id if t.category_id is not None else UNCATEGORIZED
        g = groups.get(key)
        if g is None:
            g = {
                "category_id": t.category_id,
                "category_name": cat_name_by_id.get(t.category_id, "Uncategorized") if t.category_id else "Uncategorized",
                "count": 0,
                "total_debit": 0.0,
                "total_credit": 0.0,
                "first_date": t.date,
                "last_date": t.date,
                "merchant_totals": {},  # merchant -> debit total, for top_merchants ranking
                "account_ids": set(),
            }
            groups[key] = g
        g["count"] += 1
        amt = float(t.amount or 0.0)
        if t.transaction_type == TransactionType.CREDIT:
            g["total_credit"] += amt
        else:
            g["total_debit"] += amt
        if t.date < g["first_date"]:
            g["first_date"] = t.date
        if t.date > g["last_date"]:
            g["last_date"] = t.date
        m = (t.merchant or "").strip() or "Unknown"
        # Rank merchants within a category by debit spend (or count if no debits)
        g["merchant_totals"][m] = g["merchant_totals"].get(m, 0.0) + (amt if t.transaction_type != TransactionType.CREDIT else 0.0)
        if t.account_id is not None:
            g["account_ids"].add(t.account_id)

    items: List[CategoryGroup] = []
    for g in groups.values():
        top = sorted(g["merchant_totals"].items(), key=lambda kv: kv[1], reverse=True)
        # Fall back to first 5 merchants by appearance order if all debits are zero.
        top_merchants = [m for m, _ in top[:5]] if any(v > 0 for _, v in top) else list(g["merchant_totals"].keys())[:5]
        items.append(CategoryGroup(
            category_id=g["category_id"],
            category_name=g["category_name"],
            count=g["count"],
            total_debit=round(g["total_debit"], 2),
            total_credit=round(g["total_credit"], 2),
            first_date=g["first_date"],
            last_date=g["last_date"],
            top_merchants=top_merchants,
            account_ids=sorted(g["account_ids"]),
        ))

    reverse = (sort_order or "desc").lower() != "asc"
    sort_key_map = {
        "category": lambda x: x.category_name.lower(),
        "count": lambda x: x.count,
        "total_spend": lambda x: x.total_debit,
        "total_income": lambda x: x.total_credit,
        "last_date": lambda x: x.last_date,
        "first_date": lambda x: x.first_date,
    }
    items.sort(key=sort_key_map.get(sort_by, sort_key_map["total_spend"]), reverse=reverse)
    return items


@router.post("/bulk-update")
def bulk_update_transactions(
    payload: BulkUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.ids:
        return {"updated": 0}
    if payload.category_id is None and payload.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide category_id and/or account_id",
        )

    if payload.category_id is not None:
        cat = (
            db.query(Category)
            .filter(Category.id == payload.category_id, Category.user_id == current_user.id)
            .first()
        )
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

    if payload.account_id is not None:
        acc = (
            db.query(Account)
            .filter(Account.id == payload.account_id, Account.user_id == current_user.id)
            .first()
        )
        if not acc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found",
            )

    update_data = {}
    if payload.category_id is not None:
        update_data["category_id"] = payload.category_id
        update_data["is_manually_categorized"] = True
    if payload.account_id is not None:
        update_data["account_id"] = payload.account_id

    affected = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.id.in_(payload.ids),
        )
        .update(update_data, synchronize_session=False)
    )
    db.commit()
    return {"updated": int(affected)}


@router.post("/bulk-update-by-merchant")
def bulk_update_by_merchant(
    payload: BulkUpdateByMerchantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    merchant = (payload.merchant or "").strip()
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="merchant is required",
        )
    if payload.category_id is None and payload.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide category_id and/or account_id",
        )

    if payload.category_id is not None:
        cat = (
            db.query(Category)
            .filter(Category.id == payload.category_id, Category.user_id == current_user.id)
            .first()
        )
        if not cat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if payload.account_id is not None:
        acc = (
            db.query(Account)
            .filter(Account.id == payload.account_id, Account.user_id == current_user.id)
            .first()
        )
        if not acc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    q = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        func.lower(func.trim(Transaction.merchant)) == merchant.lower(),
    )
    if payload.start_date:
        q = q.filter(Transaction.date >= payload.start_date)
    if payload.end_date:
        q = q.filter(Transaction.date <= payload.end_date)
    if payload.filter_account_id is not None:
        q = q.filter(Transaction.account_id == payload.filter_account_id)

    update_data = {}
    if payload.category_id is not None:
        update_data["category_id"] = payload.category_id
        update_data["is_manually_categorized"] = True
    if payload.account_id is not None:
        update_data["account_id"] = payload.account_id

    affected = q.update(update_data, synchronize_session=False)
    db.commit()
    return {"updated": int(affected)}


@router.post("/", response_model=TransactionSchema)
def create_transaction(
    transaction_in: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    categorization_service = CategorizationService(db)

    if not transaction_in.category_id:
        category_id = categorization_service.categorize_transaction(
            current_user.id,
            transaction_in.merchant,
            transaction_in.description or ""
        )
    else:
        category_id = transaction_in.category_id

    payload = transaction_in.model_dump()
    payload.pop("category_id", None)

    transaction = Transaction(
        user_id=current_user.id,
        category_id=category_id,
        **payload,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.put("/{transaction_id}", response_model=TransactionSchema)
def update_transaction(
    transaction_id: int,
    transaction_in: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    update_data = transaction_in.model_dump(exclude_unset=True)

    if "category_id" in update_data:
        transaction.is_manually_categorized = True

    for field, value in update_data.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/clear")
def clear_my_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all transactions for the current user. Categories are kept."""
    deleted_trans = db.query(Transaction).filter(Transaction.user_id == current_user.id).delete()
    db.commit()
    return {"message": f"Deleted {deleted_trans} transaction(s).", "deleted_transactions": deleted_trans}


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    db.delete(transaction)
    db.commit()
    return {"message": "Transaction deleted successfully"}


@router.post("/upload")
async def upload_bank_statement(
    file: UploadFile = File(...),
    account_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".csv", ".pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV and PDF files are supported",
        )

    content = await file.read()
    if len(content) > getattr(settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 10 MB.",
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, f"{current_user.id}_{file.filename}")

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # Resolve account: explicit > inferred > default
    target_account: Optional[Account] = None
    if account_id is not None:
        target_account = (
            db.query(Account)
            .filter(Account.id == account_id, Account.user_id == current_user.id)
            .first()
        )
        if not target_account:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found",
            )

    try:
        if file_ext == ".csv" and is_account_activity_csv(file_path):
            transactions_data = parse_account_activity_csv(file_path)
            use_csv_categories = True
        elif file_ext == ".csv":
            parser = PNCParser()
            transactions_data = parser.parse_csv(file_path)
            use_csv_categories = False
        else:
            parser = PNCParser()
            transactions_data = parser.parse_pdf(file_path)
            use_csv_categories = False
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse file: {str(e)}",
        )

    if not transactions_data:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No transactions found in this file. The PDF format may not be supported. Try CSV export from your bank, or ensure the PDF is a transaction list.",
        )

    if target_account is None:
        inferred_name, inferred_type = _infer_account_for_upload(file.filename, file_ext, file_path)
        target_account = get_or_create_account(
            db, current_user.id, inferred_name, account_type=inferred_type, institution="PNC"
        )
        # Make sure a default exists in case this is the user's first account.
        if not db.query(Account).filter(
            Account.user_id == current_user.id, Account.is_default == True
        ).first():
            target_account.is_default = True

    # Build set of existing (date, merchant, amount) to avoid duplicates
    def _to_date(d):
        return d.date() if hasattr(d, "date") and callable(d.date) else d

    dates = [_to_date(t["date"]) for t in transactions_data if t.get("date")]
    if dates:
        min_date = min(dates)
        max_date = max(dates)
        existing_keys = _existing_transaction_keys(db, current_user.id, min_date, max_date)
    else:
        existing_keys = set()
    # Track keys we add in this batch so we don't insert same row twice from the file
    seen_in_batch = set(existing_keys)

    categorization_service = CategorizationService(db)
    created_count = 0
    skipped_count = 0

    for trans_data in transactions_data:
        key = _transaction_duplicate_key(trans_data)
        if key in seen_in_batch:
            skipped_count += 1
            continue
        seen_in_batch.add(key)

        if use_csv_categories and "category_name" in trans_data:
            category_name = trans_data.get("category_name")
            if category_name and str(category_name).strip():
                category_id_resolved = _get_or_create_category(db, current_user.id, str(category_name).strip())
            else:
                category_id_resolved = None
            if category_id_resolved is None:
                category_id_resolved = _get_or_create_category(db, current_user.id, "Uncategorized")
            payload = {k: v for k, v in trans_data.items() if k != "category_name"}
        else:
            category_id_resolved = categorization_service.categorize_transaction(
                current_user.id,
                trans_data["merchant"],
                trans_data.get("description", ""),
            )
            if category_id_resolved is None:
                category_id_resolved = _get_or_create_category(db, current_user.id, "Uncategorized")
            payload = trans_data

        transaction = Transaction(
            user_id=current_user.id,
            category_id=category_id_resolved,
            account_id=target_account.id,
            source_file=file.filename,
            **payload
        )

        db.add(transaction)
        created_count += 1

    db.commit()

    os.remove(file_path)

    message = f"Successfully imported {created_count} transactions"
    if skipped_count:
        message += f". Skipped {skipped_count} duplicate(s)."
    message += f" Account: {target_account.name}."
    return {
        "message": message,
        "count": created_count,
        "skipped": skipped_count,
        "account_id": target_account.id,
        "account_name": target_account.name,
    }


@router.post("/export")
def export_transactions(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import csv
    from io import StringIO

    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.order_by(Transaction.date.desc()).all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(['Date', 'Merchant', 'Description', 'Amount', 'Type', 'Category', 'Account'])

    for trans in transactions:
        writer.writerow([
            trans.date.strftime('%Y-%m-%d'),
            trans.merchant,
            trans.description or '',
            trans.amount,
            trans.transaction_type.value,
            trans.category.name if trans.category else 'Uncategorized',
            trans.account.name if trans.account else '',
        ])

    return {
        "csv_data": output.getvalue()
    }
