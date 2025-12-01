"""Command registry for storing and managing commands."""
import logging

from telegram import Bot, BotCommand

from .models import ClaudeCommand
from .discovery import scan_commands

logger = logging.getLogger(__name__)


class CommandRegistry:
    """Stores and manages Claude commands."""

    # Built-in TeleClaude commands (cannot be overridden)
    BUILTIN_COMMANDS = [
        ("start", "Start the bot"),
        ("new", "Start new session"),
        ("continue", "Resume last session"),
        ("sessions", "List all sessions"),
        ("switch", "Switch to session"),
        ("help", "Show help"),
        ("cancel", "Stop current operation"),
        ("cost", "Show usage costs"),
        ("cd", "Change directory"),
        ("ls", "List directory"),
        ("pwd", "Show current directory"),
        ("git", "Git operations"),
        ("export", "Export session"),
        ("refresh", "Rescan Claude commands"),
        ("mcp", "Manage MCP servers"),
    ]

    def __init__(self):
        self._commands: dict[str, ClaudeCommand] = {}

    @property
    def builtin_names(self) -> set[str]:
        """Get set of built-in command names."""
        return {name for name, _ in self.BUILTIN_COMMANDS}

    @property
    def commands(self) -> list[ClaudeCommand]:
        """Get all registered commands."""
        return list(self._commands.values())

    def get(self, name: str) -> ClaudeCommand | None:
        """Get command by name."""
        return self._commands.get(name)

    def substitute_args(self, cmd: ClaudeCommand, args: str) -> str:
        """Substitute arguments into command prompt.

        Handles both $ARGUMENTS (all args) and $1, $2, etc. (positional).
        If no placeholders exist and args are provided, appends them to prompt.

        Args:
            cmd: The command to substitute into.
            args: User-provided arguments string.

        Returns:
            Prompt with arguments substituted.
        """
        prompt = cmd.prompt
        has_placeholders = "$ARGUMENTS" in prompt or "$1" in prompt

        # Substitute $ARGUMENTS with full args string
        prompt = prompt.replace("$ARGUMENTS", args)

        # Substitute positional args $1, $2, etc.
        parts = args.split()
        for i, part in enumerate(parts, start=1):
            prompt = prompt.replace(f"${i}", part)

        # If no placeholders and args provided, append them
        if args and not has_placeholders:
            prompt = f"{prompt}\n\nARGUMENTS: {args}"

        return prompt

    async def refresh(self, bot: Bot, project_path: str | None = None) -> int:
        """Rescan commands and update Telegram menu.

        Args:
            bot: Telegram bot instance.
            project_path: Optional project directory.

        Returns:
            Number of Claude commands loaded.
        """
        # Scan directories
        discovered = scan_commands(project_path)

        # Filter out conflicts with built-in commands
        self._commands.clear()
        for cmd in discovered:
            if cmd.name in self.builtin_names:
                logger.warning(
                    f"Skipping command '{cmd.name}' - conflicts with built-in"
                )
                continue
            self._commands[cmd.name] = cmd

        # Build Telegram command list
        telegram_commands = [
            BotCommand(name, desc) for name, desc in self.BUILTIN_COMMANDS
        ]

        # Add Claude commands (respect Telegram's 100 command limit)
        remaining_slots = 100 - len(telegram_commands)
        claude_cmds = list(self._commands.values())[:remaining_slots]

        if len(self._commands) > remaining_slots:
            logger.warning(
                f"Too many commands ({len(self._commands)}), "
                f"truncated to {remaining_slots}"
            )

        for cmd in claude_cmds:
            telegram_commands.append(BotCommand(cmd.name, cmd.description))

        # Update Telegram menu
        await bot.set_my_commands(telegram_commands)

        return len(self._commands)
