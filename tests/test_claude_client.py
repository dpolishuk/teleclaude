"""Test Claude client wrapper."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.claude.client import TeleClaudeClient, create_claude_options
from src.config.settings import Config, ClaudeConfig


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return Config(
        allowed_users=[12345678],
        claude=ClaudeConfig(
            max_turns=10,
            permission_mode="acceptEdits",
            max_budget_usd=5.0,
        ),
    )


@pytest.fixture
def mock_session():
    """Create mock session."""
    return MagicMock(
        id="test123",
        claude_session_id=None,
        current_directory="/home/user/myapp",
        project_path="/home/user/myapp",
    )


def test_create_claude_options_basic(mock_config, mock_session):
    """create_claude_options builds correct options."""
    options = create_claude_options(mock_config, mock_session)

    assert options.max_turns == 10
    assert options.permission_mode == "acceptEdits"
    assert options.max_budget_usd == 5.0
    assert options.cwd == "/home/user/myapp"


def test_create_claude_options_with_resume(mock_config, mock_session):
    """create_claude_options includes resume when session has claude_session_id."""
    mock_session.claude_session_id = "claude_abc123"
    options = create_claude_options(mock_config, mock_session)

    # Default behavior uses resume (not fork_session)
    assert options.resume == "claude_abc123"


def test_create_claude_options_with_fork_mode(mock_config, mock_session):
    """create_claude_options uses fork_session when resume_mode is fork."""
    mock_session.claude_session_id = "claude_abc123"
    options = create_claude_options(mock_config, mock_session, resume_mode="fork")

    assert options.fork_session == "claude_abc123"


def test_teleclaude_client_init(mock_config, mock_session):
    """TeleClaudeClient initializes with config and session."""
    client = TeleClaudeClient(mock_config, mock_session)

    assert client.config == mock_config
    assert client.session == mock_session
