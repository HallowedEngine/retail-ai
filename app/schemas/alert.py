"""
Pydantic schemas for Alert model.
"""
from typing import Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class AlertType(str, Enum):
    """Alert types."""
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    EXPIRY_WARNING = "expiry_warning"
    SYSTEM = "system"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertBase(BaseModel):
    """Base alert schema."""
    alert_type: AlertType
    severity: AlertSeverity = AlertSeverity.MEDIUM
    title: str = Field(..., max_length=255)
    message: Optional[str] = None


class AlertCreate(AlertBase):
    """Schema for creating an alert."""
    product_id: Optional[uuid.UUID] = None
    expires_at: Optional[datetime] = None
    metadata_: Optional[dict] = Field(None, alias="metadata")


class AlertUpdate(BaseModel):
    """Schema for updating an alert."""
    is_read: Optional[bool] = None
    is_sent_email: Optional[bool] = None


class AlertResponse(AlertBase):
    """Schema for alert response."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    product_id: Optional[uuid.UUID]
    is_read: bool
    is_sent_email: bool
    sent_email_at: Optional[datetime]
    expires_at: Optional[datetime]
    metadata_: Optional[dict] = Field(None, alias="metadata")
    created_at: datetime
    updated_at: datetime


class AlertWithProduct(AlertResponse):
    """Alert with product details."""
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    current_stock: Optional[int] = None


class AlertListResponse(BaseModel):
    """Paginated alert list."""
    items: list[AlertResponse]
    total: int
    unread_count: int
    page: int
    page_size: int
    pages: int


class AlertStats(BaseModel):
    """Alert statistics."""
    total: int
    unread: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    recent_count: int  # Last 24 hours
