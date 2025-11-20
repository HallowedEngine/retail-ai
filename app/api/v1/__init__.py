"""API v1 Router."""
from fastapi import APIRouter

from app.api.v1 import auth, products, receipts, stock, alerts, dashboard

api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(receipts.router)
api_router.include_router(stock.router)
api_router.include_router(alerts.router)
api_router.include_router(dashboard.router)

__all__ = ["api_router"]
