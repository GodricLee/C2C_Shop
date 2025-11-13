"""Populate the development database with a comprehensive demo dataset."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.config import get_settings
from app.db import session_scope
from app.models.admin_config import AdminConfig
from app.models.audit_log import AuditLog
from app.models.cashback import Cashback
from app.models.coupon import Coupon, CouponAssignment, CouponScope, CouponStatus
from app.models.deal import Deal, DealStatus
from app.models.membership import Membership, MembershipLevel
from app.models.parameter_set import ParameterSet, ParameterStatus, PricePolicy
from app.models.product import Product, ProductStatus
from app.models.synonym import SynonymEntry
from app.models.tag import Tag, TagStatus
from app.models.user import TwoFAMethod, TwoFAMethodType, User
from app.security.hashing import hash_password
from app.services.discount_engine import apply_discount

settings = get_settings()


def ensure_user(
    session,
    *,
    email: str,
    password: str,
    is_admin: bool = False,
    membership_level: MembershipLevel | None = None,
) -> User:
    user = session.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(password),
            is_admin=is_admin,
        )
        session.add(user)
        session.flush()
        session.add(
            TwoFAMethod(
                user_id=user.id,
                type=TwoFAMethodType.EMAIL,
                secret="demo-secret",
                enabled=True,
            )
        )
    else:
        user.is_admin = user.is_admin or is_admin

    if membership_level is not None:
        expires_at = datetime.now(tz=timezone.utc) + timedelta(days=365)
        membership = session.query(Membership).filter(Membership.user_id == user.id).first()
        if membership is None:
            membership = Membership(
                user_id=user.id,
                level=membership_level,
                expires_at=expires_at,
            )
            session.add(membership)
        else:
            membership.level = membership_level
            membership.expires_at = expires_at
    return user


def ensure_admin_config(session) -> tuple[AdminConfig, ParameterSet]:
    config = session.query(AdminConfig).first()
    if config is None:
        config = AdminConfig(commission_rate=Decimal("0.05"), cashback_default=Decimal("0.02"))
        session.add(config)
        session.flush()

    parameter = (
        session.query(ParameterSet)
        .filter(ParameterSet.admin_config_id == config.id, ParameterSet.version == 1)
        .first()
    )
    if parameter is None:
        parameter = ParameterSet(
            admin_config_id=config.id,
            version=1,
            status=ParameterStatus.PUBLISHED,
            effective_at=datetime.now(tz=timezone.utc),
            payload={"season": "spring", "note": "baseline policy"},
        )
        session.add(parameter)
        session.flush()
        session.add(
            PricePolicy(
                parameter_set_id=parameter.id,
                min_price=Decimal("50.00"),
                subsidy_cap=Decimal("30.00"),
            )
        )
        config.current_parameter_set_id = parameter.id
    else:
        if parameter.price_policy is None:
            session.add(
                PricePolicy(
                    parameter_set_id=parameter.id,
                    min_price=Decimal("50.00"),
                    subsidy_cap=Decimal("30.00"),
                )
            )
        parameter.status = ParameterStatus.PUBLISHED
        if parameter.effective_at is None:
            parameter.effective_at = datetime.now(tz=timezone.utc)
        config.current_parameter_set_id = parameter.id

    draft = (
        session.query(ParameterSet)
        .filter(ParameterSet.admin_config_id == config.id, ParameterSet.version == 2)
        .first()
    )
    if draft is None:
        draft = ParameterSet(
            admin_config_id=config.id,
            version=2,
            status=ParameterStatus.DRAFT,
            payload={"season": "summer", "note": "work in progress"},
            previous_version_id=parameter.id,
        )
        session.add(draft)

    return config, parameter


def ensure_tag(session, *, name: str, status: TagStatus) -> Tag:
    tag = session.query(Tag).filter(Tag.name == name).first()
    if tag is None:
        tag = Tag(name=name, status=status)
        session.add(tag)
        session.flush()
    else:
        tag.status = status
    return tag


def ensure_product(
    session,
    *,
    seller: User,
    title: str,
    description: str,
    price: Decimal,
    status: ProductStatus,
    tag_specs: list[tuple[str, TagStatus]],
) -> Product:
    product = (
        session.query(Product)
        .filter(Product.title == title, Product.seller_id == seller.id)
        .first()
    )
    if product is None:
        product = Product(
            seller_id=seller.id,
            title=title,
            description=description,
            price=price,
            status=status,
        )
        session.add(product)
        session.flush()
    else:
        product.description = description
        product.price = price
        product.status = status

    for name, tag_status in tag_specs:
        tag = ensure_tag(session, name=name, status=tag_status)
        if tag not in product.tags:
            product.tags.append(tag)
    return product


def ensure_coupon(
    session,
    *,
    code: str,
    description: str,
    discount_amount: Decimal,
    min_revenue: Decimal,
    min_sales: int,
    status: CouponStatus,
    scope: CouponScope = CouponScope.ALL,
) -> Coupon:
    coupon = session.query(Coupon).filter(Coupon.code == code).first()
    if coupon is None:
        coupon = Coupon(
            code=code,
            status=status,
            scope=scope,
            description=description,
            min_revenue=min_revenue,
            min_sales=min_sales,
            discount_amount=discount_amount,
        )
        session.add(coupon)
    else:
        coupon.status = status
        coupon.scope = scope
        coupon.description = description
        coupon.min_revenue = min_revenue
        coupon.min_sales = min_sales
        coupon.discount_amount = discount_amount
    return coupon


def ensure_coupon_assignment(
    session,
    *,
    coupon: Coupon,
    user: User,
    used: bool = False,
) -> CouponAssignment:
    assignment = (
        session.query(CouponAssignment)
        .filter(
            CouponAssignment.user_id == user.id,
            CouponAssignment.coupon_id == coupon.id,
        )
        .first()
    )
    if assignment is None:
        assignment = CouponAssignment(user_id=user.id, coupon_id=coupon.id, used=used)
        if used:
            assignment.used_at = datetime.now(tz=timezone.utc)
        session.add(assignment)
    else:
        assignment.used = used
        assignment.used_at = datetime.now(tz=timezone.utc) if used else None
    return assignment


def ensure_deal(
    session,
    *,
    product: Product,
    buyer: User,
    coupon: Coupon | None,
    config: AdminConfig,
    status: DealStatus,
) -> Deal:
    deal = (
        session.query(Deal)
        .filter(Deal.product_id == product.id, Deal.buyer_id == buyer.id)
        .first()
    )
    if deal is None:
        deal = Deal(
            product_id=product.id,
            buyer_id=buyer.id,
            seller_id=product.seller_id,
        )
        session.add(deal)
        session.flush()

    deal.status = status
    if status == DealStatus.CONFIRMED_BY_SELLER:
        deal.confirmed_at = datetime.now(tz=timezone.utc) - timedelta(days=1)
        coupon_discount = coupon.discount_amount if coupon else None
        final_price, _ = apply_discount(
            base_price=product.price,
            is_member=buyer.membership is not None
            and buyer.membership.level == MembershipLevel.SHOPPER,
            min_price=Decimal("50.00"),
            subsidy_cap=Decimal("30.00"),
            coupon_discount=coupon_discount,
        )
        if coupon:
            deal.used_coupon_id = coupon.id
        cashback_ratio = Decimal(str(config.cashback_default))
        cashback_amount = (final_price * cashback_ratio).quantize(Decimal("0.01"))
        cashback = session.query(Cashback).filter(Cashback.deal_id == deal.id).first()
        if cashback is None:
            cashback = Cashback(
                deal_id=deal.id,
                ratio=cashback_ratio,
                amount=cashback_amount,
            )
            session.add(cashback)
        else:
            cashback.ratio = cashback_ratio
            cashback.amount = cashback_amount
        product.status = ProductStatus.SOLD
    return deal


def ensure_synonyms(session) -> None:
    entries = {
        "camera": ["photography", "dslr", "lens"],
        "console": ["gaming", "retro", "arcade"],
        "vinyl": ["record", "music", "lp"],
    }
    for word, synonyms in entries.items():
        entry = session.query(SynonymEntry).filter(SynonymEntry.word == word).first()
        if entry is None:
            entry = SynonymEntry(word=word, synonyms=synonyms)
            session.add(entry)
        else:
            entry.synonyms = synonyms


def ensure_audit_entry(
    session,
    *,
    actor: User | None,
    action: str,
    entity: str,
    entity_id: int | str,
    diff: dict,
) -> None:
    existing = (
        session.query(AuditLog)
        .filter(AuditLog.action == action, AuditLog.entity_id == str(entity_id))
        .first()
    )
    if existing is None:
        session.add(
            AuditLog(
                actor_user_id=actor.id if actor else None,
                action=action,
                entity=entity,
                entity_id=str(entity_id),
                diff=diff,
            )
        )


def main() -> None:
    with session_scope() as session:
        admin = ensure_user(
            session,
            email=settings.admin_default_email,
            password="admin123",
            is_admin=True,
        )
        seller_anna = ensure_user(
            session,
            email="anna.seller@c2c.local",
            password="seller123",
        )
        seller_mike = ensure_user(
            session,
            email="mike.seller@c2c.local",
            password="seller123",
        )
        buyer_jane = ensure_user(
            session,
            email="jane.buyer@c2c.local",
            password="buyer123",
            membership_level=MembershipLevel.SHOPPER,
        )
        buyer_omar = ensure_user(
            session,
            email="omar.buyer@c2c.local",
            password="buyer123",
        )

        config, primary_parameter = ensure_admin_config(session)
        ensure_synonyms(session)

        welcome_coupon = ensure_coupon(
            session,
            code="WELCOME10",
            description="10 currency units off for first purchase",
            discount_amount=Decimal("10.00"),
            min_revenue=Decimal("80.00"),
            min_sales=0,
            status=CouponStatus.ACTIVE,
        )
        ensure_coupon_assignment(session, coupon=welcome_coupon, user=buyer_jane, used=True)

        ensure_coupon(
            session,
            code="LOYALTY15",
            description="15 off loyal shopper coupon",
            discount_amount=Decimal("15.00"),
            min_revenue=Decimal("100.00"),
            min_sales=1,
            status=CouponStatus.DRAFT,
        )

        vintage_camera = ensure_product(
            session,
            seller=seller_anna,
            title="Vintage Camera",
            description="Classic film camera in great condition with leather case",
            price=Decimal("140.00"),
            status=ProductStatus.PUBLISHED,
            tag_specs=[
                ("electronics", TagStatus.APPROVED),
                ("camera", TagStatus.APPROVED),
                ("vintage", TagStatus.APPROVED),
            ],
        )

        retro_console = ensure_product(
            session,
            seller=seller_mike,
            title="Retro Game Console",
            description="Refurbished 90s console with two controllers",
            price=Decimal("220.00"),
            status=ProductStatus.PUBLISHED,
            tag_specs=[
                ("electronics", TagStatus.APPROVED),
                ("console", TagStatus.APPROVED),
            ],
        )

        vinyl_bundle = ensure_product(
            session,
            seller=seller_anna,
            title="Jazz Vinyl Bundle",
            description="Set of five rare jazz records",
            price=Decimal("85.00"),
            status=ProductStatus.DRAFT,
            tag_specs=[
                ("music", TagStatus.PENDING),
                ("vinyl", TagStatus.PENDING),
            ],
        )

        ensure_deal(
            session,
            product=vintage_camera,
            buyer=buyer_jane,
            coupon=welcome_coupon,
            config=config,
            status=DealStatus.CONFIRMED_BY_SELLER,
        )

        ensure_deal(
            session,
            product=retro_console,
            buyer=buyer_omar,
            coupon=None,
            config=config,
            status=DealStatus.INITIATED,
        )

        ensure_audit_entry(
            session,
            actor=admin,
            action="admin.parameter.publish",
            entity="ParameterSet",
            entity_id=primary_parameter.id,
            diff={"version": primary_parameter.version},
        )
        ensure_audit_entry(
            session,
            actor=seller_anna,
            action="product.create",
            entity="Product",
            entity_id=vintage_camera.id,
            diff={"title": vintage_camera.title},
        )
        ensure_audit_entry(
            session,
            actor=buyer_jane,
            action="deal.confirm",
            entity="Deal",
            entity_id=vintage_camera.id,
            diff={"product": vintage_camera.title},
        )

        print("Demo data seeded successfully.")


    if __name__ == "__main__":
        main()
