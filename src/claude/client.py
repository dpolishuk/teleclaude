"""Claude SDK client wrapper."""
from typing import Any, Optional

from telegram import Bot

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
)

from src.config.settings import Config
from src.storage.models import Session
from src.claude.hooks import create_approval_hooks
from src.claude.permissions import can_use_tool_callback, get_permission_manager


def create_claude_options(
    config: Config,
    session: Session | None = None,
    hooks: dict | None = None,
    mcp_servers: dict[str, dict[str, Any]] | None = None,
    bot: Bot | None = None,
    chat_id: int | None = None,
    resume_mode: str | None = None,
    model: str | None = None,
) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions from config and session.

    Args:
        config: Application configuration.
        session: Current user session (optional for sessionless commands).
        hooks: Optional custom hooks dict. If None, uses default dangerous command hooks.
        mcp_servers: Optional MCP servers dict. If None and config.mcp.auto_load is True,
                     loads from config.
        bot: Telegram bot instance for permission prompts.
        chat_id: Telegram chat ID for permission prompts.
        resume_mode: Resume mode - "fork" for fork_session, "continue" for resume.
        model: Claude model to use (sonnet, opus, haiku, opusplan).

    Returns:
        Configured ClaudeAgentOptions.
    """
    # Build hooks with HookMatcher format (includes Bash dangerous patterns + MCP approval)
    if hooks is None:
        hooks = create_approval_hooks()

    # Determine working directory
    if session:
        cwd = session.project_path
    else:
        # Sessionless mode - use /tmp for safety
        cwd = "/tmp"

    # Handle MCP servers
    if mcp_servers is None and config.mcp.enabled and config.mcp.auto_load:
        mcp_servers = config.mcp.get_enabled_servers()
        # Only pass if there are servers
        if not mcp_servers:
            mcp_servers = None

    # Set up permission manager with Telegram context for interactive permission prompts
    if bot and chat_id:
        permission_manager = get_permission_manager()
        permission_manager.set_telegram_context(bot, chat_id)

    # Use can_use_tool callback for interactive permission prompts
    # This shows Telegram buttons (Accept/Accept Always/Deny) for each tool request
    options = ClaudeAgentOptions(
        permission_mode=config.claude.permission_mode,
        max_turns=config.claude.max_turns,
        max_budget_usd=config.claude.max_budget_usd,
        cwd=cwd,
        hooks=hooks,
        mcp_servers=mcp_servers,
        can_use_tool=can_use_tool_callback,
        model=model,
    )

    # Resume from previous Claude session if available
    import logging
    logger = logging.getLogger(__name__)

    if session and session.claude_session_id:
        # Use resume_mode to determine which parameter to use
        # Default to resume (continue) for seamless conversation continuity
        if resume_mode == "fork":
            logger.info(f"Using fork_session: {session.claude_session_id}")
            options.fork_session = session.claude_session_id
        else:
            # Default to resume - identical to Claude Code behavior
            logger.info(f"Using resume: {session.claude_session_id}")
            options.resume = session.claude_session_id
    else:
        logger.info(f"No claude_session_id to resume (session={session is not None}, claude_session_id={session.claude_session_id if session else None})")

    return options


class TeleClaudeClient:
    """Wrapper for Claude SDK client with Telegram integration."""

    def __init__(
        self,
        config: Config,
        session: Session | None = None,
        hooks: dict | None = None,
        mcp_servers: dict[str, dict[str, Any]] | None = None,
        bot: Bot | None = None,
        chat_id: int | None = None,
        resume_mode: str | None = None,
        model: str | None = None,
    ):
        """Initialize with configuration and session.

        Args:
            config: Application configuration.
            session: Current user session (optional for sessionless commands).
            hooks: Optional custom hooks for tool approval.
            mcp_servers: Optional MCP servers dict. If None, uses config.mcp settings.
            bot: Telegram bot instance for permission prompts.
            chat_id: Telegram chat ID for permission prompts.
            resume_mode: Resume mode - "fork" for fork_session, "continue" for resume.
            model: Claude model to use (sonnet, opus, haiku, opusplan).
        """
        self.config = config
        self.session = session
        self.hooks = hooks
        self.mcp_servers = mcp_servers
        self.bot = bot
        self.chat_id = chat_id
        self.resume_mode = resume_mode
        self.model = model
        self._client: Optional[ClaudeSDKClient] = None
        self._options: Optional[ClaudeAgentOptions] = None

    async def __aenter__(self) -> "TeleClaudeClient":
        """Enter async context - create SDK client."""
        self._options = create_claude_options(
            self.config,
            self.session,
            self.hooks,
            self.mcp_servers,
            self.bot,
            self.chat_id,
            self.resume_mode,
            self.model,
        )
        self._client = ClaudeSDKClient(options=self._options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args) -> None:
        """Exit async context - cleanup."""
        if self._client:
            await self._client.__aexit__(*args)

    async def query(self, prompt: str):
        """Send prompt to Claude.

        Args:
            prompt: User's message to Claude.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        await self._client.query(prompt)

    def receive_response(self):
        """Get async iterator for response messages.

        Returns:
            AsyncIterator of SDK messages.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client.receive_response()

    async def interrupt(self):
        """Interrupt current operation."""
        if self._client:
            await self._client.interrupt()

    @property
    def client(self) -> Optional[ClaudeSDKClient]:
        """Access underlying SDK client."""
        return self._client
