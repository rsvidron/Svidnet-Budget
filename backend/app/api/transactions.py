from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import os
from app.core.database import get_db
from app.core.config import settings
from app.models import User, Transaction, Category
from app.schemas.transaction import Transaction as TransactionSchema, TransactionCreate, TransactionUpdate, TransactionFilter
from app.api.deps import get_current_user
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


@router.get("/", response_model=List[TransactionSchema])
def get_transactions(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category_id: Optional[str] = None,
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
    }

    sort_column = sort_column_map.get(sort_by, Transaction.date)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    transactions = query.offset(skip).limit(limit).all()
    return transactions


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

    transaction = Transaction(
        user_id=current_user.id,
        category_id=category_id,
        **transaction_in.model_dump()
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
            category_id = _get_or_create_category(db, current_user.id, category_name)
            if category_id is None:
                category_id = categorization_service.categorize_transaction(
                    current_user.id,
                    trans_data["merchant"],
                    trans_data.get("description", ""),
                )
            payload = {k: v for k, v in trans_data.items() if k != "category_name"}
        else:
            category_id = categorization_service.categorize_transaction(
                current_user.id,
                trans_data["merchant"],
                trans_data.get("description", ""),
            )
            payload = trans_data

        transaction = Transaction(
            user_id=current_user.id,
            category_id=category_id,
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
    return {
        "message": message,
        "count": created_count,
        "skipped": skipped_count,
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

    writer.writerow(['Date', 'Merchant', 'Description', 'Amount', 'Type', 'Category'])

    for trans in transactions:
        writer.writerow([
            trans.date.strftime('%Y-%m-%d'),
            trans.merchant,
            trans.description or '',
            trans.amount,
            trans.transaction_type.value,
            trans.category.name if trans.category else 'Uncategorized'
        ])

    return {
        "csv_data": output.getvalue()
    }
