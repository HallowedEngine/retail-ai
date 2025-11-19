"""
User model for authentication and authorization.
"""
from typing import Optional
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """User account model."""

    __tablename__ = "users"

    # User credentials
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile information
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Role and permissions
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    products = relationship("Product", back_populates="user", cascade="all, delete-orphan")
    receipts = relationship("Receipt", back_populates="user", cascade="all, delete-orphan")
    stock_transactions = relationship("StockTransaction", back_populates="user", foreign_keys="StockTransaction.user_id")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    email_queue = relationship("EmailQueue", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
