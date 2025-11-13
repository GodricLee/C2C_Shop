"""Search utilities backed by SQL LIKE queries with synonym expansion."""
from __future__ import annotations

from typing import List

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.product import Product, ProductStatus
from app.models.synonym import SynonymEntry


def _normalize(term: str) -> str:
    return term.strip().lower()


def expand_terms(db: Session, query: str) -> List[str]:
    """Expand search query with configured synonyms."""

    base_terms = [_normalize(part) for part in query.split() if part.strip()]
    expanded = set(base_terms)
    if not base_terms:
        return []

    stmt = select(SynonymEntry).where(SynonymEntry.word.in_(base_terms))
    for entry in db.execute(stmt).scalars():
        for synonym in entry.synonyms:
            expanded.add(_normalize(synonym))
    return list(expanded)


def search_products(db: Session, query: str, limit: int = 20, offset: int = 0) -> List[Product]:
    """Search published products using expanded term list."""

    terms = expand_terms(db, query)
    base_query = select(Product).where(Product.status == ProductStatus.PUBLISHED)

    if terms:
        like_clauses = []
        for term in terms:
            pattern = f"%{term}%"
            like_clauses.append(Product.title.ilike(pattern))
            like_clauses.append(Product.description.ilike(pattern))
        if like_clauses:
            base_query = base_query.where(or_(*like_clauses))

    stmt = base_query.order_by(Product.created_at.desc()).offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()
