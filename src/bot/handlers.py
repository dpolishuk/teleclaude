"""Telegram bot command handlers."""
import asyncio
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from claude_agent_sdk import (
    AssistantMessage,
    UserMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

from src.storage.database import get_session
from src.storage.repository import SessionRepository
from src.claude import TeleClaudeClient, MessageStreamer
from src.claude.streaming import escape_html
from src.utils.keyboards import project_keyboard, cancel_keyboard
from src.commands import ClaudeCommand
from src.claude.sessions import scan_projects, scan_sessions
from src.bot.keyboards import build_project_keyboard, build_session_keyboard, build_mode_keyboard


class TypingIndicator:
    """Sends typing indicator while Claude is working.

    Telegram's typing indicator lasts ~5 seconds, so we send it
    repeatedly every 4 seconds until stopped.
    """

    def __init__(self, chat_id: int, bot):
        self.chat_id = chat_id
        self.bot = bot
        self._task: asyncio.Task | None = None
        self._running = False

    async def _send_typing_loop(self):
        """Send typing indicator every 4 seconds."""
        while self._running:
            try:
                await self.bot.send_chat_action(
                    chat_id=self.chat_id,
                    action=ChatAction.TYPING
                )
            except Exception:
                pass  # Ignore errors
            await asyncio.sleep(4)

    def start(self):
        """Start sending typing indicators."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._send_typing_loop())

    def stop(self):
        """Stop sending typing indicators."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None


HELP_TEXT = """
📱 *TeleClaude Commands*

*Session Management*
/new \\[project\\] \\- Start new session
/continue \\- Resume last session
/resume \\- Resume Claude Code session
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
/refresh \\- Rescan Claude commands

*MCP Servers*
/mcp \\- List MCP servers \\& status
/mcp test \\- Test all server connections
/mcp enable <name> \\- Enable a server
/mcp disable <name> \\- Disable a server
/mcp reload \\- Reload MCP config

*Help*
/help \\- Show this message

💡 Claude commands from \\.claude/commands/ appear in the / menu\\!
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
        display_name = session.project_name or session.project_path
        await update.message.reply_text(
            f"▶️ Continuing session in <code>{escape_html(display_name)}</code>\n\n"
            "Send a message to chat with Claude.",
            parse_mode="HTML",
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
    client = context.user_data.get("active_client")
    pending = context.user_data.get("pending_command")

    if client:
        try:
            await client.interrupt()
            await update.message.reply_text("🛑 Operation cancelled.")
        except Exception:
            await update.message.reply_text("🛑 Cancel requested.")
        finally:
            context.user_data.pop("active_client", None)
    elif pending:
        context.user_data.pop("pending_command", None)
        await update.message.reply_text("🛑 Command cancelled.")
    else:
        await update.message.reply_text("ℹ️ No operation in progress.")


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


async def refresh_commands(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /refresh command - rescan Claude commands."""
    registry = context.bot_data.get("command_registry")
    session = context.user_data.get("current_session")
    project_path = session.project_path if session else None

    count = await registry.refresh(update.get_bot(), project_path=project_path)

    await update.message.reply_text(
        f"🔄 Commands refreshed. {count} Claude command(s) loaded."
    )


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

    # Check if awaiting arguments for pending command
    if context.user_data.get("pending_command"):
        pending = context.user_data.pop("pending_command")
        registry = context.bot_data.get("command_registry")
        cmd = ClaudeCommand(
            name=pending["name"],
            description="",
            prompt=pending["prompt"],
            needs_args=True,
        )
        prompt = registry.substitute_args(cmd, update.message.text)
        await _execute_claude_prompt(update, context, prompt)
        return

    session = context.user_data.get("current_session")

    if not session:
        await update.message.reply_text(
            "❌ No active session. Use /new to start one or /continue to resume."
        )
        return

    prompt = update.message.text
    await _execute_claude_prompt(update, context, prompt)


async def _execute_claude_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
) -> None:
    """Execute a prompt and stream Claude's response."""
    session = context.user_data.get("current_session")
    config = context.bot_data.get("config")

    # Send "thinking" message
    thinking_msg = await update.message.reply_text(
        "🤔 Thinking...",
        reply_markup=cancel_keyboard(),
    )

    # Start typing indicator
    typing = TypingIndicator(update.effective_chat.id, context.bot)
    typing.start()

    # Create streamer for this response
    streamer = MessageStreamer(
        message=thinking_msg,
        throttle_ms=config.streaming.edit_throttle_ms,
        chunk_size=config.streaming.chunk_size,
    )

    try:
        # Get resume mode from context if available
        resume_mode = context.user_data.get("resume_mode")

        # Pass bot and chat_id for interactive permission prompts
        async with TeleClaudeClient(
            config,
            session,
            bot=context.bot,
            chat_id=update.effective_chat.id,
            resume_mode=resume_mode,
        ) as client:
            # Track client for cancel
            context.user_data["active_client"] = client

            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            await streamer.append_text(escape_html(block.text))
                        elif isinstance(block, ToolUseBlock):
                            # Format tool usage with full details (HTML)
                            tool_info = f"\n🔧 <b>{escape_html(block.name)}</b>\n"
                            if block.input:
                                for key, value in block.input.items():
                                    # Truncate long values
                                    str_val = str(value)
                                    if len(str_val) > 200:
                                        str_val = str_val[:200] + "..."
                                    tool_info += f"   <code>{escape_html(key)}</code>: {escape_html(str_val)}\n"
                            await streamer.append_text(tool_info)

                elif isinstance(message, UserMessage):
                    # Show tool results
                    for block in message.content:
                        if isinstance(block, ToolResultBlock):
                            result_text = str(block.content) if block.content else "(no output)"
                            # Truncate long results
                            if len(result_text) > 500:
                                result_text = result_text[:500] + "\n... (truncated)"
                            result_info = f"\n📄 Result:\n<pre>{escape_html(result_text)}</pre>\n"
                            await streamer.append_text(result_info)

                elif isinstance(message, ResultMessage):
                    # Update session with Claude session ID for continuity
                    if session and message.session_id:
                        session.claude_session_id = message.session_id
                    # Update session cost (if session exists)
                    if session and message.total_cost_usd:
                        session.total_cost_usd += message.total_cost_usd

            # Final flush
            await streamer.flush()

    except Exception as e:
        await thinking_msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        typing.stop()
        context.user_data.pop("active_client", None)


async def _create_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    project_path: str,
    project_name: str | None = None,
) -> None:
    """Create a new session."""
    user_id = update.effective_user.id

    async with get_session() as db:
        repo = SessionRepository(db)
        session = await repo.create_session(
            telegram_user_id=user_id,
            project_path=project_path,
            project_name=project_name,
        )
        # Store session in user_data for quick access
        context.user_data["current_session"] = session

    # Refresh commands for this project
    registry = context.bot_data.get("command_registry")
    cmd_count = await registry.refresh(update.get_bot(), project_path=project_path)

    display_name = project_name or project_path

    # Get MCP server count
    mcp_manager = context.bot_data.get("mcp_manager")
    mcp_count = len(mcp_manager.config.get_enabled_servers()) if mcp_manager else 0

    mcp_msg = f"\n🔌 {mcp_count} MCP server(s) enabled." if mcp_count > 0 else ""

    await update.message.reply_text(
        f"✅ Created new session for {display_name}\n"
        f"📋 {cmd_count} Claude command(s) available.{mcp_msg}\n\n"
        "Send a message to start chatting with Claude."
    )


async def resume_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resume command - show project selection."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("resume_cmd: Starting /resume command")

    projects = scan_projects()
    logger.info(f"resume_cmd: Found {len(projects)} projects")

    if not projects:
        logger.info("resume_cmd: No projects found")
        await update.message.reply_text(
            "❌ No Claude Code sessions found in ~/.claude/projects/"
        )
        return

    keyboard = build_project_keyboard(projects)
    logger.info(f"resume_cmd: Built keyboard with {len(keyboard.inline_keyboard)} rows")
    await update.message.reply_text(
        "📁 Select a project to resume:",
        reply_markup=keyboard,
    )
    logger.info("resume_cmd: Sent message with keyboard")


async def mcp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mcp command - MCP server management."""
    mcp_manager = context.bot_data.get("mcp_manager")

    if not mcp_manager:
        await update.message.reply_text("❌ MCP manager not initialized.")
        return

    # No args - show status (auto-test first)
    if not context.args:
        await update.message.reply_text("🔍 Checking MCP servers...")
        await mcp_manager.test_all_servers()
        status_msg = mcp_manager.format_status_message()
        await update.message.reply_text(status_msg, parse_mode="HTML")
        return

    subcommand = context.args[0].lower()

    if subcommand == "list":
        await update.message.reply_text("🔍 Checking MCP servers...")
        await mcp_manager.test_all_servers()
        status_msg = mcp_manager.format_status_message()
        await update.message.reply_text(status_msg, parse_mode="HTML")

    elif subcommand == "test":
        # Test specific server or all
        if len(context.args) > 1:
            server_name = context.args[1]
            await update.message.reply_text(f"🔍 Testing {escape_html(server_name)}...")
            info = await mcp_manager.test_server(server_name)
            status_icon = "🟢" if info.status.value == "online" else "🔴"
            msg = f"{status_icon} <code>{escape_html(info.name)}</code>: {info.status.value}"
            if info.error:
                msg += f"\n└─ {escape_html(info.error)}"
            await update.message.reply_text(msg, parse_mode="HTML")
        else:
            await update.message.reply_text("🔍 Testing all MCP servers...")
            results = await mcp_manager.test_all_servers()
            lines = ["<b>Test Results</b>\n"]
            for info in results:
                icon = "🟢" if info.status.value == "online" else "🔴" if info.status.value in ("offline", "error") else "⏸️"
                line = f"{icon} <code>{escape_html(info.name)}</code>: {info.status.value}"
                if info.error:
                    line += f"\n   └─ {escape_html(info.error)}"
                lines.append(line)
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    elif subcommand == "enable":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /mcp enable <server_name>")
            return
        server_name = context.args[1]
        if mcp_manager.enable_server(server_name):
            await update.message.reply_text(f"✅ Enabled MCP server: <code>{escape_html(server_name)}</code>", parse_mode="HTML")
        else:
            await update.message.reply_text(f"❌ Server not found: {escape_html(server_name)}")

    elif subcommand == "disable":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /mcp disable <server_name>")
            return
        server_name = context.args[1]
        if mcp_manager.disable_server(server_name):
            await update.message.reply_text(f"⏸️ Disabled MCP server: <code>{escape_html(server_name)}</code>", parse_mode="HTML")
        else:
            await update.message.reply_text(f"❌ Server not found: {escape_html(server_name)}")

    elif subcommand == "reload":
        count = mcp_manager.reload_config()
        # Also update the config in bot_data
        config = context.bot_data.get("config")
        if config:
            config.mcp = mcp_manager.config
        await update.message.reply_text(f"🔄 Reloaded MCP config: {count} server(s)")

    elif subcommand == "on":
        mcp_manager.config.enabled = True
        await update.message.reply_text("✅ MCP servers enabled globally")

    elif subcommand == "off":
        mcp_manager.config.enabled = False
        await update.message.reply_text("⏸️ MCP servers disabled globally")

    else:
        await update.message.reply_text(
            "Usage: /mcp [list|test|enable|disable|reload|on|off]\n\n"
            "Examples:\n"
            "  /mcp - Show server status\n"
            "  /mcp test - Test all connections\n"
            "  /mcp test perplexity-mcp - Test specific server\n"
            "  /mcp enable context7 - Enable server\n"
            "  /mcp disable serena - Disable server\n"
            "  /mcp reload - Reload .mcp.json\n"
            "  /mcp on/off - Global MCP toggle"
        )
