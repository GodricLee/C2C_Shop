"""Upgrade existing database schema with new columns if missing."""
from __future__ import annotations

from sqlalchemy import inspect, text

from app.db import engine


def _ensure_mysql_columns() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("users")}
    statements: list[str] = []

    if "is_admin" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN is_admin TINYINT(1) NOT NULL DEFAULT 0 AFTER password_hash"
        )
    if "status" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN status ENUM('ACTIVE','SUSPENDED','CLOSED') "
            "NOT NULL DEFAULT 'ACTIVE' AFTER is_admin"
        )
    if "two_fa_enabled" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN two_fa_enabled TINYINT(1) NOT NULL DEFAULT 1 AFTER status"
        )
    if "created_at" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN created_at DATETIME(6) NOT NULL "
            "DEFAULT CURRENT_TIMESTAMP(6) AFTER two_fa_enabled"
        )

    if not statements:
        print("Schema already up to date.")
        return

    with engine.begin() as connection:
        for statement in statements:
            print(f"Executing: {statement}")
            connection.execute(text(statement))

    print("Schema upgrade complete.")


def main() -> None:
    dialect = engine.dialect.name
    if dialect == "mysql":
        _ensure_mysql_columns()
    else:
        print(f"No upgrade actions defined for dialect '{dialect}'.")


if __name__ == "__main__":
    main()
