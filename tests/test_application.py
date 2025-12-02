"""Test bot application setup."""
import pytest
from unittest.mock import MagicMock, patch
from src.bot.application import create_application
from src.config.settings import Config


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return Config(
        allowed_users=[12345678],
        telegram_token="test_token",
    )


def test_create_application_returns_application(mock_config):
    """create_application returns Application instance."""
    with patch("src.bot.application.Application") as MockApp:
        mock_builder = MagicMock()
        MockApp.builder.return_value = mock_builder
        mock_builder.token.return_value = mock_builder
        mock_builder.post_init.return_value = mock_builder
        mock_builder.concurrent_updates.return_value = mock_builder
        mock_builder.build.return_value = MagicMock()

        app = create_application(mock_config)

        MockApp.builder.assert_called_once()
        mock_builder.token.assert_called_once_with("test_token")
        mock_builder.build.assert_called_once()


def test_create_application_stores_config(mock_config):
    """create_application stores config in bot_data."""
    with patch("src.bot.application.Application") as MockApp:
        mock_app = MagicMock()
        mock_app.bot_data = {}
        mock_builder = MagicMock()
        MockApp.builder.return_value = mock_builder
        mock_builder.token.return_value = mock_builder
        mock_builder.post_init.return_value = mock_builder
        mock_builder.concurrent_updates.return_value = mock_builder
        mock_builder.build.return_value = mock_app

        create_application(mock_config)

        assert mock_app.bot_data["config"] == mock_config


def test_create_application_has_command_registry(mock_config):
    """Application has CommandRegistry in bot_data."""
    from src.commands import CommandRegistry

    with patch("src.bot.application.Application") as MockApp:
        mock_builder = MagicMock()
        mock_app = MagicMock()
        mock_builder.token.return_value = mock_builder
        mock_builder.post_init.return_value = mock_builder
        mock_builder.concurrent_updates.return_value = mock_builder
        mock_builder.build.return_value = mock_app
        mock_app.bot_data = {}
        MockApp.builder.return_value = mock_builder

        app = create_application(mock_config)

        assert "command_registry" in app.bot_data
        assert isinstance(app.bot_data["command_registry"], CommandRegistry)


def test_voice_handlers_registered_when_enabled():
    """Voice handlers are registered when voice is enabled."""
    from src.bot.application import create_application
    from src.config.settings import Config, VoiceConfig

    config = Config(
        telegram_token="test-token",
        voice=VoiceConfig(enabled=True, openai_api_key="sk-test"),
    )

    app = create_application(config)

    # Check that voice and audio handlers exist
    from telegram.ext import MessageHandler

    handler_filters = [
        str(h.filters) for h in app.handlers[0]
        if isinstance(h, MessageHandler)
    ]

    # Should have VOICE or AUDIO filter
    voice_found = any('VOICE' in f for f in handler_filters)
    audio_found = any('AUDIO' in f for f in handler_filters)

    assert voice_found or audio_found, "Voice/Audio handlers not registered"


def test_voice_handlers_not_registered_when_disabled():
    """Voice handlers are not registered when voice is disabled."""
    from src.bot.application import create_application
    from src.config.settings import Config, VoiceConfig

    config = Config(
        telegram_token="test-token",
        voice=VoiceConfig(enabled=False),
    )

    app = create_application(config)

    # Voice handlers should not exist
    from telegram.ext import MessageHandler

    handler_filters = [
        str(h.filters) for h in app.handlers[0]
        if isinstance(h, MessageHandler)
    ]

    voice_found = any('VOICE' in f for f in handler_filters)
    assert not voice_found, "Voice handlers registered when disabled"
