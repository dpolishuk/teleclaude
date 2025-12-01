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


def test_client_builds_complete_options(mock_config, mock_session):
    """Client builds options with all fields correctly set."""
    mock_session.claude_session_id = "claude_abc123"
    client = TeleClaudeClient(mock_config, mock_session)
    options = client._build_options()

    # Verify all 7 fields
    assert options.max_turns == 10
    assert options.permission_mode == "acceptEdits"
    assert options.max_budget_usd == 5.0
    assert options.cwd == "/home/user/myapp"
    assert options.resume == "claude_abc123"
    assert options.allowed_tools == ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
    assert options.hooks == {}


@pytest.mark.asyncio
async def test_async_context_manager(mock_config, mock_session):
    """Client supports async context manager protocol."""
    client = TeleClaudeClient(mock_config, mock_session)

    # Test __aenter__
    result = await client.__aenter__()
    assert result is client

    # Test __aexit__
    await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_query_method(mock_config, mock_session):
    """Client query method yields messages."""
    client = TeleClaudeClient(mock_config, mock_session)
    prompt = "Hello, Claude!"

    messages = []
    async for message in client.query(prompt):
        messages.append(message)

    # Verify we got at least one message
    assert len(messages) >= 1

    # Verify message structure
    first_message = messages[0]
    assert first_message["type"] == "assistant"
    assert "content" in first_message
    assert isinstance(first_message["content"], list)
    assert first_message["content"][0]["type"] == "text"
    assert "Response to:" in first_message["content"][0]["text"]
    assert prompt in first_message["content"][0]["text"]


def test_get_session_id(mock_config, mock_session):
    """Client returns session's claude_session_id."""
    # Test with no session ID
    client = TeleClaudeClient(mock_config, mock_session)
    assert client.get_session_id() is None

    # Test with session ID
    mock_session.claude_session_id = "claude_xyz789"
    assert client.get_session_id() == "claude_xyz789"
