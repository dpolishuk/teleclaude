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
        """Create a new session (transitional - will be removed in Task 8).

        This method is kept for backward compatibility during the migration.
        New code should use get_or_create_session instead.
        """
        # Generate temporary hex ID (32 chars)
        # In Task 7+, SDK will provide the UUID directly
        session = Session(
            id=secrets.token_hex(16),
            telegram_user_id=telegram_user_id,
            project_path=project_path,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_or_create_session(
        self,
        session_id: str,
        telegram_user_id: int,
        project_path: str,
    ) -> Session:
        """Get existing session or create new one.

        This is the primary method for unified sessions - called when
        SDK returns a session_id.
        """
        session = await self.get_session(session_id)
        if session:
            session.last_active = datetime.now(timezone.utc)
            await self.db.flush()
            return session

        # Create new session with the SDK's session_id as primary key
        session = Session(
            id=session_id,
            telegram_user_id=telegram_user_id,
            project_path=project_path,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID (claude_session_id)."""
        result = await self.db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_active_session_for_user(
        self, telegram_user_id: int
    ) -> Optional[Session]:
        """Get most recent session for user."""
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

    async def list_sessions_for_project(
        self, telegram_user_id: int, project_path: str, limit: int = 10
    ) -> list[Session]:
        """List sessions for a specific project."""
        result = await self.db.execute(
            select(Session)
            .where(Session.telegram_user_id == telegram_user_id)
            .where(Session.project_path == project_path)
            .order_by(Session.last_active.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_session(self, session: Session) -> None:
        """Update session last_active timestamp."""
        session.last_active = datetime.now(timezone.utc)
        await self.db.flush()

    async def add_cost(self, session_id: str, cost: float) -> None:
        """Add cost to session."""
        session = await self.get_session(session_id)
        if session:
            session.total_cost_usd += cost
            session.last_active = datetime.now(timezone.utc)
            await self.db.flush()

    async def get_session_ids_for_project(
        self, telegram_user_id: int, project_path: str
    ) -> set[str]:
        """Get set of session IDs owned by user for a project.

        Used to determine origin (Telegram vs Terminal) in unified list.
        """
        result = await self.db.execute(
            select(Session.id)
            .where(Session.telegram_user_id == telegram_user_id)
            .where(Session.project_path == project_path)
        )
        return {row[0] for row in result.all()}


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
