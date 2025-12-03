"""Data access repository."""
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Session, Usage, AuditLog


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
        """Create a new session.

        TODO: This is transitional - in Tasks 5-8, session creation will be lazy.
        The actual UUID will come from the SDK when the first message is sent,
        not during session creation. For now, we generate a temporary hex ID to keep
        create_session working.
        """
        # Mark existing active sessions as idle
        await self._mark_existing_idle(telegram_user_id)

        # TODO: This generates a 32-char hex string. SDK will provide 36-char UUIDs later.
        session = Session(
            id=secrets.token_hex(16),
            telegram_user_id=telegram_user_id,
            project_path=project_path,
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
        """Get active session for user (most recent)."""
        result = await self.db.execute(
            select(Session)
            .where(Session.telegram_user_id == telegram_user_id)
            .order_by(Session.last_active.desc())
            .limit(1)
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
        """Set Claude session ID (deprecated - id is now the claude_session_id)."""
        # This method is now a no-op since id field is the claude_session_id
        # Will be removed in Task 2
        pass

    async def mark_idle(self, session_id: str) -> None:
        """Mark session as idle (updates last_active)."""
        session = await self.get_session(session_id)
        if session:
            session.last_active = datetime.now(timezone.utc)
            await self.db.flush()

    async def mark_active(self, session_id: str) -> None:
        """Mark session as active (updates last_active)."""
        session = await self.get_session(session_id)
        if session:
            await self._mark_existing_idle(session.telegram_user_id)
            session.last_active = datetime.now(timezone.utc)
            await self.db.flush()

    async def _mark_existing_idle(self, telegram_user_id: int) -> None:
        """Update last_active for existing sessions."""
        # This method is now a no-op since status field removed
        # Will be removed in Task 2
        pass


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
