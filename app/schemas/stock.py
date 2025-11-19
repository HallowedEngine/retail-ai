"""
Pydantic schemas for StockTransaction model.
"""
from typing import Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class TransactionType(str, Enum):
    """Stock transaction types."""
    IN = "in"
    OUT = "out"
    ADJUSTMENT = "adjustment"


class ReferenceType(str, Enum):
    """Transaction reference types."""
    RECEIPT = "receipt"
    MANUAL = "manual"
    SALE = "sale"
    ADJUSTMENT = "adjustment"
    RETURN = "return"


class StockTransactionBase(BaseModel):
    """Base stock transaction schema."""
    transaction_type: TransactionType
    quantity: int = Field(..., description="Positive for IN, negative for OUT")
    reference_type: Optional[ReferenceType] = None
    reference_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class StockTransactionCreate(StockTransactionBase):
    """Schema for creating a stock transaction."""
    product_id: uuid.UUID


class StockAdjustment(BaseModel):
    """Schema for manual stock adjustment."""
    product_id: uuid.UUID
    new_quantity: int = Field(..., ge=0)
    notes: Optional[str] = None


class StockTransactionResponse(StockTransactionBase):
    """Schema for stock transaction response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    product_id: uuid.UUID
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime


class StockTransactionWithProduct(StockTransactionResponse):
    """Stock transaction with product details."""
    product_name: str
    product_sku: str
    stock_before: Optional[int] = None
    stock_after: Optional[int] = None


class StockTransactionListResponse(BaseModel):
    """Paginated stock transaction list."""
    items: list[StockTransactionResponse]
    total: int
    page: int
    page_size: int
    pages: int


class StockSummary(BaseModel):
    """Stock summary statistics."""
    total_products: int
    total_stock_value: Optional[float] = None
    low_stock_count: int
    out_of_stock_count: int
    total_categories: int
    recent_transactions: int  # Last 24 hours


class StockStats(BaseModel):
    """Stock statistics for dashboard."""
    total_in: int  # Total items added in period
    total_out: int  # Total items removed in period
    net_change: int  # Net change in period
    transactions_count: int
    most_active_products: list[dict]  # Top 5 products by transaction count
    stock_distribution: dict  # By category
