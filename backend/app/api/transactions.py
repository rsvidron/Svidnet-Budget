from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime
import os
from app.core.database import get_db
from app.core.config import settings
from app.models import User, Transaction
from app.schemas.transaction import Transaction as TransactionSchema, TransactionCreate, TransactionUpdate, TransactionFilter
from app.api.deps import get_current_user
from app.parsers import PNCParser
from app.services.categorization_service import CategorizationService

router = APIRouter()


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

    parser = PNCParser()

    try:
        if file_ext == ".csv":
            transactions_data = parser.parse_csv(file_path)
        else:
            transactions_data = parser.parse_pdf(file_path)
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

    categorization_service = CategorizationService(db)
    created_count = 0

    for trans_data in transactions_data:
        category_id = categorization_service.categorize_transaction(
            current_user.id,
            trans_data["merchant"],
            trans_data.get("description", "")
        )

        transaction = Transaction(
            user_id=current_user.id,
            category_id=category_id,
            source_file=file.filename,
            **trans_data
        )

        db.add(transaction)
        created_count += 1

    db.commit()

    os.remove(file_path)

    return {
        "message": f"Successfully imported {created_count} transactions",
        "count": created_count
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
