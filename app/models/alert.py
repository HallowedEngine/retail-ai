"""
Alert and notification models for stock warnings and system notifications.
"""
from typing import Optional
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, ForeignKey, Index, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Alert(Base):
    """Alert model for stock warnings and notifications."""

    __tablename__ = "alerts"

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Alert details
    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )  # 'low_stock', 'expiry_warning', 'out_of_stock', 'system'
    severity: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False
    )  # 'low', 'medium', 'high', 'critical'

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status tracking
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_sent_email: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_email_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Flexible metadata storage
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSONB if "postgresql" else Text,
        nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="alerts")
    product = relationship("Product", back_populates="alerts")

    # Indexes
    __table_args__ = (
        Index("idx_alerts_user", "user_id"),
        Index("idx_alerts_user_unread", "user_id", "is_read"),
        Index("idx_alerts_type", "alert_type"),
        Index("idx_alerts_severity", "severity"),
        Index("idx_alerts_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, type={self.alert_type}, severity={self.severity})>"


class EmailQueue(Base):
    """Email queue for asynchronous email sending."""

    __tablename__ = "email_queue"

    # Foreign keys
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Email details
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Sending status
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        index=True
    )  # 'pending', 'sent', 'failed', 'cancelled'
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="email_queue")

    # Indexes
    __table_args__ = (
        Index("idx_email_queue_user", "user_id"),
        Index("idx_email_queue_status", "status"),
        Index("idx_email_queue_pending", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<EmailQueue(id={self.id}, to={self.recipient_email}, status={self.status})>"


class AuditLog(Base):
    """Audit log for tracking all system actions."""

    __tablename__ = "audit_logs"

    # Foreign keys
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Action details
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Change tracking
    changes: Mapped[Optional[dict]] = mapped_column(
        JSONB if "postgresql" else Text,
        nullable=True
    )

    # Request metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 compatible
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Note: No relationship to User since we want to keep audit logs even if user is deleted

    # Indexes
    __table_args__ = (
        Index("idx_audit_logs_user", "user_id"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_resource", "resource_type", "resource_id"),
        Index("idx_audit_logs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, resource={self.resource_type})>"
