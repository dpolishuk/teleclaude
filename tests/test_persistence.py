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
