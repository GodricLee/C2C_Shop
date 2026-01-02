"""Product CRUD endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.deps import get_current_user
from app.common.exceptions import AppError
from app.common.pagination import apply_pagination, pagination_params
from app.common.serialization import serialize_diff
from app.db import get_db
from app.models.audit_log import AuditLog
from app.models.product import Product, ProductStatus
from app.models.tag import Tag, TagStatus
from app.models.user import User
from app.schemas.product import ProductCreate, ProductListResponse, ProductOut, ProductUpdate
from app.schemas.tag import TagAssignRequest, TagOut
from app.services import search

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ProductOut)
def create_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProductOut:
    """Create a product listing for the authenticated seller."""

    product = Product(
        seller_id=current_user.id,
        title=payload.title,
        description=payload.description,
        price=payload.price,
        status=ProductStatus.DRAFT,
    )
    db.add(product)
    db.flush()

    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="product.create",
            entity="Product",
            entity_id=str(product.id),
            diff={"title": product.title, "price": str(product.price)},
        )
    )
    db.commit()
    db.refresh(product)
    return ProductOut.from_orm(product)


@router.get("/", response_model=ProductListResponse)
def list_products(
    q: Optional[str] = Query(None, description="Search query"),
    db: Session = Depends(get_db),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> ProductListResponse:
    """List products, optionally filtered via search."""

    page, page_size = pagination
    offset = (page - 1) * page_size
    if q:
        items = search.search_products(db, q, limit=page_size, offset=offset)
        total = len(items)
    else:
        base_stmt = select(Product).where(Product.status == ProductStatus.PUBLISHED)
        count_stmt = select(func.count()).select_from(Product).where(
            Product.status == ProductStatus.PUBLISHED
        )
        total = db.execute(count_stmt).scalar_one()
        stmt = apply_pagination(base_stmt.order_by(Product.created_at.desc()), page, page_size)
        items = db.execute(stmt).scalars().all()

    return ProductListResponse(
        items=[ProductOut.from_orm(item) for item in items],
        total=total,
    )


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductOut:
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise AppError(404, "Product not found")
    return ProductOut.from_orm(product)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProductOut:
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise AppError(404, "Product not found")
    if product.seller_id != current_user.id and not current_user.is_admin:
        raise AppError(403, "Not authorized to modify product")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="product.update",
            entity="Product",
            entity_id=str(product.id),
            diff=serialize_diff(update_data),
        )
    )
    db.commit()
    db.refresh(product)
    return ProductOut.from_orm(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise AppError(404, "Product not found")
    if product.seller_id != current_user.id and not current_user.is_admin:
        raise AppError(403, "Not authorized to delete product")

    product.status = ProductStatus.UNLISTED
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="product.delete",
            entity="Product",
            entity_id=str(product.id),
            diff={"status": ProductStatus.UNLISTED.value},
        )
    )
    db.commit()


@router.post("/{product_id}/tags", response_model=list[TagOut])
def assign_tags(
    product_id: int,
    payload: TagAssignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TagOut]:
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise AppError(404, "Product not found")
    if product.seller_id != current_user.id and not current_user.is_admin:
        raise AppError(403, "Not authorized to tag product")

    assigned = []
    for name in payload.names:
        tag = db.query(Tag).filter(Tag.name == name).first()
        if tag is None:
            tag = Tag(name=name, status=TagStatus.PENDING)
            db.add(tag)
            db.flush()
        if tag not in product.tags:
            product.tags.append(tag)
            assigned.append(tag)

    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="product.tag.assign",
            entity="Product",
            entity_id=str(product.id),
            diff={"tags": payload.names},
        )
    )
    db.commit()
    db.refresh(product)
    return [TagOut.from_orm(tag) for tag in product.tags]
