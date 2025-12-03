"""Test database models."""
import pytest
from datetime import datetime
from src.storage.models import Session, Usage, AuditLog


def test_session_creation():
    """Session can be created with required fields."""
    session = Session(
        id="test123",
        telegram_user_id=12345678,
        project_path="/home/user/myapp",
    )

    assert session.id == "test123"
    assert session.telegram_user_id == 12345678
    assert session.project_path == "/home/user/myapp"


def test_session_defaults():
    """Session has sensible defaults."""
    session = Session(
        id="test123",
        telegram_user_id=12345678,
        project_path="/home/user/myapp",
    )

    assert session.total_cost_usd == 0.0
    assert session.created_at is not None
    assert session.last_active is not None


def test_usage_creation():
    """Usage record can be created."""
    usage = Usage(
        session_id="test123",
        telegram_user_id=12345678,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
    )

    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.cost_usd == 0.001


def test_audit_log_creation():
    """AuditLog record can be created."""
    log = AuditLog(
        telegram_user_id=12345678,
        action="session_created",
        details="Created new session",
    )

    assert log.action == "session_created"
    assert log.details == "Created new session"
