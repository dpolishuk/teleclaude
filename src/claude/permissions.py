"""Tool permission handling with Telegram UI integration."""
import asyncio
import html
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from claude_agent_sdk import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
    PermissionUpdate,
)

logger = logging.getLogger(__name__)


@dataclass
class PendingPermission:
    """A pending permission request waiting for user input."""

    request_id: str
    tool_name: str
    tool_input: dict[str, Any]
    context: ToolPermissionContext
    event: asyncio.Event = field(default_factory=asyncio.Event)
    result: PermissionResultAllow | PermissionResultDeny | None = None
    always_allow: bool = False  # Whether to add to always-allowed list


class PermissionManager:
    """Manages tool permission requests with Telegram UI.

    This class:
    1. Stores pending permission requests
    2. Shows inline keyboard buttons to users
    3. Waits for user response
    4. Returns the permission decision to the SDK
    """

    def __init__(self):
        self._pending: dict[str, PendingPermission] = {}
        self._always_allowed: set[str] = set()  # Tool names always allowed
        self._bot: Bot | None = None
        self._chat_id: int | None = None

    def set_telegram_context(self, bot: Bot, chat_id: int) -> None:
        """Set the Telegram bot and chat for permission prompts."""
        self._bot = bot
        self._chat_id = chat_id

    def is_always_allowed(self, tool_name: str) -> bool:
        """Check if tool is in always-allowed list."""
        return tool_name in self._always_allowed

    def add_always_allowed(self, tool_name: str) -> None:
        """Add tool to always-allowed list."""
        self._always_allowed.add(tool_name)
        logger.info(f"Tool {tool_name} added to always-allowed list")

    async def request_permission(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: ToolPermissionContext,
    ) -> PermissionResultAllow | PermissionResultDeny:
        """Request permission for a tool use.

        This is called by the SDK's can_use_tool callback.
        Shows Telegram buttons and waits for user response.
        """
        logger.info(f"Permission requested for tool: {tool_name}")

        # Check always-allowed list first
        if tool_name in self._always_allowed:
            logger.info(f"Tool {tool_name} is always allowed - auto-approving")
            return PermissionResultAllow()

        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]

        # Create pending permission
        pending = PendingPermission(
            request_id=request_id,
            tool_name=tool_name,
            tool_input=tool_input,
            context=context,
        )
        self._pending[request_id] = pending
        logger.info(f"Created pending permission: {request_id} for {tool_name}")

        # Show permission prompt in Telegram
        if self._bot and self._chat_id:
            await self._show_permission_prompt(pending)
        else:
            logger.warning("No Telegram context set, auto-denying permission")
            return PermissionResultDeny(message="No UI available for permission prompt")

        # Wait for user response (with timeout)
        try:
            await asyncio.wait_for(pending.event.wait(), timeout=300.0)  # 5 min timeout
        except asyncio.TimeoutError:
            logger.warning(f"Permission request {request_id} timed out")
            self._pending.pop(request_id, None)
            return PermissionResultDeny(message="Permission request timed out")

        # Get result and cleanup
        self._pending.pop(request_id, None)

        if pending.result:
            # Handle "Accept Always" - add to always-allowed list
            if pending.always_allow and isinstance(pending.result, PermissionResultAllow):
                self._always_allowed.add(tool_name)

            return pending.result

        return PermissionResultDeny(message="Permission denied")

    async def _show_permission_prompt(self, pending: PendingPermission) -> None:
        """Show permission prompt with inline keyboard."""
        tool_name = pending.tool_name
        tool_input = pending.tool_input
        request_id = pending.request_id

        # Format tool input for display
        input_lines = []
        for key, value in tool_input.items():
            str_val = str(value)
            if len(str_val) > 100:
                str_val = str_val[:100] + "..."
            input_lines.append(f"  <code>{html.escape(key)}</code>: {html.escape(str_val)}")

        input_text = "\n".join(input_lines) if input_lines else "  (no parameters)"

        message = (
            f"🔐 <b>Permission Request</b>\n\n"
            f"Tool: <code>{html.escape(tool_name)}</code>\n"
            f"Input:\n{input_text}\n\n"
            f"Allow this tool to execute?"
        )

        # Create inline keyboard with Accept, Accept Always, Deny buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"perm_allow:{request_id}"),
                InlineKeyboardButton("✅ Always", callback_data=f"perm_always:{request_id}"),
            ],
            [
                InlineKeyboardButton("❌ Deny", callback_data=f"perm_deny:{request_id}"),
            ],
        ])

        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.error(f"Failed to send permission prompt: {e}")
            # Set result to deny if we can't show the prompt
            pending.result = PermissionResultDeny(message=f"Failed to show prompt: {e}")
            pending.event.set()

    def handle_permission_response(
        self, request_id: str, action: str
    ) -> tuple[bool, str]:
        """Handle user's permission response from callback.

        Args:
            request_id: The permission request ID.
            action: "allow", "always", or "deny".

        Returns:
            Tuple of (success, message).
        """
        logger.info(
            f"handle_permission_response: request_id={request_id}, action={action}, "
            f"pending_count={len(self._pending)}, pending_ids={list(self._pending.keys())}"
        )
        pending = self._pending.get(request_id)
        if not pending:
            logger.warning(f"Permission request {request_id} not found in pending dict")
            return False, "Permission request not found or expired"

        if action == "allow":
            pending.result = PermissionResultAllow()
            pending.always_allow = False
            pending.event.set()
            logger.info(f"Set event for {request_id} - allow")
            return True, f"✅ Allowed: {pending.tool_name}"

        elif action == "always":
            pending.result = PermissionResultAllow()
            pending.always_allow = True
            pending.event.set()
            logger.info(f"Set event for {request_id} - always")
            return True, f"✅ Always allowed: {pending.tool_name}"

        elif action == "deny":
            pending.result = PermissionResultDeny(message="User denied permission")
            pending.event.set()
            logger.info(f"Set event for {request_id} - deny")
            return True, f"❌ Denied: {pending.tool_name}"

        return False, f"Unknown action: {action}"

    def get_pending_count(self) -> int:
        """Get number of pending permission requests."""
        return len(self._pending)

    def cancel_all(self) -> int:
        """Cancel all pending permissions. Returns count cancelled."""
        count = len(self._pending)
        for pending in self._pending.values():
            pending.result = PermissionResultDeny(message="Operation cancelled")
            pending.event.set()
        self._pending.clear()
        return count


# Global permission manager instance
_permission_manager: PermissionManager | None = None


def get_permission_manager() -> PermissionManager:
    """Get or create global permission manager."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager


async def can_use_tool_callback(
    tool_name: str,
    tool_input: dict[str, Any],
    context: ToolPermissionContext,
) -> PermissionResultAllow | PermissionResultDeny:
    """SDK callback for tool permission requests.

    This is passed to ClaudeAgentOptions.can_use_tool.
    """
    manager = get_permission_manager()
    return await manager.request_permission(tool_name, tool_input, context)
