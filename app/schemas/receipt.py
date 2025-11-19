"""
Pydantic schemas for Receipt and ReceiptItem models.
"""
from typing import Optional
from datetime import datetime, date
import uuid
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


# Receipt Item schemas
class ReceiptItemBase(BaseModel):
    """Base receipt item schema."""
    name_raw: Optional[str] = Field(None, max_length=500)
    quantity: Optional[Decimal] = Field(None, decimal_places=3)
    unit: Optional[str] = Field(None, max_length=50)
    unit_price: Optional[Decimal] = Field(None, decimal_places=2)
    total_price: Optional[Decimal] = Field(None, decimal_places=2)


class ReceiptItemCreate(ReceiptItemBase):
    """Schema for creating a receipt item."""
    product_id: Optional[uuid.UUID] = None
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1, decimal_places=4)
    matched_automatically: bool = False


class ReceiptItemUpdate(BaseModel):
    """Schema for updating a receipt item."""
    product_id: Optional[uuid.UUID] = None
    name_raw: Optional[str] = Field(None, max_length=500)
    quantity: Optional[Decimal] = Field(None, decimal_places=3)
    unit: Optional[str] = Field(None, max_length=50)
    unit_price: Optional[Decimal] = Field(None, decimal_places=2)
    total_price: Optional[Decimal] = Field(None, decimal_places=2)


class ReceiptItemResponse(ReceiptItemBase):
    """Schema for receipt item response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    receipt_id: uuid.UUID
    product_id: Optional[uuid.UUID]
    confidence_score: Optional[Decimal]
    matched_automatically: bool
    created_at: datetime
    updated_at: datetime


# Receipt schemas
class ReceiptBase(BaseModel):
    """Base receipt schema."""
    receipt_number: Optional[str] = Field(None, max_length=100)
    store_name: Optional[str] = Field(None, max_length=255)
    receipt_date: Optional[date] = None
    total_amount: Optional[Decimal] = Field(None, decimal_places=2)


class ReceiptCreate(ReceiptBase):
    """Schema for creating a receipt (via upload)."""
    image_url: str  # Will be populated after upload
    metadata_: Optional[dict] = Field(None, alias="metadata")


class ReceiptUpdate(ReceiptBase):
    """Schema for updating receipt information."""
    processing_status: Optional[str] = Field(None, max_length=50)
    metadata_: Optional[dict] = Field(None, alias="metadata")


class ReceiptResponse(ReceiptBase):
    """Schema for receipt response."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    image_url: str
    image_hash: Optional[str]
    ocr_raw_text: Optional[str]
    ocr_confidence: Optional[Decimal]
    processing_status: str
    processed_at: Optional[datetime]
    metadata_: Optional[dict] = Field(None, alias="metadata")
    created_at: datetime
    updated_at: datetime


class ReceiptWithItems(ReceiptResponse):
    """Receipt with its items."""
    items: list[ReceiptItemResponse]


class ReceiptListResponse(BaseModel):
    """Paginated receipt list response."""
    items: list[ReceiptResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ReceiptUploadResponse(BaseModel):
    """Response for receipt upload."""
    receipt_id: uuid.UUID
    status: str
    message: str
    confidence: Optional[Decimal] = None


class ReceiptProcessingStatus(BaseModel):
    """Receipt processing status."""
    receipt_id: uuid.UUID
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: Optional[int] = Field(None, ge=0, le=100)
    message: Optional[str] = None
    items_found: Optional[int] = None
    items_matched: Optional[int] = None
