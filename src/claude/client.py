"""Claude SDK client wrapper."""
from typing import Optional

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
)

from src.config.settings import Config
from src.storage.models import Session
from src.claude.hooks import check_dangerous_command


def create_claude_options(
    config: Config,
    session: Session,
    hooks: dict | None = None,
) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions from config and session.

    Args:
        config: Application configuration.
        session: Current user session.
        hooks: Optional custom hooks dict. If None, uses default dangerous command hooks.

    Returns:
        Configured ClaudeAgentOptions.
    """
    # Build hooks with HookMatcher format
    if hooks is None:
        hooks = {
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[check_dangerous_command]),
            ],
        }

    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        permission_mode=config.claude.permission_mode,
        max_turns=config.claude.max_turns,
        max_budget_usd=config.claude.max_budget_usd,
        cwd=session.current_directory or session.project_path,
        hooks=hooks,
    )

    # Resume from previous Claude session if available
    if session.claude_session_id:
        options.fork_session = session.claude_session_id

    return options


class TeleClaudeClient:
    """Wrapper for Claude SDK client with Telegram integration."""

    def __init__(
        self,
        config: Config,
        session: Session,
        hooks: dict | None = None,
    ):
        """Initialize with configuration and session.

        Args:
            config: Application configuration.
            session: Current user session.
            hooks: Optional custom hooks for tool approval.
        """
        self.config = config
        self.session = session
        self.hooks = hooks
        self._client: Optional[ClaudeSDKClient] = None
        self._options: Optional[ClaudeAgentOptions] = None

    async def __aenter__(self) -> "TeleClaudeClient":
        """Enter async context - create SDK client."""
        self._options = create_claude_options(
            self.config, self.session, self.hooks
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
