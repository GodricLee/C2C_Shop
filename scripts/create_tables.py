"""Create database tables for the C2C backend."""
from __future__ import annotations

from app.db import Base, engine

# Import models to ensure metadata registration
from app.models import (  # noqa: F401
    admin_config,
    audit_log,
    cashback,
    coupon,
    deal,
    membership,
    parameter_set,
    product,
    synonym,
    tag,
    user,
)


def main() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()
    print("Tables created successfully.")
