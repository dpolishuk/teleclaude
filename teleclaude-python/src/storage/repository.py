"""Data access repository."""
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Session, Usage, AuditLog, SessionStatus


class SessionRepository:
    """Repository for session operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create_session(
        self,
        telegram_user_id: int,
        project_path: str,
        project_name: Optional[str] = None,
    ) -> Session:
        """Create a new session."""
        # Mark existing active sessions as idle
        await self._mark_existing_idle(telegram_user_id)

        session = Session(
            id=secrets.token_hex(16),
            telegram_user_id=telegram_user_id,
            project_path=project_path,
            project_name=project_name,
            current_directory=project_path,
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc),
        )

        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        result = await self.db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_active_session(self, telegram_user_id: int) -> Optional[Session]:
        """Get active session for user."""
        result = await self.db.execute(
            select(Session)
            .where(Session.telegram_user_id == telegram_user_id)
            .where(Session.status == SessionStatus.ACTIVE)
            .order_by(Session.last_active.desc())
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self, telegram_user_id: int, limit: int = 10
    ) -> list[Session]:
        """List sessions for user."""
        result = await self.db.execute(
            select(Session)
            .where(Session.telegram_user_id == telegram_user_id)
            .order_by(Session.last_active.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_session(self, session: Session) -> None:
        """Update session."""
        session.last_active = datetime.now(timezone.utc)
        await self.db.flush()

    async def add_cost(self, session_id: str, cost: float) -> None:
        """Add cost to session."""
        session = await self.get_session(session_id)
        if session:
            session.total_cost_usd += cost
            session.last_active = datetime.now(timezone.utc)
            await self.db.flush()

    async def set_claude_session_id(
        self, session_id: str, claude_session_id: str
    ) -> None:
        """Set Claude session ID."""
        session = await self.get_session(session_id)
        if session:
            session.claude_session_id = claude_session_id
            await self.db.flush()

    async def mark_idle(self, session_id: str) -> None:
        """Mark session as idle."""
        session = await self.get_session(session_id)
        if session:
            session.status = SessionStatus.IDLE
            session.last_active = datetime.now(timezone.utc)
            await self.db.flush()

    async def mark_active(self, session_id: str) -> None:
        """Mark session as active."""
        session = await self.get_session(session_id)
        if session:
            # Mark other active sessions as idle first
            await self._mark_existing_idle(session.telegram_user_id)
            session.status = SessionStatus.ACTIVE
            session.last_active = datetime.now(timezone.utc)
            await self.db.flush()

    async def _mark_existing_idle(self, telegram_user_id: int) -> None:
        """Mark existing active sessions as idle."""
        result = await self.db.execute(
            select(Session)
            .where(Session.telegram_user_id == telegram_user_id)
            .where(Session.status == SessionStatus.ACTIVE)
        )
        for session in result.scalars():
            session.status = SessionStatus.IDLE


class UsageRepository:
    """Repository for usage tracking."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def record_usage(
        self,
        telegram_user_id: int,
        session_id: Optional[str],
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> Usage:
        """Record usage entry."""
        usage = Usage(
            telegram_user_id=telegram_user_id,
            session_id=session_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            timestamp=datetime.now(timezone.utc),
        )

        self.db.add(usage)
        await self.db.flush()
        return usage

    async def get_total_cost(self, telegram_user_id: int) -> float:
        """Get total cost for user."""
        result = await self.db.execute(
            select(Usage.cost_usd).where(Usage.telegram_user_id == telegram_user_id)
        )
        return sum(row[0] for row in result.all())


class AuditRepository:
    """Repository for audit logging."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def log(
        self,
        telegram_user_id: int,
        action: str,
        session_id: Optional[str] = None,
        details: Optional[str] = None,
    ) -> AuditLog:
        """Create audit log entry."""
        entry = AuditLog(
            telegram_user_id=telegram_user_id,
            session_id=session_id,
            action=action,
            details=details,
            timestamp=datetime.now(timezone.utc),
        )

        self.db.add(entry)
        await self.db.flush()
        return entry
