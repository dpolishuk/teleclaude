"""Claude SDK client wrapper."""
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from src.config.settings import Config
from src.storage.models import Session


@dataclass
class ClaudeOptions:
    """Options for Claude SDK (placeholder until SDK available)."""

    max_turns: int = 50
    permission_mode: str = "acceptEdits"
    max_budget_usd: float = 10.0
    cwd: Optional[str] = None
    resume: Optional[str] = None
    allowed_tools: list[str] = None
    hooks: dict = None

    def __post_init__(self):
        if self.allowed_tools is None:
            self.allowed_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
        if self.hooks is None:
            self.hooks = {}


class TeleClaudeClient:
    """Wrapper for Claude SDK client."""

    def __init__(self, config: Config, session: Session):
        """Initialize with configuration and session."""
        self.config = config
        self.session = session
        self._client = None

    def _build_options(self) -> ClaudeOptions:
        """Build Claude SDK options."""
        options = ClaudeOptions(
            max_turns=self.config.claude.max_turns,
            permission_mode=self.config.claude.permission_mode,
            max_budget_usd=self.config.claude.max_budget_usd,
            cwd=self.session.current_directory,
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        )

        if self.session.claude_session_id:
            options.resume = self.session.claude_session_id

        return options

    async def __aenter__(self) -> "TeleClaudeClient":
        """Enter async context - connect to Claude."""
        # TODO: Replace with actual SDK when available
        # from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
        #
        # options = ClaudeAgentOptions(
        #     **self._build_options().__dict__
        # )
        # self._client = ClaudeSDKClient(options=options)
        # await self._client.connect()
        return self

    async def __aexit__(self, *args) -> None:
        """Exit async context - disconnect."""
        if self._client:
            # await self._client.disconnect()
            pass

    async def query(self, prompt: str) -> AsyncIterator:
        """Send prompt and yield messages."""
        # TODO: Replace with actual SDK implementation
        # await self._client.query(prompt)
        # async for message in self._client.receive_messages():
        #     yield message

        # Placeholder implementation for testing
        yield {
            "type": "assistant",
            "content": [{"type": "text", "text": f"Response to: {prompt}"}],
        }

    def get_session_id(self) -> Optional[str]:
        """Get Claude session ID if available."""
        return self.session.claude_session_id
