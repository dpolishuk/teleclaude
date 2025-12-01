"""Test callback handlers."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.bot.callbacks import handle_callback, parse_callback_data


def test_parse_callback_data_simple():
    """parse_callback_data handles simple callbacks."""
    action, data = parse_callback_data("cancel")
    assert action == "cancel"
    assert data is None


def test_parse_callback_data_with_value():
    """parse_callback_data handles callbacks with values."""
    action, data = parse_callback_data("project:myapp")
    assert action == "project"
    assert data == "myapp"


def test_parse_callback_data_with_colon_in_value():
    """parse_callback_data handles colons in values."""
    action, data = parse_callback_data("approve:req:123:abc")
    assert action == "approve"
    assert data == "req:123:abc"


@pytest.fixture
def mock_callback_query():
    """Create mock callback query."""
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.message.reply_text = AsyncMock()
    return query


@pytest.fixture
def mock_update(mock_callback_query):
    """Create mock update with callback query."""
    update = MagicMock()
    update.callback_query = mock_callback_query
    update.effective_user.id = 12345678
    return update


@pytest.fixture
def mock_context():
    """Create mock context."""
    context = MagicMock()
    context.bot_data = {
        "config": MagicMock(
            projects={"myapp": "/home/user/myapp"}
        )
    }
    context.user_data = {}
    return context


@pytest.mark.asyncio
async def test_handle_callback_cancel(mock_update, mock_context):
    """handle_callback processes cancel."""
    mock_update.callback_query.data = "cancel"

    await handle_callback(mock_update, mock_context)

    mock_update.callback_query.answer.assert_called()


@pytest.mark.asyncio
async def test_handle_callback_project_selection(mock_update, mock_context):
    """handle_callback processes project selection."""
    mock_update.callback_query.data = "project:myapp"

    await handle_callback(mock_update, mock_context)

    mock_update.callback_query.answer.assert_called()
