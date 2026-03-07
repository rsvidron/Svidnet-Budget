from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import User, Category, Transaction
from app.schemas.category import Category as CategorySchema, CategoryCreate, CategoryUpdate
from app.api.deps import get_current_user
from app.services.categorization_service import CategorizationService

router = APIRouter()


@router.get("/", response_model=List[CategorySchema])
def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    categories = db.query(Category).filter(Category.user_id == current_user.id).all()
    return categories


@router.post("/", response_model=CategorySchema)
def create_category(
    category_in: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = Category(
        user_id=current_user.id,
        **category_in.model_dump()
    )

    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategorySchema)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    update_data = category_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    uncategorized = db.query(Category).filter(
        Category.user_id == current_user.id,
        Category.name == "Uncategorized"
    ).first()

    if uncategorized:
        db.query(Transaction).filter(
            Transaction.category_id == category_id
        ).update({"category_id": uncategorized.id})

    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}


@router.post("/{category_id}/merge/{target_category_id}")
def merge_categories(
    category_id: int,
    target_category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    source_category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    target_category = db.query(Category).filter(
        Category.id == target_category_id,
        Category.user_id == current_user.id
    ).first()

    if not source_category or not target_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    db.query(Transaction).filter(
        Transaction.category_id == category_id
    ).update({"category_id": target_category_id})

    db.delete(source_category)
    db.commit()

    return {"message": f"Merged '{source_category.name}' into '{target_category.name}'"}


@router.post("/rules")
def add_categorization_rule(
    category_id: int,
    keyword: str,
    priority: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    categorization_service = CategorizationService(db)
    rule = categorization_service.add_rule(current_user.id, category_id, keyword, priority)

    return {"message": "Rule added successfully", "rule_id": rule.id}


@router.post("/recategorize")
def recategorize_all_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    categorization_service = CategorizationService(db)
    categorization_service.recategorize_all(current_user.id)

    return {"message": "All transactions recategorized successfully"}
