"""
Pydantic schemas for Product model.
"""
from typing import Optional
from datetime import datetime
import uuid
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    """Base product schema."""
    sku: str = Field(..., max_length=100)
    name: str = Field(..., max_length=500)
    category: Optional[str] = Field(None, max_length=255)
    barcode_gtin: Optional[str] = Field(None, max_length=50)
    unit: str = Field(default="adet", max_length=50)
    unit_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    critical_stock_level: int = Field(default=10, ge=0)
    shelf_life_days: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    """Schema for creating a product."""
    current_stock: int = Field(default=0, ge=0)
    metadata_: Optional[dict] = Field(None, alias="metadata")


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    name: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=255)
    barcode_gtin: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=50)
    unit_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    critical_stock_level: Optional[int] = Field(None, ge=0)
    shelf_life_days: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    metadata_: Optional[dict] = Field(None, alias="metadata")


class ProductResponse(ProductBase):
    """Schema for product response."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    current_stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    metadata_: Optional[dict] = Field(None, alias="metadata")
    is_low_stock: bool
    stock_status: str


class ProductWithStock(ProductResponse):
    """Product with stock information."""
    stock_value: Optional[Decimal] = None  # current_stock * unit_price
    days_until_critical: Optional[int] = None  # Estimated days until critical level


class ProductListResponse(BaseModel):
    """Paginated product list response."""
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ProductBulkCreate(BaseModel):
    """Schema for bulk product creation."""
    products: list[ProductCreate]


class ProductBulkCreateResponse(BaseModel):
    """Response for bulk product creation."""
    created: int
    failed: int
    errors: Optional[list[dict]] = None
