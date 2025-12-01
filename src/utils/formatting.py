"""Telegram formatting utilities."""
import re
from pathlib import Path

# Characters that need escaping in Telegram MarkdownV2
MARKDOWN_SPECIAL_CHARS = r"_*[]()~`>#+-=|{}.!"


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    return re.sub(f"([{re.escape(MARKDOWN_SPECIAL_CHARS)}])", r"\\\1", text)


def format_tool_use(tool_name: str, tool_input: dict) -> str:
    """Format tool use as inline annotation."""
    icons = {
        "Read": "📁",
        "Write": "📝",
        "Edit": "✏️",
        "Bash": "⚡",
        "Grep": "🔍",
        "Glob": "🔎",
    }
    icon = icons.get(tool_name, "🔧")

    # Extract relevant info based on tool type
    if tool_name in ("Read", "Write", "Edit"):
        path = tool_input.get("file_path", "")
        name = Path(path).name if path else "file"
        return f"[{icon} {name}]"

    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")
        cmd_short = truncate_text(cmd, max_len=40)
        return f"[{icon} {cmd_short}]"

    elif tool_name in ("Grep", "Glob"):
        pattern = tool_input.get("pattern", "")
        return f"[{icon} {pattern}]"

    else:
        return f"[{icon} {tool_name}]"


def chunk_text(text: str, max_size: int = 3800) -> list[str]:
    """Split text into chunks respecting max size."""
    if len(text) <= max_size:
        return [text]

    chunks = []
    current = ""

    for char in text:
        if len(current) >= max_size:
            chunks.append(current)
            current = ""
        current += char

    if current:
        chunks.append(current)

    return chunks


def truncate_text(text: str, max_len: int = 4096) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
