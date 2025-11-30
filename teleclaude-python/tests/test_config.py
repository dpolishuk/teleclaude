"""Test configuration loading."""
import os
import pytest
from pathlib import Path
from src.config.settings import Config, load_config


@pytest.fixture
def config_file(tmp_path):
    """Create a temporary config file."""
    config_content = """
allowed_users:
  - 12345678
  - 87654321

projects:
  myapp: /home/user/myapp

sandbox:
  allowed_paths:
    - /home/user

claude:
  max_turns: 25
  permission_mode: "acceptEdits"
  max_budget_usd: 5.0

approval:
  dangerous_commands:
    - "rm -rf"
  require_approval_for:
    - "Bash"

streaming:
  edit_throttle_ms: 500
  chunk_size: 4000

database:
  path: /tmp/test.db
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)
    return config_path


def test_load_config(config_file):
    """Config loads from YAML file."""
    config = load_config(config_file)

    assert len(config.allowed_users) == 2
    assert 12345678 in config.allowed_users
    assert config.projects["myapp"] == "/home/user/myapp"
    assert config.claude.max_turns == 25
    assert config.claude.max_budget_usd == 5.0
    assert config.streaming.chunk_size == 4000


def test_load_config_defaults(tmp_path):
    """Config applies defaults for missing values."""
    config_content = """
allowed_users:
  - 12345678
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)

    config = load_config(config_path)

    assert config.claude.max_turns == 50
    assert config.claude.permission_mode == "acceptEdits"
    assert config.streaming.edit_throttle_ms == 1000
    assert config.streaming.chunk_size == 3800


def test_is_user_allowed():
    """is_user_allowed checks whitelist."""
    config = Config(allowed_users=[12345678, 87654321])

    assert config.is_user_allowed(12345678) is True
    assert config.is_user_allowed(99999999) is False


def test_config_expands_home_path(tmp_path):
    """Database path expands ~ to home directory."""
    config_content = """
allowed_users:
  - 12345678

database:
  path: ~/.teleclaude/test.db
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)

    config = load_config(config_path)

    assert "~" not in config.database.path
    assert config.database.path.startswith(str(Path.home()))
