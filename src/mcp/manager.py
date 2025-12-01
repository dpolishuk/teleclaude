"""MCP server manager for runtime control."""
import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx

from src.config.settings import MCPConfig, MCPServerConfig, load_mcp_config

logger = logging.getLogger(__name__)


class ServerStatus(Enum):
    """MCP server connection status."""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ServerInfo:
    """Runtime information about an MCP server."""
    name: str
    config: MCPServerConfig
    status: ServerStatus = ServerStatus.UNKNOWN
    error: str | None = None
    tools: list[str] | None = None


class MCPManager:
    """Manages MCP server lifecycle and runtime state."""

    def __init__(self, mcp_config: MCPConfig):
        """Initialize with MCP configuration.

        Args:
            mcp_config: MCP configuration from settings.
        """
        self._config = mcp_config
        self._server_info: dict[str, ServerInfo] = {}

        # Initialize server info from config
        for name, server_config in mcp_config.servers.items():
            self._server_info[name] = ServerInfo(
                name=name,
                config=server_config,
                status=ServerStatus.DISABLED if not server_config.enabled else ServerStatus.UNKNOWN,
            )

    @property
    def config(self) -> MCPConfig:
        """Get current MCP configuration."""
        return self._config

    def list_servers(self) -> list[ServerInfo]:
        """List all configured MCP servers with status.

        Returns:
            List of ServerInfo for all servers.
        """
        return list(self._server_info.values())

    def get_server(self, name: str) -> ServerInfo | None:
        """Get info for a specific server.

        Args:
            name: Server name.

        Returns:
            ServerInfo or None if not found.
        """
        return self._server_info.get(name)

    def enable_server(self, name: str) -> bool:
        """Enable an MCP server.

        Args:
            name: Server name.

        Returns:
            True if successful, False if server not found.
        """
        if name not in self._server_info:
            return False

        self._server_info[name].config.enabled = True
        self._server_info[name].status = ServerStatus.UNKNOWN
        self._config.servers[name].enabled = True
        logger.info(f"Enabled MCP server: {name}")
        return True

    def disable_server(self, name: str) -> bool:
        """Disable an MCP server.

        Args:
            name: Server name.

        Returns:
            True if successful, False if server not found.
        """
        if name not in self._server_info:
            return False

        self._server_info[name].config.enabled = False
        self._server_info[name].status = ServerStatus.DISABLED
        self._config.servers[name].enabled = False
        logger.info(f"Disabled MCP server: {name}")
        return True

    async def test_server(self, name: str) -> ServerInfo:
        """Test connection to an MCP server.

        Args:
            name: Server name.

        Returns:
            Updated ServerInfo with status.
        """
        if name not in self._server_info:
            return ServerInfo(
                name=name,
                config=MCPServerConfig(name=name, type="unknown"),
                status=ServerStatus.ERROR,
                error="Server not found",
            )

        info = self._server_info[name]
        config = info.config

        if not config.enabled:
            info.status = ServerStatus.DISABLED
            return info

        if config.type == "http":
            info = await self._test_http_server(info)
        elif config.type == "stdio":
            info = await self._test_stdio_server(info)
        else:
            info.status = ServerStatus.ERROR
            info.error = f"Unknown server type: {config.type}"

        self._server_info[name] = info
        return info

    async def test_all_servers(self) -> list[ServerInfo]:
        """Test all configured servers concurrently.

        Returns:
            List of ServerInfo with updated statuses.
        """
        tasks = [self.test_server(name) for name in self._server_info]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        updated = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error testing server: {result}")
            elif isinstance(result, ServerInfo):
                updated.append(result)

        return updated

    async def _test_http_server(self, info: ServerInfo) -> ServerInfo:
        """Test HTTP-based MCP server connection."""
        config = info.config
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try a simple request to check if server is reachable
                headers = config.headers.copy() if config.headers else {}
                response = await client.get(
                    config.url.rstrip("/"),
                    headers=headers,
                    follow_redirects=True,
                )
                # MCP servers typically return 200 or 405 (method not allowed for GET)
                if response.status_code in (200, 405, 400):
                    info.status = ServerStatus.ONLINE
                    info.error = None
                else:
                    info.status = ServerStatus.ERROR
                    info.error = f"HTTP {response.status_code}"

        except httpx.ConnectError:
            info.status = ServerStatus.OFFLINE
            info.error = "Connection refused"
        except httpx.TimeoutException:
            info.status = ServerStatus.OFFLINE
            info.error = "Connection timeout"
        except Exception as e:
            info.status = ServerStatus.ERROR
            info.error = str(e)

        return info

    async def _test_stdio_server(self, info: ServerInfo) -> ServerInfo:
        """Test stdio-based MCP server (check if command exists)."""
        config = info.config
        try:
            # Check if command exists using 'which'
            proc = await asyncio.create_subprocess_exec(
                "which", config.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)

            if proc.returncode == 0:
                info.status = ServerStatus.ONLINE
                info.error = None
            else:
                info.status = ServerStatus.OFFLINE
                info.error = f"Command not found: {config.command}"

        except asyncio.TimeoutError:
            info.status = ServerStatus.ERROR
            info.error = "Timeout checking command"
        except Exception as e:
            info.status = ServerStatus.ERROR
            info.error = str(e)

        return info

    def reload_config(self, mcp_path: str | None = None) -> int:
        """Reload MCP configuration from file.

        Args:
            mcp_path: Optional path to .mcp.json file.

        Returns:
            Number of servers loaded.
        """
        from pathlib import Path

        new_config = load_mcp_config(Path(mcp_path) if mcp_path else None)

        # Preserve enabled/disabled state for existing servers
        for name, server in new_config.servers.items():
            if name in self._config.servers:
                server.enabled = self._config.servers[name].enabled

        self._config = new_config

        # Update server info
        self._server_info.clear()
        for name, server_config in new_config.servers.items():
            self._server_info[name] = ServerInfo(
                name=name,
                config=server_config,
                status=ServerStatus.DISABLED if not server_config.enabled else ServerStatus.UNKNOWN,
            )

        logger.info(f"Reloaded MCP config: {len(new_config.servers)} servers")
        return len(new_config.servers)

    def get_enabled_servers_for_sdk(self) -> dict[str, dict[str, Any]] | None:
        """Get enabled servers in SDK format.

        Returns:
            Dict of server configs for ClaudeAgentOptions, or None if MCP disabled.
        """
        if not self._config.enabled:
            return None

        servers = self._config.get_enabled_servers()
        return servers if servers else None

    def format_status_message(self) -> str:
        """Format server status for display (HTML format).

        Returns:
            Formatted status message in HTML.
        """
        import html

        if not self._server_info:
            return "No MCP servers configured."

        lines = ["🔌 <b>MCP Servers</b>\n"]

        status_icons = {
            ServerStatus.ONLINE: "🟢",
            ServerStatus.OFFLINE: "🔴",
            ServerStatus.ERROR: "⚠️",
            ServerStatus.DISABLED: "⏸️",
            ServerStatus.UNKNOWN: "❓",
        }

        for name, info in self._server_info.items():
            icon = status_icons.get(info.status, "❓")
            type_badge = f"[{html.escape(info.config.type)}]"
            status_text = info.status.value

            line = f"{icon} <code>{html.escape(name)}</code> {type_badge} - {status_text}"
            if info.error:
                line += f"\n   └─ {html.escape(info.error)}"

            lines.append(line)

        config_path = html.escape(str(self._config.config_path or "none"))
        lines.append(f"\n📂 Config: <code>{config_path}</code>")
        lines.append(f"🔧 Master: {'enabled' if self._config.enabled else 'disabled'}")

        return "\n".join(lines)
