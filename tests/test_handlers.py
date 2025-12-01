"""Test bot command handlers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.bot.handlers import start, help_cmd, pwd, handle_message


@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    update = MagicMock()
    update.effective_user.id = 12345678
    update.effective_user.first_name = "Test"
    update.message = AsyncMock()
    update.message.text = "Hello Claude"
    update.message.reply_text = AsyncMock(return_value=AsyncMock())
    return update


@pytest.fixture
def mock_context():
    """Create mock context."""
    context = MagicMock()
    context.bot_data = {
        "config": MagicMock(
            claude=MagicMock(
                max_turns=10,
                permission_mode="acceptEdits",
                max_budget_usd=5.0
            ),
            streaming=MagicMock(
                edit_throttle_ms=1000,
                chunk_size=3800
            ),
        )
    }
    context.user_data = {}
    return context


@pytest.mark.asyncio
async def test_start_handler(mock_update, mock_context):
    """start handler sends welcome message."""
    await start(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = str(mock_update.message.reply_text.call_args)
    assert "TeleClaude" in call_args or "Welcome" in call_args


@pytest.mark.asyncio
async def test_help_handler(mock_update, mock_context):
    """help handler lists commands."""
    await help_cmd(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = str(mock_update.message.reply_text.call_args)
    assert "/new" in call_args
    assert "/help" in call_args


@pytest.mark.asyncio
async def test_pwd_with_session(mock_update, mock_context):
    """pwd shows current directory when session exists."""
    mock_context.user_data["current_session"] = MagicMock(
        current_directory="/home/user/myapp"
    )

    await pwd(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = str(mock_update.message.reply_text.call_args)
    assert "/home/user/myapp" in call_args


@pytest.mark.asyncio
async def test_pwd_without_session(mock_update, mock_context):
    """pwd shows error when no session."""
    mock_context.user_data["current_session"] = None

    await pwd(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = str(mock_update.message.reply_text.call_args)
    assert "session" in call_args.lower()


@pytest.mark.asyncio
async def test_handle_message_no_session(mock_update, mock_context):
    """handle_message prompts to create session when none exists."""
    mock_context.user_data = {}

    await handle_message(mock_update, mock_context)

    mock_update.message.reply_text.assert_called()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "No active session" in call_args


@pytest.mark.asyncio
async def test_handle_message_with_session_calls_claude(mock_update, mock_context):
    """handle_message sends prompt to Claude when session exists."""
    mock_session = MagicMock(
        id="sess123",
        claude_session_id=None,
        current_directory="/test",
        project_path="/test",
        total_cost_usd=0.0,
    )
    mock_context.user_data = {"current_session": mock_session}

    # Create a mock thinking message
    mock_thinking_msg = AsyncMock()
    mock_thinking_msg.edit_text = AsyncMock()
    mock_update.message.reply_text.return_value = mock_thinking_msg

    # Mock the TeleClaudeClient
    with patch("src.bot.handlers.TeleClaudeClient") as mock_client_class:
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.query = AsyncMock()

        # Create an async generator that yields nothing (empty response)
        async def mock_receive_response():
            if False:
                yield

        mock_client.receive_response = MagicMock(return_value=mock_receive_response())
        mock_client_class.return_value = mock_client

        # Also mock MessageStreamer
        with patch("src.bot.handlers.MessageStreamer") as mock_streamer_class:
            mock_streamer = AsyncMock()
            mock_streamer.append_text = AsyncMock()
            mock_streamer.flush = AsyncMock()
            mock_streamer_class.return_value = mock_streamer

            await handle_message(mock_update, mock_context)

            # Should have called query with the user's message
            mock_client.query.assert_called_once_with("Hello Claude")
