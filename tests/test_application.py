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
        MockApp.builder.return_value.token.return_value.build.return_value = mock_app

        create_application(mock_config)

        assert mock_app.bot_data["config"] == mock_config
