"""
Stock transaction model for inventory tracking and audit trail.
"""
from typing import Optional
import uuid
from sqlalchemy import String, Integer, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class StockTransaction(Base):
    """Stock transaction model for tracking all inventory movements."""

    __tablename__ = "stock_transactions"

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Transaction details
    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # 'in', 'out', 'adjustment'
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Reference to source document
    reference_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )  # 'receipt', 'manual', 'sale', 'adjustment'
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Additional notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="stock_transactions", foreign_keys=[user_id])
    product = relationship("Product", back_populates="stock_transactions")
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        Index("idx_stock_transactions_user", "user_id"),
        Index("idx_stock_transactions_product", "product_id"),
        Index("idx_stock_transactions_type", "transaction_type"),
        Index("idx_stock_transactions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<StockTransaction(id={self.id}, type={self.transaction_type}, qty={self.quantity})>"
