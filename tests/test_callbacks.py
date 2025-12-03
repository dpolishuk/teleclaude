"""Test callback handlers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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

    # Mock database session and repository
    mock_session = MagicMock()
    mock_repo = MagicMock()
    mock_repo.create_session = AsyncMock(return_value=MagicMock(id="test123"))

    # Mock command registry
    mock_registry = MagicMock()
    mock_registry.refresh = AsyncMock(return_value=5)
    mock_context.bot_data["command_registry"] = mock_registry

    with patch("src.bot.callbacks.get_session") as mock_get_session, \
         patch("src.bot.callbacks.SessionRepository", return_value=mock_repo):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await handle_callback(mock_update, mock_context)

    mock_update.callback_query.answer.assert_called()


@pytest.mark.asyncio
async def test_voice_send_callback():
    """voice:send callback sends transcript to Claude."""
    from src.bot.callbacks import handle_callback

    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "voice:send"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.effective_user.id = 12345

    context = MagicMock()
    context.user_data = {
        "pending_voice_text": "Hello Claude",
        "current_session": MagicMock(),
    }
    context.bot_data = {
        "config": MagicMock(
            streaming=MagicMock(edit_throttle_ms=1000, chunk_size=3800)
        )
    }

    # Mock _execute_claude_prompt to avoid full execution
    with patch("src.bot.callbacks._execute_claude_prompt", new_callable=AsyncMock) as mock_execute:
        await handle_callback(update, context)

        # Should have cleared pending text
        assert "pending_voice_text" not in context.user_data

        # Should call Claude with transcript
        mock_execute.assert_called_once()


@pytest.mark.asyncio
async def test_voice_cancel_callback():
    """voice:cancel callback clears pending transcript."""
    from src.bot.callbacks import handle_callback

    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "voice:cancel"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = MagicMock()
    context.user_data = {"pending_voice_text": "Hello Claude"}

    await handle_callback(update, context)

    # Should have cleared pending text
    assert "pending_voice_text" not in context.user_data

    # Should show cancelled message
    update.callback_query.edit_message_text.assert_called()
    call_args = str(update.callback_query.edit_message_text.call_args)
    assert "cancelled" in call_args.lower()


@pytest.mark.asyncio
async def test_voice_edit_callback():
    """voice:edit callback prompts user to type correction."""
    from src.bot.callbacks import handle_callback

    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "voice:edit"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    context = MagicMock()
    context.user_data = {"pending_voice_text": "Hello Claude"}

    await handle_callback(update, context)

    # Should set editing flag
    assert context.user_data.get("editing_voice_text") is True

    # Should show edit prompt
    update.callback_query.edit_message_text.assert_called()
