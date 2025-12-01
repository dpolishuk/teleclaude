"""Handler for dynamic Claude commands."""
from telegram import Update
from telegram.ext import ContextTypes

from .handlers import _execute_claude_prompt


async def handle_claude_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle a Claude slash command.

    If command needs args, prompts user and stores pending state.
    Otherwise executes immediately.
    """
    registry = context.bot_data.get("command_registry")
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text(
            "❌ No active session. Use /new to start one."
        )
        return

    # Extract command name from message
    text = update.message.text
    parts = text.split(maxsplit=1)
    cmd_name = parts[0][1:]  # Remove leading /
    inline_args = parts[1] if len(parts) > 1 else ""

    cmd = registry.get(cmd_name)
    if not cmd:
        await update.message.reply_text(
            f"❌ Unknown command: /{cmd_name}"
        )
        return

    # Check if args are needed
    if cmd.needs_args and not inline_args:
        # Store pending command and prompt for args
        context.user_data["pending_command"] = {
            "name": cmd.name,
            "prompt": cmd.prompt,
        }
        await update.message.reply_text(
            f"🔧 /{cmd.name} requires input.\n\n"
            f"📝 {cmd.description}\n\n"
            "Enter your input or /cancel:"
        )
        return

    # Execute command
    prompt = registry.substitute_args(cmd, inline_args)
    await _execute_claude_prompt(update, context, prompt)
