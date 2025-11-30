"""Configuration settings."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ClaudeConfig:
    """Claude SDK settings."""

    max_turns: int = 50
    permission_mode: str = "acceptEdits"
    max_budget_usd: float = 10.0


@dataclass
class ApprovalConfig:
    """Approval workflow settings."""

    dangerous_commands: list[str] = field(default_factory=lambda: ["rm -rf", "sudo"])
    require_approval_for: list[str] = field(default_factory=lambda: ["Bash"])


@dataclass
class StreamingConfig:
    """Streaming behavior settings."""

    edit_throttle_ms: int = 1000
    chunk_size: int = 3800


@dataclass
class SandboxConfig:
    """Directory sandbox settings."""

    allowed_paths: list[str] = field(default_factory=list)


@dataclass
class DatabaseConfig:
    """Database settings."""

    path: str = "~/.teleclaude/teleclaude.db"


@dataclass
class Config:
    """Main configuration."""

    allowed_users: list[int] = field(default_factory=list)
    projects: dict[str, str] = field(default_factory=dict)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    approval: ApprovalConfig = field(default_factory=ApprovalConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    telegram_token: str = ""

    def is_user_allowed(self, user_id: int) -> bool:
        """Check if user is in whitelist."""
        return user_id in self.allowed_users


def load_config(path: Path | str | None = None) -> Config:
    """Load configuration from YAML file."""
    if path is None:
        path = Path.home() / ".teleclaude" / "config.yaml"
    else:
        path = Path(path)

    if not path.exists():
        return Config()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return _parse_config(data)


def _parse_config(data: dict[str, Any]) -> Config:
    """Parse config dictionary into Config object."""
    config = Config(
        allowed_users=data.get("allowed_users", []),
        projects=data.get("projects", {}),
    )

    # Parse nested configs
    if "sandbox" in data:
        config.sandbox = SandboxConfig(
            allowed_paths=data["sandbox"].get("allowed_paths", [])
        )

    if "claude" in data:
        config.claude = ClaudeConfig(
            max_turns=data["claude"].get("max_turns", 50),
            permission_mode=data["claude"].get("permission_mode", "acceptEdits"),
            max_budget_usd=data["claude"].get("max_budget_usd", 10.0),
        )

    if "approval" in data:
        config.approval = ApprovalConfig(
            dangerous_commands=data["approval"].get("dangerous_commands", []),
            require_approval_for=data["approval"].get("require_approval_for", []),
        )

    if "streaming" in data:
        config.streaming = StreamingConfig(
            edit_throttle_ms=data["streaming"].get("edit_throttle_ms", 1000),
            chunk_size=data["streaming"].get("chunk_size", 3800),
        )

    if "database" in data:
        db_path = data["database"].get("path", "~/.teleclaude/teleclaude.db")
        config.database = DatabaseConfig(path=str(Path(db_path).expanduser()))
    else:
        config.database = DatabaseConfig(
            path=str(Path("~/.teleclaude/teleclaude.db").expanduser())
        )

    return config
