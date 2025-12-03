"""Test persistence configuration."""


def test_persistence_path_in_config():
    """Config includes persistence file path."""
    from src.config.settings import Config

    config = Config()
    assert hasattr(config, "persistence_path")
    assert config.persistence_path.endswith(".pickle")


def test_application_has_persistence(tmp_path):
    """Application is configured with PicklePersistence."""
    from src.config.settings import Config
    from src.bot.application import create_application

    config = Config(
        telegram_token="test:token",
        persistence_path=str(tmp_path / "test.pickle"),
    )

    app = create_application(config)

    assert app.persistence is not None
    assert "PicklePersistence" in type(app.persistence).__name__


async def test_session_id_stored_in_user_data():
    """Session ID is stored in user_data for persistence."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.bot.callbacks import handle_callback

    # Mock update and context
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "project:myapp"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.get_bot = MagicMock(return_value=MagicMock())
    update.effective_user.id = 12345

    context = MagicMock()
    context.user_data = {}
    context.bot_data = {
        "config": MagicMock(projects={"myapp": "/home/user/myapp"}),
        "command_registry": MagicMock(refresh=AsyncMock(return_value=5)),
    }

    mock_session = MagicMock(id="session123", claude_session_id=None)
    mock_repo = MagicMock()
    mock_repo.create_session = AsyncMock(return_value=mock_session)

    with patch("src.bot.callbacks.get_session") as mock_get_session, \
         patch("src.bot.callbacks.SessionRepository", return_value=mock_repo):
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        await handle_callback(update, context)

    # Verify session ID stored in user_data
    assert "current_session_id" in context.user_data
    assert context.user_data["current_session_id"] == "session123"
    # Also verify project_path is stored
    assert "current_project_path" in context.user_data
    assert context.user_data["current_project_path"] == "/home/user/myapp"
