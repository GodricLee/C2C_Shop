"""Router package exports."""
from app.routers import admin, audit, auth, deals, health, membership, products, promotions

__all__ = [
    "admin",
    "audit",
    "auth",
    "deals",
    "health",
    "membership",
    "products",
    "promotions",
]
