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
