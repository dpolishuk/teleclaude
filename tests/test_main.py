"""Test main entry point."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_main_requires_token(tmp_path, monkeypatch):
    """main exits if TELEGRAM_BOT_TOKEN not set."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    # Import after clearing env
    from src.main import main
    import asyncio

    # Should not raise, just log error and return
    asyncio.run(main())


@pytest.mark.asyncio
async def test_main_loads_config(tmp_path, monkeypatch):
    """main loads configuration."""
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
            mock_app.run_polling = AsyncMock()
            mock_create.return_value = mock_app

            with patch("src.main.init_database", new_callable=AsyncMock):
                from src.main import main
                await main()

                mock_create.assert_called_once()
