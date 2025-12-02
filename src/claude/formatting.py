"""Minimalistic Claude Code style formatting for Telegram.

Clean, professional formatting that mimics Claude Code CLI output.
Uses minimal symbols and monospace formatting for a terminal-like feel.
"""
import html
import re
from typing import Any


# Claude Code style symbol for tool calls
TOOL_SYMBOL = "⏵"

# Diff formatting constants
DIFF_ADD = "✅"
DIFF_DEL = "❌"
FILE_ICON = "📄"


def escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return html.escape(text)


def format_tool_call(name: str, inputs: dict[str, Any]) -> str:
    """Format a tool call in minimalistic Claude Code style.

    Examples:
        ⏵ Read src/main.py
        ⏵ Bash ls -la
        ⏵ Edit src/config.py
        ⏵ Grep "pattern"

    Args:
        name: Tool name (e.g., "Read", "Bash", "Edit")
        inputs: Tool input parameters

    Returns:
        Formatted HTML string for Telegram
    """
    primary_arg = _get_primary_argument(name, inputs)

    if primary_arg:
        return f"\n<code>{TOOL_SYMBOL} {escape_html(name)}</code> <code>{escape_html(primary_arg)}</code>\n"
    else:
        return f"\n<code>{TOOL_SYMBOL} {escape_html(name)}</code>\n"


def _get_primary_argument(tool_name: str, inputs: dict[str, Any]) -> str:
    """Extract the primary argument to show inline with tool name."""
    tool_lower = tool_name.lower()

    # File operations - show path
    if tool_lower in ("read", "write", "edit"):
        path = inputs.get("file_path", inputs.get("path", ""))
        return _truncate(str(path), 60)

    # Bash - show command
    if tool_lower == "bash":
        cmd = inputs.get("command", "")
        return _truncate(str(cmd), 80)

    # Grep - show pattern
    if tool_lower == "grep":
        pattern = inputs.get("pattern", "")
        path = inputs.get("path", "")
        if path and path != ".":
            return _truncate(f'"{pattern}" {path}', 60)
        return _truncate(f'"{pattern}"', 50)

    # Glob - show pattern
    if tool_lower == "glob":
        pattern = inputs.get("pattern", "")
        return _truncate(f'"{pattern}"', 50)

    # Task - show description
    if tool_lower == "task":
        desc = inputs.get("description", inputs.get("prompt", ""))
        return _truncate(str(desc), 50)

    # WebFetch - show URL
    if tool_lower == "webfetch":
        url = inputs.get("url", "")
        return _truncate(str(url), 60)

    # WebSearch - show query
    if tool_lower == "websearch":
        query = inputs.get("query", "")
        return _truncate(str(query), 50)

    # TodoWrite - no args needed
    if tool_lower == "todowrite":
        return ""

    # Default: try common parameter names
    for key in ("file_path", "path", "command", "query", "pattern", "description"):
        if key in inputs:
            return _truncate(str(inputs[key]), 50)

    return ""


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if too long."""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "…"


def format_tool_result(content: str | list | None, is_error: bool = False) -> str:
    """Format a tool result in minimalistic style.

    Shows results in monospace, clean and readable.

    Args:
        content: Tool result content
        is_error: Whether this is an error result

    Returns:
        Formatted HTML string for Telegram
    """
    if content is None:
        return ""

    # Convert list/structured content to string
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                text_parts.append(str(item["text"]))
            else:
                text_parts.append(str(item))
        result_text = "\n".join(text_parts)
    else:
        result_text = str(content)

    result_text = result_text.strip()

    if not result_text:
        return ""

    # Smart truncation for long results
    max_len = 1500
    if len(result_text) > max_len:
        lines = result_text.split("\n")
        truncated = result_text[:max_len]
        last_newline = truncated.rfind("\n")
        if last_newline > max_len // 2:
            truncated = truncated[:last_newline]
        remaining = len(lines) - truncated.count("\n") - 1
        if remaining > 0:
            result_text = f"{truncated}\n⋯ {remaining} more lines"
        else:
            result_text = f"{truncated}…"

    # Format output
    if is_error:
        return f"\n<pre>✗ {escape_html(result_text)}</pre>\n"
    else:
        return f"\n<pre>{escape_html(result_text)}</pre>\n"


def format_status(tool_name: str, inputs: dict[str, Any]) -> str:
    """Generate a minimal status message for a tool.

    Args:
        tool_name: Name of the tool
        inputs: Tool input parameters

    Returns:
        Status message string (no emojis, clean text)
    """
    tool_lower = tool_name.lower()

    # File operations
    if tool_lower == "read":
        path = inputs.get("file_path", inputs.get("path", ""))
        return f"Reading {_truncate(str(path), 30)}…"

    if tool_lower == "write":
        path = inputs.get("file_path", inputs.get("path", ""))
        return f"Writing {_truncate(str(path), 30)}…"

    if tool_lower == "edit":
        path = inputs.get("file_path", inputs.get("path", ""))
        return f"Editing {_truncate(str(path), 30)}…"

    # Bash
    if tool_lower == "bash":
        cmd = inputs.get("command", "")
        first_word = str(cmd).split()[0] if cmd else "command"
        return f"Running {_truncate(first_word, 20)}…"

    # Search
    if tool_lower == "grep":
        return "Searching…"

    if tool_lower == "glob":
        return "Finding files…"

    # Web
    if tool_lower == "webfetch":
        return "Fetching…"

    if tool_lower == "websearch":
        return "Searching web…"

    # Task/Agent
    if tool_lower == "task":
        return "Running agent…"

    # MCP tools
    if tool_lower.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            return f"{parts[1]}…"
        return "MCP…"

    return f"{tool_name}…"


def format_diff(content: str) -> str:
    """Format unified diff with emoji indicators.

    Args:
        content: Unified diff text

    Returns:
        HTML-formatted diff with ✅/❌ markers
    """
    lines = content.split("\n")
    output: list[str] = []
    current_file: str | None = None

    for line in lines:
        # Git diff header - extract filename
        if line.startswith("diff --git "):
            match = re.search(r"b/(.+)$", line)
            if match:
                current_file = match.group(1)
                output.append(f"\n{FILE_ICON} <b>{escape_html(current_file)}</b>\n")
            continue

        # Skip --- and +++ headers (already got filename)
        if line.startswith("--- ") or line.startswith("+++ "):
            continue

        # Hunk header
        if line.startswith("@@ ") and " @@" in line:
            match = re.search(r"@@ -(\d+)", line)
            line_num = match.group(1) if match else "?"
            output.append(f"<code>── line {line_num} ──</code>")
            continue

        # Added line (but not +++)
        if line.startswith("+") and not line.startswith("+++"):
            output.append(f"{DIFF_ADD} <code>{escape_html(line[1:])}</code>")
            continue

        # Removed line (but not ---)
        if line.startswith("-") and not line.startswith("---"):
            output.append(f"{DIFF_DEL} <code>{escape_html(line[1:])}</code>")
            continue

        # Context line
        if line.startswith(" "):
            output.append(f"   <code>{escape_html(line[1:])}</code>")
            continue

        # Other lines (empty, etc)
        if line.strip():
            output.append(f"<code>{escape_html(line)}</code>")

    return "\n".join(output)


# Todo status symbols
TODO_COMPLETED = "☑"
TODO_IN_PROGRESS = "⏳"
TODO_PENDING = "☐"


def format_todos(todos: list[dict]) -> str:
    """Format a todo list for Telegram display.

    Args:
        todos: List of todo items with 'content', 'status', and optional 'activeForm'

    Returns:
        Formatted HTML string with checkbox-style todos
    """
    if not todos:
        return ""

    lines = []
    for todo in todos:
        content = todo.get("content", "")
        status = todo.get("status", "pending")

        # Choose symbol based on status
        if status == "completed":
            symbol = TODO_COMPLETED
        elif status == "in_progress":
            symbol = TODO_IN_PROGRESS
            # Use activeForm for in-progress items if available
            active_form = todo.get("activeForm")
            if active_form:
                content = active_form
        else:
            symbol = TODO_PENDING

        lines.append(f"{symbol} {escape_html(content)}")

    return "\n".join(lines)
