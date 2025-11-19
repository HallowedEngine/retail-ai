"""
Receipt model for invoice processing and OCR.
"""
from typing import Optional
import uuid
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import String, Date, DateTime, Numeric, Boolean, ForeignKey, Index, Text, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Receipt(Base):
    """Receipt/Invoice model with OCR processing."""

    __tablename__ = "receipts"

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Receipt information
    receipt_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    store_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    receipt_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), nullable=True)

    # Image storage
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)

    # OCR results
    ocr_raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 4), nullable=True)

    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Flexible metadata storage
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB if "postgresql" else Text,
        nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="receipts")
    items = relationship("ReceiptItem", back_populates="receipt", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_receipts_user_id", "user_id"),
        Index("idx_receipts_status", "processing_status"),
        Index("idx_receipts_date", "receipt_date"),
    )

    def __repr__(self) -> str:
        return f"<Receipt(id={self.id}, number={self.receipt_number}, status={self.processing_status})>"


class ReceiptItem(Base):
    """Individual line items from a receipt."""

    __tablename__ = "receipt_items"

    # Foreign keys
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Item information (as extracted from receipt)
    name_raw: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    quantity: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 3), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), nullable=True)
    total_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), nullable=True)

    # OCR confidence and matching
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(5, 4), nullable=True)
    matched_automatically: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    receipt = relationship("Receipt", back_populates="items")
    product = relationship("Product", back_populates="receipt_items")

    # Indexes
    __table_args__ = (
        Index("idx_receipt_items_receipt", "receipt_id"),
        Index("idx_receipt_items_product", "product_id"),
    )

    def __repr__(self) -> str:
        return f"<ReceiptItem(id={self.id}, name={self.name_raw}, quantity={self.quantity})>"
