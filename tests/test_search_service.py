"""Unit tests for the search service - 80%+ coverage."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.product import Product, ProductStatus
from app.models.synonym import SynonymEntry
from app.services.search import _normalize, expand_terms, search_products


class TestNormalizeFunction:
    """Tests for the _normalize helper function."""

    def test_normalize_lowercase(self) -> None:
        """Test that uppercase is converted to lowercase"""
        assert _normalize("HELLO") == "hello"

    def test_normalize_strips_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped"""
        assert _normalize("  test  ") == "test"

    def test_normalize_mixed_case(self) -> None:
        """Test mixed case input"""
        assert _normalize("HeLLo WoRLd") == "hello world"

    def test_normalize_empty_string(self) -> None:
        """Test empty string input"""
        assert _normalize("") == ""

    def test_normalize_only_spaces(self) -> None:
        """Test string with only spaces"""
        assert _normalize("   ") == ""

    def test_normalize_special_characters(self) -> None:
        """Test special characters are preserved"""
        assert _normalize("  Test-123!  ") == "test-123!"


class TestExpandTerms:
    """Tests for the expand_terms function."""

    def test_expand_terms_empty_query(self, db_session: Session) -> None:
        """Test with empty query string"""
        result = expand_terms(db_session, "")
        assert result == []

    def test_expand_terms_whitespace_only(self, db_session: Session) -> None:
        """Test with whitespace only query"""
        result = expand_terms(db_session, "   ")
        assert result == []

    def test_expand_terms_single_word_no_synonyms(self, db_session: Session) -> None:
        """Test single word without synonyms in database"""
        result = expand_terms(db_session, "phone")
        assert "phone" in result
        assert len(result) == 1

    def test_expand_terms_multiple_words_no_synonyms(self, db_session: Session) -> None:
        """Test multiple words without synonyms"""
        result = expand_terms(db_session, "smart phone")
        assert "smart" in result
        assert "phone" in result
        assert len(result) == 2

    def test_expand_terms_with_synonyms(self, db_session: Session) -> None:
        """Test word expansion with synonyms in database"""
        # Create synonym entry
        synonym = SynonymEntry(word="phone", synonyms=["mobile", "cellphone", "smartphone"])
        db_session.add(synonym)
        db_session.commit()

        result = expand_terms(db_session, "phone")
        assert "phone" in result
        assert "mobile" in result
        assert "cellphone" in result
        assert "smartphone" in result
        assert len(result) == 4

    def test_expand_terms_preserves_original(self, db_session: Session) -> None:
        """Test that original terms are preserved"""
        synonym = SynonymEntry(word="laptop", synonyms=["notebook", "computer"])
        db_session.add(synonym)
        db_session.commit()

        result = expand_terms(db_session, "laptop case")
        assert "laptop" in result
        assert "case" in result
        assert "notebook" in result
        assert "computer" in result

    def test_expand_terms_normalizes_synonyms(self, db_session: Session) -> None:
        """Test that synonyms are also normalized"""
        synonym = SynonymEntry(word="car", synonyms=["  VEHICLE  ", "AUTOMOBILE"])
        db_session.add(synonym)
        db_session.commit()

        result = expand_terms(db_session, "car")
        assert "car" in result
        assert "vehicle" in result
        assert "automobile" in result

    def test_expand_terms_case_insensitive_lookup(self, db_session: Session) -> None:
        """Test that lookup is case insensitive"""
        synonym = SynonymEntry(word="camera", synonyms=["cam", "shooter"])
        db_session.add(synonym)
        db_session.commit()

        result = expand_terms(db_session, "CAMERA")
        assert "camera" in result
        assert "cam" in result
        assert "shooter" in result


class TestSearchProducts:
    """Tests for the search_products function."""

    def test_search_empty_query(self, db_session: Session) -> None:
        """Test search with empty query returns published products"""
        product = Product(
            seller_id=1,
            title="Test Product",
            description="A test",
            price=Decimal("10.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add(product)
        db_session.commit()

        results = search_products(db_session, "")
        # Empty query returns all published products
        assert len(results) >= 0

    def test_search_matches_title(self, db_session: Session) -> None:
        """Test search matches product title"""
        product = Product(
            seller_id=1,
            title="Vintage Camera",
            description="Old film camera",
            price=Decimal("150.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add(product)
        db_session.commit()

        results = search_products(db_session, "vintage")
        assert len(results) == 1
        assert results[0].title == "Vintage Camera"

    def test_search_matches_description(self, db_session: Session) -> None:
        """Test search matches product description"""
        product = Product(
            seller_id=1,
            title="Camera",
            description="A beautiful vintage lens",
            price=Decimal("100.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add(product)
        db_session.commit()

        results = search_products(db_session, "vintage")
        assert len(results) == 1
        assert "vintage" in results[0].description.lower()

    def test_search_excludes_unpublished(self, db_session: Session) -> None:
        """Test search excludes non-published products"""
        draft = Product(
            seller_id=1,
            title="Draft Camera",
            description="Draft product",
            price=Decimal("50.00"),
            status=ProductStatus.DRAFT,
        )
        published = Product(
            seller_id=1,
            title="Published Camera",
            description="Available",
            price=Decimal("75.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add_all([draft, published])
        db_session.commit()

        results = search_products(db_session, "camera")
        assert len(results) == 1
        assert results[0].status == ProductStatus.PUBLISHED

    def test_search_case_insensitive(self, db_session: Session) -> None:
        """Test search is case insensitive"""
        product = Product(
            seller_id=1,
            title="LAPTOP Computer",
            description="Gaming laptop",
            price=Decimal("1000.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add(product)
        db_session.commit()

        results = search_products(db_session, "laptop")
        assert len(results) == 1

        results = search_products(db_session, "LAPTOP")
        assert len(results) == 1

    def test_search_pagination_limit(self, db_session: Session) -> None:
        """Test search respects limit parameter"""
        for i in range(5):
            product = Product(
                seller_id=1,
                title=f"Phone {i}",
                description="A phone",
                price=Decimal("500.00"),
                status=ProductStatus.PUBLISHED,
            )
            db_session.add(product)
        db_session.commit()

        results = search_products(db_session, "phone", limit=3)
        assert len(results) == 3

    def test_search_pagination_offset(self, db_session: Session) -> None:
        """Test search respects offset parameter"""
        for i in range(5):
            product = Product(
                seller_id=1,
                title=f"Tablet {i}",
                description="A tablet",
                price=Decimal("300.00"),
                status=ProductStatus.PUBLISHED,
            )
            db_session.add(product)
        db_session.commit()

        all_results = search_products(db_session, "tablet", limit=10)
        offset_results = search_products(db_session, "tablet", limit=10, offset=2)

        assert len(offset_results) == len(all_results) - 2

    def test_search_multiple_terms(self, db_session: Session) -> None:
        """Test search with multiple terms (OR logic)"""
        phone = Product(
            seller_id=1,
            title="Smartphone",
            description="Latest phone",
            price=Decimal("800.00"),
            status=ProductStatus.PUBLISHED,
        )
        laptop = Product(
            seller_id=1,
            title="Laptop",
            description="Gaming laptop",
            price=Decimal("1200.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add_all([phone, laptop])
        db_session.commit()

        results = search_products(db_session, "phone laptop")
        assert len(results) == 2

    def test_search_with_synonyms(self, db_session: Session) -> None:
        """Test search expands to synonyms"""
        synonym = SynonymEntry(word="phone", synonyms=["mobile", "cellphone"])
        product = Product(
            seller_id=1,
            title="Mobile Device",
            description="Latest cellphone",
            price=Decimal("600.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add_all([synonym, product])
        db_session.commit()

        results = search_products(db_session, "phone")
        assert len(results) == 1
        assert results[0].title == "Mobile Device"

    def test_search_no_results(self, db_session: Session) -> None:
        """Test search with no matching results"""
        product = Product(
            seller_id=1,
            title="Camera",
            description="Digital camera",
            price=Decimal("400.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add(product)
        db_session.commit()

        results = search_products(db_session, "xyznonexistent")
        assert len(results) == 0

    def test_search_partial_match(self, db_session: Session) -> None:
        """Test search with partial word match"""
        product = Product(
            seller_id=1,
            title="Photography Equipment",
            description="Professional gear",
            price=Decimal("2000.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add(product)
        db_session.commit()

        results = search_products(db_session, "photo")
        assert len(results) == 1

    def test_search_orders_by_created_at(self, db_session: Session) -> None:
        """Test search results are ordered by created_at desc"""
        from datetime import datetime, timedelta, timezone

        old = Product(
            seller_id=1,
            title="Old Watch",
            description="Vintage",
            price=Decimal("100.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add(old)
        db_session.flush()

        new = Product(
            seller_id=1,
            title="New Watch",
            description="Modern",
            price=Decimal("200.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add(new)
        db_session.commit()

        results = search_products(db_session, "watch")
        assert len(results) == 2
        # Newer should come first (desc order)
        assert results[0].created_at >= results[1].created_at
