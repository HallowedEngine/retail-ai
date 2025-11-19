"""
SQLAlchemy models for the Retail AI application.
Import all models here to ensure they're registered with SQLAlchemy.
"""
from app.models.user import User
from app.models.product import Product
from app.models.receipt import Receipt, ReceiptItem
from app.models.stock import StockTransaction
from app.models.alert import Alert, EmailQueue, AuditLog

__all__ = [
    "User",
    "Product",
    "Receipt",
    "ReceiptItem",
    "StockTransaction",
    "Alert",
    "EmailQueue",
    "AuditLog",
]
