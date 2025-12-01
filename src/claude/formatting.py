"""Claude Code style message formatting for Telegram.

Formats tool usage, results, and status messages to mimic Claude Code CLI output.
"""
import html
from typing import Any


def escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return html.escape(text)


def format_tool_call(name: str, inputs: dict[str, Any]) -> str:
    """Format a tool call in Claude Code compact inline style.

    Examples:
        > Read src/main.py
        > Bash ls -la
        > Edit src/config.py
        > Grep "pattern" --path=src/

    Args:
        name: Tool name (e.g., "Read", "Bash", "Edit")
        inputs: Tool input parameters

    Returns:
        Formatted HTML string for Telegram
    """
    # Get the primary argument for inline display
    primary_arg = _get_primary_argument(name, inputs)

    if primary_arg:
        return f"\n<code>&gt; {escape_html(name)}</code> <code>{escape_html(primary_arg)}</code>\n"
    else:
        return f"\n<code>&gt; {escape_html(name)}</code>\n"


def _get_primary_argument(tool_name: str, inputs: dict[str, Any]) -> str:
    """Extract the primary argument to show inline with tool name.

    Different tools have different primary arguments:
    - Read/Write/Edit: file_path
    - Bash: command
    - Grep: pattern + optional path
    - Glob: pattern
    - Task: description
    """
    tool_lower = tool_name.lower()

    # File operations - show path
    if tool_lower in ("read", "write", "edit"):
        path = inputs.get("file_path", inputs.get("path", ""))
        return _truncate(str(path), 80)

    # Bash - show command
    if tool_lower == "bash":
        cmd = inputs.get("command", "")
        return _truncate(str(cmd), 100)

    # Grep - show pattern and optional path
    if tool_lower == "grep":
        pattern = inputs.get("pattern", "")
        path = inputs.get("path", "")
        if path and path != ".":
            return _truncate(f'"{pattern}" --path={path}', 80)
        return _truncate(f'"{pattern}"', 60)

    # Glob - show pattern
    if tool_lower == "glob":
        pattern = inputs.get("pattern", "")
        return _truncate(f'"{pattern}"', 60)

    # Task - show description
    if tool_lower == "task":
        desc = inputs.get("description", inputs.get("prompt", ""))
        return _truncate(str(desc), 60)

    # WebFetch - show URL
    if tool_lower == "webfetch":
        url = inputs.get("url", "")
        return _truncate(str(url), 80)

    # WebSearch - show query
    if tool_lower == "websearch":
        query = inputs.get("query", "")
        return _truncate(str(query), 60)

    # TodoWrite - just show tool name
    if tool_lower == "todowrite":
        return ""

    # Default: try common parameter names
    for key in ("file_path", "path", "command", "query", "pattern", "description"):
        if key in inputs:
            return _truncate(str(inputs[key]), 60)

    # Fallback: show first parameter if short enough
    if inputs:
        first_key = next(iter(inputs))
        first_val = str(inputs[first_key])
        if len(first_val) <= 40:
            return _truncate(first_val, 40)

    return ""


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if too long."""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def format_tool_result(content: str | list | None, is_error: bool = False) -> str:
    """Format a tool result in Claude Code style.

    Shows results inline, truncating only very long outputs.

    Args:
        content: Tool result content (string or structured)
        is_error: Whether this is an error result

    Returns:
        Formatted HTML string for Telegram
    """
    if content is None:
        return ""

    # Convert list/structured content to string
    if isinstance(content, list):
        # Handle structured content from tool results
        text_parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                text_parts.append(str(item["text"]))
            else:
                text_parts.append(str(item))
        result_text = "\n".join(text_parts)
    else:
        result_text = str(content)

    # Clean up whitespace
    result_text = result_text.strip()

    if not result_text:
        return ""

    # Truncate very long results (keep more than before - 2000 chars)
    max_result_len = 2000
    if len(result_text) > max_result_len:
        # Count lines
        lines = result_text.split("\n")
        truncated = result_text[:max_result_len]
        # Find last complete line
        last_newline = truncated.rfind("\n")
        if last_newline > max_result_len // 2:
            truncated = truncated[:last_newline]
        remaining_lines = len(lines) - truncated.count("\n") - 1
        result_text = f"{truncated}\n... ({remaining_lines} more lines)"

    # Format based on error status
    if is_error:
        return f"\n<pre>❌ {escape_html(result_text)}</pre>\n"
    else:
        return f"\n<pre>{escape_html(result_text)}</pre>\n"


def format_status(tool_name: str, inputs: dict[str, Any]) -> str:
    """Generate a dynamic status message for a tool.

    Examples:
        "Reading src/main.py..."
        "Running bash command..."
        "Searching for pattern..."

    Args:
        tool_name: Name of the tool
        inputs: Tool input parameters

    Returns:
        Status message string
    """
    tool_lower = tool_name.lower()

    # File operations
    if tool_lower == "read":
        path = inputs.get("file_path", inputs.get("path", "file"))
        return f"📖 Reading {_truncate(str(path), 40)}..."

    if tool_lower == "write":
        path = inputs.get("file_path", inputs.get("path", "file"))
        return f"✍️ Writing {_truncate(str(path), 40)}..."

    if tool_lower == "edit":
        path = inputs.get("file_path", inputs.get("path", "file"))
        return f"✏️ Editing {_truncate(str(path), 40)}..."

    # Bash
    if tool_lower == "bash":
        cmd = inputs.get("command", "")
        short_cmd = _truncate(str(cmd).split()[0] if cmd else "command", 20)
        return f"⚡ Running {short_cmd}..."

    # Search operations
    if tool_lower == "grep":
        return "🔍 Searching..."

    if tool_lower == "glob":
        return "📁 Finding files..."

    # Web operations
    if tool_lower == "webfetch":
        return "🌐 Fetching URL..."

    if tool_lower == "websearch":
        return "🔎 Searching web..."

    # Task/Agent
    if tool_lower == "task":
        return "🤖 Running agent..."

    # MCP tools
    if tool_lower.startswith("mcp__"):
        # Extract server and tool name: mcp__server__tool
        parts = tool_name.split("__")
        if len(parts) >= 3:
            server = parts[1]
            tool = parts[2]
            return f"🔌 {server}: {tool}..."
        return f"🔌 MCP tool..."

    # Default
    return f"⚙️ {tool_name}..."
