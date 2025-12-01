"""Integration tests with real Claude SDK."""
import os
import pytest
from unittest.mock import MagicMock

from src.claude import TeleClaudeClient, create_claude_options
from src.config.settings import Config, ClaudeConfig


# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)


@pytest.fixture
def config():
    """Real config for integration tests."""
    return Config(
        allowed_users=[12345],
        claude=ClaudeConfig(
            max_turns=2,
            permission_mode="acceptEdits",
            max_budget_usd=0.10,
        ),
    )


@pytest.fixture
def session(tmp_path):
    """Real session for integration tests."""
    return MagicMock(
        id="integ_test",
        claude_session_id=None,
        current_directory=str(tmp_path),
        project_path=str(tmp_path),
    )


@pytest.mark.asyncio
async def test_simple_query(config, session):
    """Test a simple query returns response."""
    async with TeleClaudeClient(config, session) as client:
        await client.query("What is 2+2? Reply with just the number.")

        responses = []
        async for message in client.receive_response():
            responses.append(message)

        assert len(responses) > 0


@pytest.mark.asyncio
async def test_options_creation(config, session):
    """Test options are created correctly."""
    options = create_claude_options(config, session)

    assert options.max_turns == 2
    assert options.max_budget_usd == 0.10
    assert "Bash" in options.allowed_tools


@pytest.mark.asyncio
async def test_context_manager_works(config, session):
    """Test TeleClaudeClient context manager initializes and cleans up."""
    client = TeleClaudeClient(config, session)

    # Client should not be initialized before entering context
    assert client.client is None

    async with client as entered_client:
        # Client should be initialized within context
        assert entered_client.client is not None
        assert entered_client == client

    # After exiting, client should still exist but context is cleaned up
    assert client.client is not None
