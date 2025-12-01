"""Test main entry point."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_main_requires_token(monkeypatch):
    """main exits if TELEGRAM_BOT_TOKEN not set."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    from src.main import main

    # Should not raise, just log error and return
    main()


@pytest.mark.asyncio
async def test_init_app_loads_config(tmp_path, monkeypatch):
    """init_app loads configuration and creates app."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")

    config_content = """
allowed_users:
  - 12345678
"""
    config_dir = tmp_path / ".teleclaude"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(config_content)

    with patch("src.main.Path.home", return_value=tmp_path):
        with patch("src.main.create_application") as mock_create:
            mock_app = MagicMock()
            mock_create.return_value = mock_app

            with patch("src.main.init_database", new_callable=AsyncMock):
                from src.main import init_app
                app = await init_app()

                mock_create.assert_called_once()
                assert app == mock_app
