"""
Product model for inventory management.
"""
from typing import Optional
import uuid
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, Boolean, ForeignKey, Index, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Product(Base):
    """Product inventory model."""

    __tablename__ = "products"

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Product identification
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    barcode_gtin: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # Stock information
    current_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_stock_level: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="adet", nullable=False)

    # Pricing
    unit_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), nullable=True)

    # Additional information
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    shelf_life_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Flexible metadata storage (JSONB for PostgreSQL, JSON for others)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB if "postgresql" else String,
        nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="products")
    receipt_items = relationship("ReceiptItem", back_populates="product")
    stock_transactions = relationship("StockTransaction", back_populates="product")
    alerts = relationship("Alert", back_populates="product")

    # Indexes
    __table_args__ = (
        Index("idx_products_user_id", "user_id"),
        Index("idx_products_barcode", "barcode_gtin"),
        Index("idx_products_low_stock", "user_id", "current_stock"),
        Index("idx_products_sku", "user_id", "sku", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, sku={self.sku}, name={self.name}, stock={self.current_stock})>"

    @property
    def is_low_stock(self) -> bool:
        """Check if product stock is below critical level."""
        return self.current_stock <= self.critical_stock_level

    @property
    def stock_status(self) -> str:
        """Get human-readable stock status."""
        if self.current_stock == 0:
            return "out_of_stock"
        elif self.is_low_stock:
            return "low_stock"
        else:
            return "in_stock"
