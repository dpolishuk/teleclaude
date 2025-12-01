"""Test bot command handlers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.bot.handlers import start, help_cmd, pwd


@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    update = MagicMock()
    update.effective_user.id = 12345678
    update.effective_user.first_name = "Test"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock context."""
    context = MagicMock()
    context.bot_data = {"config": MagicMock()}
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
