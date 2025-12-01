"""Telegram bot command handlers."""
from telegram import Update
from telegram.ext import ContextTypes

from src.utils.keyboards import project_keyboard, cancel_keyboard


HELP_TEXT = """
📱 *TeleClaude Commands*

*Session Management*
/new \\[project\\] \\- Start new session
/continue \\- Resume last session
/sessions \\- List all sessions
/switch <id> \\- Switch to session
/cancel \\- Stop current operation

*Navigation*
/cd <path> \\- Change directory
/ls \\[path\\] \\- List directory
/pwd \\- Show current directory

*Tools*
/git \\[cmd\\] \\- Git operations
/export \\[fmt\\] \\- Export session
/cost \\- Show usage costs

*Help*
/help \\- Show this message
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome to TeleClaude, {user.first_name}!\n\n"
        "I'm your mobile interface to Claude Code.\n\n"
        "Use /new to start a new session or /help for all commands."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")


async def new_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new command."""
    config = context.bot_data.get("config")

    if context.args:
        # Project name provided
        project_name = context.args[0]
        if project_name in config.projects:
            project_path = config.projects[project_name]
            await _create_session(update, context, project_path, project_name)
        else:
            await update.message.reply_text(
                f"❌ Project '{project_name}' not found.\n"
                "Use /new without arguments to see available projects."
            )
    else:
        # Show project selection keyboard
        keyboard = project_keyboard(config.projects)
        await update.message.reply_text(
            "📁 Select a project or choose Other to enter a path:",
            reply_markup=keyboard,
        )


async def continue_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /continue command."""
    session = context.user_data.get("current_session")

    if session:
        await update.message.reply_text(
            f"▶️ Continuing session in `{session.project_name or session.project_path}`\n\n"
            "Send a message to chat with Claude.",
            parse_mode="MarkdownV2",
        )
    else:
        await update.message.reply_text(
            "❌ No active session. Use /new to start one."
        )


async def list_sessions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /sessions command."""
    # TODO: Load sessions from database
    await update.message.reply_text(
        "📋 *Your Sessions*\n\nNo sessions found\\. Use /new to create one\\.",
        parse_mode="MarkdownV2",
    )


async def switch_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /switch command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /switch <session_id>\n\nUse /sessions to see available sessions."
        )
        return

    session_id = context.args[0]
    # TODO: Load session from database
    await update.message.reply_text(f"🔄 Switching to session {session_id}...")


async def show_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cost command."""
    session = context.user_data.get("current_session")

    if session:
        await update.message.reply_text(
            f"💰 *Session Cost*\n\n"
            f"Current session: ${session.total_cost_usd:.4f}",
            parse_mode="MarkdownV2",
        )
    else:
        await update.message.reply_text(
            "💰 *Usage Cost*\n\nNo active session\\.",
            parse_mode="MarkdownV2",
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command."""
    # TODO: Cancel running Claude operation
    await update.message.reply_text("🛑 Operation cancelled.")


async def cd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cd command."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text("❌ No active session. Use /new to start one.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /cd <path>")
        return

    new_path = context.args[0]
    # TODO: Validate path with sandbox
    session.current_directory = new_path
    await update.message.reply_text(f"📂 Changed to: `{new_path}`", parse_mode="MarkdownV2")


async def ls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ls command."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text("❌ No active session. Use /new to start one.")
        return

    path = context.args[0] if context.args else session.current_directory
    # TODO: List directory contents
    await update.message.reply_text(f"📁 Contents of `{path}`:\n\n(not implemented)", parse_mode="MarkdownV2")


async def pwd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pwd command."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text("❌ No active session. Use /new to start one.")
        return

    await update.message.reply_text(
        f"📂 Current directory: `{session.current_directory}`",
        parse_mode="MarkdownV2",
    )


async def git(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /git command."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text("❌ No active session. Use /new to start one.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /git <command>\n\n"
            "Examples:\n"
            "  /git status\n"
            "  /git log\n"
            "  /git diff"
        )
        return

    git_cmd = " ".join(context.args)
    # TODO: Execute git command
    await update.message.reply_text(f"🔀 Running: git {git_cmd}")


async def export_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /export command."""
    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text("❌ No active session. Use /new to start one.")
        return

    format_type = context.args[0] if context.args else "md"
    valid_formats = ["md", "html", "json"]

    if format_type not in valid_formats:
        await update.message.reply_text(
            f"❌ Invalid format. Use: {', '.join(valid_formats)}"
        )
        return

    # TODO: Export session
    await update.message.reply_text(f"📤 Exporting session as {format_type}...")


async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle regular text messages (Claude interaction)."""
    # Check if awaiting custom project path from /new -> Other
    if context.user_data.get("awaiting_path"):
        context.user_data["awaiting_path"] = False
        path = update.message.text.strip()
        await _create_session(update, context, path)
        return

    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text(
            "❌ No active session. Use /new to start one or /continue to resume."
        )
        return

    prompt = update.message.text

    # Send "thinking" message
    thinking_msg = await update.message.reply_text(
        "🤔 Thinking...",
        reply_markup=cancel_keyboard(),
    )

    # TODO: Send to Claude and stream response
    await thinking_msg.edit_text(
        f"Response to: {prompt}\n\n(Claude integration pending)"
    )


async def _create_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    project_path: str,
    project_name: str | None = None,
) -> None:
    """Create a new session."""
    # TODO: Create session in database
    display_name = project_name or project_path
    await update.message.reply_text(
        f"✅ Created new session for {display_name}\n\n"
        "Send a message to start chatting with Claude."
    )
