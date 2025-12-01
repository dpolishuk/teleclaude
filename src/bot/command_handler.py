"""Handler for dynamic Claude commands."""
from telegram import Update
from telegram.ext import ContextTypes

from claude_agent_sdk import (
    AssistantMessage,
    UserMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

from src.claude import TeleClaudeClient, MessageStreamer
from src.claude.streaming import escape_html
from src.utils.keyboards import cancel_keyboard


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
    await _execute_prompt(update, context, prompt)


async def _execute_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
) -> None:
    """Execute a prompt and stream response."""
    session = context.user_data.get("current_session")
    config = context.bot_data.get("config")

    # Send "thinking" message
    thinking_msg = await update.message.reply_text(
        "🤔 Thinking...",
        reply_markup=cancel_keyboard(),
    )

    # Create streamer
    streamer = MessageStreamer(
        message=thinking_msg,
        throttle_ms=config.streaming.edit_throttle_ms,
        chunk_size=config.streaming.chunk_size,
    )

    try:
        async with TeleClaudeClient(config, session) as client:
            context.user_data["active_client"] = client

            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            await streamer.append_text(escape_html(block.text))
                        elif isinstance(block, ToolUseBlock):
                            tool_info = f"\n🔧 <b>{escape_html(block.name)}</b>\n"
                            if block.input:
                                for key, value in block.input.items():
                                    str_val = str(value)
                                    if len(str_val) > 200:
                                        str_val = str_val[:200] + "..."
                                    tool_info += f"   <code>{escape_html(key)}</code>: {escape_html(str_val)}\n"
                            await streamer.append_text(tool_info)

                elif isinstance(message, UserMessage):
                    for block in message.content:
                        if isinstance(block, ToolResultBlock):
                            result_text = str(block.content) if block.content else "(no output)"
                            if len(result_text) > 500:
                                result_text = result_text[:500] + "\n... (truncated)"
                            result_info = f"\n📄 Result:\n<pre>{escape_html(result_text)}</pre>\n"
                            await streamer.append_text(result_info)

                elif isinstance(message, ResultMessage):
                    if message.total_cost_usd:
                        session.total_cost_usd += message.total_cost_usd

            await streamer.flush()

    except Exception as e:
        await thinking_msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        context.user_data.pop("active_client", None)
