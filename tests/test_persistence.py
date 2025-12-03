"""Test persistence configuration."""


def test_persistence_path_in_config():
    """Config includes persistence file path."""
    from src.config.settings import Config

    config = Config()
    assert hasattr(config, "persistence_path")
    assert config.persistence_path.endswith(".pickle")
