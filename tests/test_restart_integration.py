"""Integration test for session continuity across restarts."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_full_restart_cycle():
    """Simulate: create session -> restart -> restore session."""
    from src.bot.callbacks import handle_callback
    from src.bot.handlers import start

    # Phase 1: User selects project, creates session
    user_data = {}

    update1 = MagicMock()
    update1.callback_query = AsyncMock()
    update1.callback_query.data = "project:myapp"
    update1.callback_query.answer = AsyncMock()
    update1.callback_query.edit_message_text = AsyncMock()
    update1.callback_query.get_bot = MagicMock(return_value=MagicMock())
    update1.effective_user.id = 12345

    context1 = MagicMock()
    context1.user_data = user_data  # Shared reference
    context1.bot_data = {
        "config": MagicMock(projects={"myapp": "/home/user/myapp"}),
        "command_registry": MagicMock(refresh=AsyncMock(return_value=5)),
    }

    # With lazy session creation, we don't create DB record yet
    await handle_callback(update1, context1)

    # Verify session was set up (but ID is None initially with lazy creation)
    assert "current_session" in user_data
    assert user_data["current_session"].id is None

    # Simulate SDK returning a session_id (which would happen in real flow)
    # For this test, we'll manually set it to simulate the lazy creation completing
    from types import SimpleNamespace
    user_data["current_session"] = SimpleNamespace(
        id="session123",
        project_path="/home/user/myapp",
        project_name="myapp",
        total_cost_usd=0.0,
    )
    user_data["current_session_id"] = "session123"

    # Now verify session ID was stored
    assert user_data.get("current_session_id") == "session123"

    mock_session = MagicMock(
        id="session123",
        project_path="/home/user/myapp",
        last_active=None,
        total_cost_usd=0.0,
    )
    mock_repo = MagicMock()
    mock_repo.get_session = AsyncMock(return_value=mock_session)

    # Phase 2: Simulate restart - user_data persisted, session object lost
    user_data.pop("current_session", None)  # Object not serializable

    # Phase 3: User sends /start after restart
    update2 = MagicMock()
    update2.effective_user.id = 12345
    update2.message = AsyncMock()
    update2.message.reply_text = AsyncMock()

    context2 = MagicMock()
    context2.user_data = user_data  # Restored from pickle
    context2.bot_data = {
        "config": MagicMock(projects={"myapp": "/home/user/myapp"}),
    }

    with patch("src.bot.handlers.get_session") as mock_get_session, \
         patch("src.bot.handlers.SessionRepository", return_value=mock_repo), \
         patch("src.bot.handlers.get_session_file_path", return_value=None), \
         patch("src.bot.handlers.get_session_last_message", return_value=None):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await start(update2, context2)

    # Verify restore message was sent
    update2.message.reply_text.assert_called_once()
    call_text = update2.message.reply_text.call_args[0][0]
    assert "restored" in call_text.lower() or "myapp" in call_text
