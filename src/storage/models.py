"""Database models."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class Session(Base):
    """Session model - maps telegram users to Claude sessions."""

    __tablename__ = "sessions"

    # Primary key is now the Claude session UUID
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    project_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        insert_default=lambda: datetime.now(timezone.utc),
    )
    last_active: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        insert_default=lambda: datetime.now(timezone.utc),
    )
    total_cost_usd: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, insert_default=0.0
    )

    def __init__(self, **kwargs):
        """Initialize with defaults."""
        kwargs.setdefault("total_cost_usd", 0.0)
        kwargs.setdefault("created_at", datetime.now(timezone.utc))
        kwargs.setdefault("last_active", datetime.now(timezone.utc))
        super().__init__(**kwargs)


class Usage(Base):
    """Usage tracking model."""

    __tablename__ = "usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=True
    )
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    """Audit log model."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
