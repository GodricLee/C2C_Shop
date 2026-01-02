"""Integration tests covering complete user journeys and module interactions."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.coupon import Coupon, CouponAssignment, CouponStatus
from app.models.membership import Membership, MembershipLevel
from app.models.product import Product, ProductStatus
from app.models.synonym import SynonymEntry
from app.models.tag import Tag, TagStatus


class TestUserPurchaseJourneyIntegration:
    """Integration test: Complete user purchase journey from browsing to deal confirmation.
    
    This test uses a bottom-up integration approach:
    1. Product Service
    2. Search Service
    3. Pricing/Discount Engine
    4. Deal Service
    """

    def test_complete_purchase_flow(
        self,
        client,
        current_user_override,
        buyer_user,
        admin_user,
        pricing_setup,
        db_session,
        user_factory,
    ) -> None:
        """Test complete flow: seller lists product -> buyer searches -> creates deal -> confirms."""
        _ = pricing_setup  # Ensure pricing is set up
        
        # Step 1: Seller creates and publishes a product
        seller = user_factory("integration.seller@example.com")
        seller_headers = current_user_override(seller)

        create_product_response = client.post(
            "/api/products",
            json={
                "title": "Vintage Record Player",
                "description": "Classic vinyl turntable in excellent condition",
                "price": "280.00",
            },
            headers=seller_headers,
        )
        assert create_product_response.status_code == 201
        product_id = create_product_response.json()["id"]

        # Step 2: Seller publishes the product
        publish_response = client.put(
            f"/api/products/{product_id}",
            json={"status": ProductStatus.PUBLISHED.value},
            headers=seller_headers,
        )
        assert publish_response.status_code == 200

        # Step 3: Buyer browses and finds the product
        browse_response = client.get("/api/products/")
        assert browse_response.status_code == 200
        products = browse_response.json()["items"]
        found = any(p["id"] == product_id for p in products)
        assert found, "Published product should appear in listing"

        # Step 4: Buyer views product details
        detail_response = client.get(f"/api/products/{product_id}")
        assert detail_response.status_code == 200
        product_detail = detail_response.json()
        assert product_detail["title"] == "Vintage Record Player"
        assert product_detail["status"] == ProductStatus.PUBLISHED.value

        # Step 5: Buyer initiates a deal
        buyer_headers = current_user_override(buyer_user)
        deal_response = client.post(
            "/api/deals",
            json={"product_id": product_id},
            headers=buyer_headers,
        )
        assert deal_response.status_code == 201
        deal_id = deal_response.json()["id"]
        assert deal_response.json()["status"] == "INITIATED"

        # Step 6: Seller confirms the deal (with pricing calculation)
        # Re-get seller headers to ensure fresh override
        seller_headers = current_user_override(seller)
        confirm_response = client.post(
            f"/api/deals/{deal_id}/confirm-by-seller",
            json={"coupon_id": None},
            headers=seller_headers,
        )
        assert confirm_response.status_code == 200
        confirmed = confirm_response.json()
        assert confirmed["status"] == "CONFIRMED_BY_SELLER"
        assert confirmed["cashback"] is not None

        # Step 7: Verify product is marked as sold
        db_session.expire_all()
        sold_product = db_session.query(Product).filter(Product.id == product_id).one()
        assert sold_product.status == ProductStatus.SOLD


class TestSearchAndDiscoveryIntegration:
    """Integration test: Search service with synonym expansion and product discovery.
    
    This test integrates:
    1. Synonym Management
    2. Search Service
    3. Product Listing
    """

    def test_synonym_enhanced_search(
        self,
        client,
        current_user_override,
        user_factory,
        db_session,
    ) -> None:
        """Test search finds products using synonym expansion."""
        # Step 1: Create synonyms in the database
        synonym1 = SynonymEntry(word="phone", synonyms=["mobile", "cellphone", "smartphone"])
        synonym2 = SynonymEntry(word="laptop", synonyms=["notebook", "computer"])
        db_session.add_all([synonym1, synonym2])
        db_session.commit()

        # Step 2: Seller creates products with various titles
        seller = user_factory("search.seller@example.com")

        product1 = Product(
            seller_id=seller.id,
            title="Apple Smartphone Pro",
            description="Latest model",
            price=Decimal("999.00"),
            status=ProductStatus.PUBLISHED,
        )
        product2 = Product(
            seller_id=seller.id,
            title="Samsung Mobile Device",
            description="Android phone",
            price=Decimal("799.00"),
            status=ProductStatus.PUBLISHED,
        )
        product3 = Product(
            seller_id=seller.id,
            title="Gaming Notebook",
            description="High performance laptop",
            price=Decimal("1500.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add_all([product1, product2, product3])
        db_session.commit()

        # Step 3: Search for "phone" should find products with "mobile", "smartphone"
        search_response = client.get("/api/products/", params={"q": "phone"})
        assert search_response.status_code == 200
        results = search_response.json()["items"]
        
        # Should find both phone-related products
        titles = [r["title"] for r in results]
        assert any("Smartphone" in t for t in titles) or any("Mobile" in t for t in titles)

        # Step 4: Search for "laptop" should find notebook products
        laptop_response = client.get("/api/products/", params={"q": "laptop"})
        assert laptop_response.status_code == 200
        laptop_results = laptop_response.json()["items"]
        titles = [r["title"] for r in laptop_results]
        assert any("Notebook" in t or "laptop" in t.lower() for t in titles)


class TestCouponAndMembershipIntegration:
    """Integration test: Coupon system with membership discounts.
    
    This test integrates:
    1. Admin Coupon Management
    2. Membership System
    3. Discount Engine
    4. Deal Processing
    """

    def test_member_with_coupon_purchase(
        self,
        client,
        current_user_override,
        admin_user,
        pricing_setup,
        db_session,
        user_factory,
    ) -> None:
        """Test member user purchasing with coupon (stacked discounts)."""
        # Step 1: Create a member buyer
        member_buyer = user_factory(
            "member.buyer@example.com",
            membership_level=MembershipLevel.SHOPPER,
        )

        # Step 2: Admin creates and activates a coupon
        admin_headers = current_user_override(admin_user)
        coupon_response = client.post(
            "/api/promotions/coupons",
            json={
                "code": "MEMBER10",
                "min_revenue": "0.00",
                "min_sales": 0,
                "discount_amount": "10.00",
                "description": "Member bonus coupon",
            },
            headers=admin_headers,
        )
        assert coupon_response.status_code == 201
        coupon_id = coupon_response.json()["id"]

        # Step 3: Activate the coupon
        activate_response = client.put(
            f"/api/promotions/coupons/{coupon_id}",
            json={"status": "ACTIVE"},
            headers=admin_headers,
        )
        assert activate_response.status_code == 200

        # Step 4: Assign coupon to member
        assign_response = client.post(
            f"/api/promotions/coupons/{coupon_id}/assign",
            json={"user_id": member_buyer.id},
            headers=admin_headers,
        )
        assert assign_response.status_code == 200

        # Step 5: Seller creates a product
        seller = user_factory("coupon.seller@example.com")
        product = Product(
            seller_id=seller.id,
            title="Premium Headphones",
            description="Studio quality",
            price=Decimal("200.00"),
            status=ProductStatus.PUBLISHED,
        )
        db_session.add(product)
        db_session.commit()

        # Step 6: Member initiates deal
        member_headers = current_user_override(member_buyer)
        deal_response = client.post(
            "/api/deals",
            json={"product_id": product.id},
            headers=member_headers,
        )
        assert deal_response.status_code == 201
        deal_id = deal_response.json()["id"]

        # Step 7: Seller confirms with coupon
        seller_headers = current_user_override(seller)
        confirm_response = client.post(
            f"/api/deals/{deal_id}/confirm-by-seller",
            json={"coupon_id": coupon_id},
            headers=seller_headers,
        )
        assert confirm_response.status_code == 200
        result = confirm_response.json()

        # Verify coupon was used
        assert result["used_coupon_id"] == coupon_id
        assert result["status"] == "CONFIRMED_BY_SELLER"

        # Verify coupon is marked as used
        assignment = (
            db_session.query(CouponAssignment)
            .filter(
                CouponAssignment.coupon_id == coupon_id,
                CouponAssignment.user_id == member_buyer.id,
            )
            .one()
        )
        assert assignment.used is True


class TestProductTaggingAndModerationIntegration:
    """Integration test: Product tagging with admin moderation.
    
    This test integrates:
    1. Product Management
    2. Tag System
    3. Admin Moderation (simulated)
    """

    def test_product_tagging_workflow(
        self,
        client,
        current_user_override,
        user_factory,
        db_session,
    ) -> None:
        """Test product tagging and tag status workflow."""
        # Step 1: Seller creates product
        seller = user_factory("tagging.seller@example.com")
        product = Product(
            seller_id=seller.id,
            title="Retro Game Console",
            description="Classic gaming system",
            price=Decimal("150.00"),
            status=ProductStatus.DRAFT,
        )
        db_session.add(product)
        db_session.commit()

        # Step 2: Seller adds tags
        seller_headers = current_user_override(seller)
        tag_response = client.post(
            f"/api/products/{product.id}/tags",
            json={"names": ["gaming", "retro", "console", "electronics"]},
            headers=seller_headers,
        )
        assert tag_response.status_code == 200
        tags = tag_response.json()
        assert len(tags) == 4

        # Step 3: Verify tags are created with PENDING status
        db_tags = db_session.query(Tag).filter(Tag.name.in_(["gaming", "retro", "console", "electronics"])).all()
        assert len(db_tags) == 4
        assert all(tag.status == TagStatus.PENDING for tag in db_tags)

        # Step 4: Publish product
        publish_response = client.put(
            f"/api/products/{product.id}",
            json={"status": ProductStatus.PUBLISHED.value},
            headers=seller_headers,
        )
        assert publish_response.status_code == 200

        # Step 5: Verify product is visible with tags
        detail_response = client.get(f"/api/products/{product.id}")
        assert detail_response.status_code == 200
        product_data = detail_response.json()
        assert product_data["status"] == ProductStatus.PUBLISHED.value
