"""Test unified session model."""
from src.storage.models import Session


def test_session_uses_uuid_primary_key():
    """Session model uses claude_session_id as primary key."""
    session = Session(
        id="550e8400-e29b-41d4-a716-446655440000",
        telegram_user_id=12345,
        project_path="/root/work/myproject",
    )
    # id should be the claude session UUID, not a hex token
    assert "-" in session.id  # UUIDs contain dashes
    assert len(session.id) == 36  # UUID length


def test_session_no_redundant_fields():
    """Session model removed redundant fields."""
    session = Session(
        id="550e8400-e29b-41d4-a716-446655440000",
        telegram_user_id=12345,
        project_path="/root/work/myproject",
    )
    # These fields should not exist
    assert not hasattr(session, "claude_session_id")
    assert not hasattr(session, "project_name")
    assert not hasattr(session, "current_directory")
    assert not hasattr(session, "status")
