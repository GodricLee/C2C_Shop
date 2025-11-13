"""Search synonym models."""
from __future__ import annotations

from sqlalchemy import Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SynonymEntry(Base):
    """Synonym set used to expand product search queries."""

    __tablename__ = "synonym_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    synonyms: Mapped[list[str]] = mapped_column(JSON, default=list)
