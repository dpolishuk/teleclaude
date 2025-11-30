"""Database models."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import String, Integer, Float, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class SessionStatus(str, Enum):
    """Session status enum."""

    ACTIVE = "active"
    IDLE = "idle"
    ARCHIVED = "archived"


class Session(Base):
    """Session model."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    claude_session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    project_path: Mapped[str] = mapped_column(Text, nullable=False)
    project_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    current_directory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus), nullable=False, default=SessionStatus.ACTIVE, insert_default=SessionStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(timezone.utc), insert_default=lambda: datetime.now(timezone.utc))
    last_active: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, insert_default=0.0)

    def __init__(self, **kwargs):
        """Initialize with defaults."""
        kwargs.setdefault('status', SessionStatus.ACTIVE)
        kwargs.setdefault('total_cost_usd', 0.0)
        kwargs.setdefault('created_at', datetime.now(timezone.utc))
        super().__init__(**kwargs)


class Usage(Base):
    """Usage tracking model."""

    __tablename__ = "usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[str]] = mapped_column(
        String(32), ForeignKey("sessions.id"), nullable=True
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
    session_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
