"""Test Claude client wrapper."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.claude.client import TeleClaudeClient
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
    )


def test_client_init(mock_config, mock_session):
    """Client initializes with config and session."""
    client = TeleClaudeClient(mock_config, mock_session)

    assert client.config == mock_config
    assert client.session == mock_session
    assert client._client is None


def test_client_builds_options(mock_config, mock_session):
    """Client builds correct options."""
    client = TeleClaudeClient(mock_config, mock_session)
    options = client._build_options()

    assert options.max_turns == 10
    assert options.permission_mode == "acceptEdits"
    assert options.cwd == "/home/user/myapp"


def test_client_builds_options_with_resume(mock_config, mock_session):
    """Client includes resume when session has claude_session_id."""
    mock_session.claude_session_id = "claude_abc123"
    client = TeleClaudeClient(mock_config, mock_session)
    options = client._build_options()

    assert options.resume == "claude_abc123"
