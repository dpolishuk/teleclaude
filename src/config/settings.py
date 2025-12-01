"""Configuration settings."""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Single MCP server configuration."""

    name: str
    type: str  # "stdio" or "http"
    command: str | None = None  # for stdio
    url: str | None = None  # for http
    args: list[str] = field(default_factory=list)  # stdio args
    env: dict[str, str] = field(default_factory=dict)  # env vars
    headers: dict[str, str] = field(default_factory=dict)  # http headers
    enabled: bool = True  # runtime toggle

    def to_sdk_format(self) -> dict[str, Any]:
        """Convert to Claude SDK mcp_servers format."""
        if self.type == "stdio":
            return {
                "type": "stdio",
                "command": self.command,
                "args": self.args,
                "env": self.env,
            }
        else:  # http
            result = {
                "type": "http",
                "url": self.url,
            }
            if self.headers:
                result["headers"] = self.headers
            return result


@dataclass
class MCPConfig:
    """MCP servers configuration."""

    enabled: bool = True  # master toggle
    auto_load: bool = True  # auto-load on session start
    config_path: str = ""  # path to .mcp.json
    servers: dict[str, MCPServerConfig] = field(default_factory=dict)

    def get_enabled_servers(self) -> dict[str, dict[str, Any]]:
        """Get SDK-formatted dict of enabled servers."""
        if not self.enabled:
            return {}
        return {
            name: server.to_sdk_format()
            for name, server in self.servers.items()
            if server.enabled
        }


@dataclass
class ClaudeConfig:
    """Claude SDK settings."""

    max_turns: int = 50
    permission_mode: str = "bypassPermissions"  # Allow all tools including MCP
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
    mcp: MCPConfig = field(default_factory=MCPConfig)
    telegram_token: str = ""

    def is_user_allowed(self, user_id: int) -> bool:
        """Check if user is in whitelist."""
        return user_id in self.allowed_users


def load_mcp_config(mcp_path: Path | None = None) -> MCPConfig:
    """Load MCP configuration from .mcp.json file.

    Searches in order:
    1. Explicit path if provided
    2. ~/.teleclaude/.mcp.json
    3. Project-specific .mcp.json (handled at session level)

    Args:
        mcp_path: Optional explicit path to .mcp.json

    Returns:
        MCPConfig with loaded servers.
    """
    search_paths = []

    if mcp_path:
        search_paths.append(Path(mcp_path))

    # Default locations
    search_paths.extend([
        Path.home() / ".teleclaude" / ".mcp.json",
        Path.home() / ".mcp.json",
        Path.cwd() / ".mcp.json",
    ])

    for config_path in search_paths:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)

                servers = {}
                mcp_servers = data.get("mcpServers", {})

                for name, server_data in mcp_servers.items():
                    server_type = server_data.get("type", "stdio")
                    servers[name] = MCPServerConfig(
                        name=name,
                        type=server_type,
                        command=server_data.get("command"),
                        url=server_data.get("url"),
                        args=server_data.get("args", []),
                        env=server_data.get("env", {}),
                        headers=server_data.get("headers", {}),
                        enabled=server_data.get("enabled", True),
                    )

                logger.info(f"Loaded {len(servers)} MCP servers from {config_path}")
                return MCPConfig(
                    enabled=True,
                    auto_load=True,
                    config_path=str(config_path),
                    servers=servers,
                )

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse MCP config {config_path}: {e}")
                continue

    logger.info("No MCP configuration found")
    return MCPConfig()


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

    # Load MCP configuration
    mcp_data = data.get("mcp", {})
    mcp_path = mcp_data.get("config_path")
    config.mcp = load_mcp_config(Path(mcp_path) if mcp_path else None)

    # Apply overrides from YAML
    if "enabled" in mcp_data:
        config.mcp.enabled = mcp_data["enabled"]
    if "auto_load" in mcp_data:
        config.mcp.auto_load = mcp_data["auto_load"]

    # Parse nested configs
    if "sandbox" in data:
        config.sandbox = SandboxConfig(
            allowed_paths=data["sandbox"].get("allowed_paths", [])
        )

    if "claude" in data:
        config.claude = ClaudeConfig(
            max_turns=data["claude"].get("max_turns", 50),
            permission_mode=data["claude"].get("permission_mode", "bypassPermissions"),
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
