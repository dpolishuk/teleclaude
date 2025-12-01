"""Test bot middleware."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.bot.middleware import auth_middleware
from src.config.settings import Config


@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    update = MagicMock()
    update.effective_user.id = 12345678
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock context with config."""
    context = MagicMock()
    context.bot_data = {
        "config": Config(allowed_users=[12345678])
    }
    return context


@pytest.mark.asyncio
async def test_auth_middleware_allows_authorized(mock_update, mock_context):
    """auth_middleware allows authorized users."""
    handler = AsyncMock(return_value="success")
    wrapped = auth_middleware(handler)

    result = await wrapped(mock_update, mock_context)

    assert result == "success"
    handler.assert_called_once_with(mock_update, mock_context)


@pytest.mark.asyncio
async def test_auth_middleware_blocks_unauthorized(mock_update, mock_context):
    """auth_middleware blocks unauthorized users."""
    mock_update.effective_user.id = 99999999  # Not in whitelist
    handler = AsyncMock()
    wrapped = auth_middleware(handler)

    await wrapped(mock_update, mock_context)

    handler.assert_not_called()
    mock_update.message.reply_text.assert_called_once()
    assert "Unauthorized" in str(mock_update.message.reply_text.call_args)


@pytest.mark.asyncio
async def test_auth_middleware_preserves_function_name():
    """auth_middleware preserves wrapped function name."""
    async def my_handler(update, context):
        pass

    wrapped = auth_middleware(my_handler)

    assert wrapped.__name__ == "my_handler"


@pytest.mark.asyncio
async def test_auth_middleware_handles_missing_config(mock_update):
    """auth_middleware handles missing config gracefully."""
    context = MagicMock()
    context.bot_data = {}  # No config
    handler = AsyncMock()
    wrapped = auth_middleware(handler)

    await wrapped(mock_update, context)

    handler.assert_not_called()
    mock_update.message.reply_text.assert_called_once()
    assert "not configured" in str(mock_update.message.reply_text.call_args).lower()


@pytest.fixture
def mock_callback_update():
    """Create mock Telegram update with callback query."""
    update = MagicMock()
    update.effective_user.id = 12345678
    update.message = None  # Callback queries don't have message
    update.callback_query.answer = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_auth_middleware_allows_authorized_callback(mock_callback_update, mock_context):
    """auth_middleware allows authorized users for callback queries."""
    handler = AsyncMock(return_value="success")
    wrapped = auth_middleware(handler)

    result = await wrapped(mock_callback_update, mock_context)

    assert result == "success"
    handler.assert_called_once_with(mock_callback_update, mock_context)


@pytest.mark.asyncio
async def test_auth_middleware_blocks_unauthorized_callback(mock_callback_update, mock_context):
    """auth_middleware blocks unauthorized users for callback queries."""
    mock_callback_update.effective_user.id = 99999999  # Not in whitelist
    handler = AsyncMock()
    wrapped = auth_middleware(handler)

    await wrapped(mock_callback_update, mock_context)

    handler.assert_not_called()
    mock_callback_update.callback_query.answer.assert_called_once()
    assert "Unauthorized" in str(mock_callback_update.callback_query.answer.call_args)
