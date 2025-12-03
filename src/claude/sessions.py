"""Claude Code session scanner for resume feature.

This module scans ~/.claude/projects/ to discover available projects and sessions
for the /resume command functionality.
"""
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Project:
    """Represents a Claude Code project."""

    name: str  # Encoded project name (e.g., "-root-work-teleclaude")
    display_name: str  # Decoded path (e.g., "/root/work/teleclaude")
    path: Path  # Full path to project directory


@dataclass
class SessionInfo:
    """Represents a Claude Code session with metadata."""

    session_id: str  # Session ID (filename without .jsonl)
    path: Path  # Full path to session file
    mtime: datetime  # Last modification time
    preview: str  # First user message (truncated)


@dataclass
class UnifiedSessionInfo:
    """Session info with origin tracking for unified display."""

    session_id: str
    path: Path
    mtime: datetime
    preview: str
    origin: str  # "telegram" or "terminal"


def scan_projects() -> list[Project]:
    """Scan ~/.claude/projects/ for available projects.

    Returns:
        List of Project objects, one for each directory found.
        Returns empty list if directory doesn't exist.
    """
    projects_dir = Path.home() / ".claude" / "projects"

    if not projects_dir.exists():
        return []

    projects = []
    for project_path in projects_dir.iterdir():
        if project_path.is_dir():
            encoded_name = project_path.name
            display_name = _decode_project_name(encoded_name)
            projects.append(
                Project(
                    name=encoded_name,
                    display_name=display_name,
                    path=project_path,
                )
            )

    return projects


def scan_sessions(project: str) -> list[SessionInfo]:
    """Get sessions for a project, sorted by mtime desc, limit 5.

    Args:
        project: Encoded project name (e.g., "-root-work-teleclaude")

    Returns:
        List of SessionInfo objects, sorted by modification time (newest first),
        limited to 5 most recent. Returns empty list if project doesn't exist.
    """
    projects_dir = Path.home() / ".claude" / "projects"
    project_path = projects_dir / project

    if not project_path.exists():
        return []

    # Find all .jsonl files
    session_files = list(project_path.glob("*.jsonl"))

    if not session_files:
        return []

    # Sort by modification time (newest first) and limit to 5
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    session_files = session_files[:5]

    # Build SessionInfo objects
    sessions = []
    for session_file in session_files:
        session_id = session_file.stem  # Filename without .jsonl
        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        preview = parse_session_preview(session_file)

        sessions.append(
            SessionInfo(
                session_id=session_id,
                path=session_file,
                mtime=mtime,
                preview=preview,
            )
        )

    return sessions


def scan_unified_sessions(
    project_path: str,
    owned_session_ids: set[str],
    limit: int = 10,
) -> list[UnifiedSessionInfo]:
    """Scan sessions with origin detection.

    Args:
        project_path: Project directory path (e.g., "/root/work/teleclaude")
        owned_session_ids: Set of session IDs owned by current telegram user
        limit: Maximum sessions to return

    Returns:
        List of UnifiedSessionInfo sorted by mtime, newest first.
    """
    encoded = encode_project_path(project_path)
    projects_dir = Path.home() / ".claude" / "projects"
    project_dir = projects_dir / encoded

    if not project_dir.exists():
        return []

    # Find all .jsonl session files, excluding subagent files (agent-*)
    session_files = [
        f for f in project_dir.glob("*.jsonl")
        if not f.stem.startswith("agent-")
    ]

    if not session_files:
        return []

    # Sort by mtime (newest first) and limit
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    session_files = session_files[:limit]

    sessions = []
    for session_file in session_files:
        session_id = session_file.stem
        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        preview = parse_session_preview(session_file)

        # Determine origin based on ownership
        origin = "telegram" if session_id in owned_session_ids else "terminal"

        sessions.append(
            UnifiedSessionInfo(
                session_id=session_id,
                path=session_file,
                mtime=mtime,
                preview=preview,
                origin=origin,
            )
        )

    return sessions


def parse_session_preview(session_path: Path) -> str:
    """Extract first user message from JSONL for preview.

    Args:
        session_path: Path to session .jsonl file

    Returns:
        First user message content, truncated to 100 chars if needed.
        Returns empty string if no user messages found or file is empty.
    """
    try:
        with open(session_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())

                    # Look for user message type
                    if data.get("type") == "user":
                        message = data.get("message", {})
                        content = message.get("content", "")

                        # Extract text from content
                        text = _extract_text_from_content(content)
                        if text:
                            # Truncate if longer than 100 chars
                            if len(text) > 100:
                                return text[:100] + "..."
                            return text

                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

    except Exception:
        # Handle any file reading errors gracefully
        pass

    return ""


def _extract_text_from_content(content) -> str:
    """Extract plain text from message content.

    Content can be:
    - A string (direct text message)
    - A list of content blocks (may include tool_result, text, etc.)

    Args:
        content: Message content (string or list)

    Returns:
        Extracted text, or empty string if none found.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        # Look for text blocks, skip tool_result blocks
        for block in content:
            if isinstance(block, dict):
                # Skip tool results - they contain JSON data, not user messages
                if block.get("type") == "tool_result":
                    continue
                # Extract text from text blocks
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        return text

    return ""


def _decode_project_name(encoded: str) -> str:
    """Decode project name from encoded format.

    Claude Code encodes project paths by replacing '/' with '-'.
    For example: "-root-work-teleclaude" -> "/root/work/teleclaude"

    Args:
        encoded: Encoded project name (e.g., "-root-work-teleclaude")

    Returns:
        Decoded path (e.g., "/root/work/teleclaude")
    """
    # Remove leading dash and replace remaining dashes with slashes
    if encoded.startswith("-"):
        decoded = "/" + encoded[1:].replace("-", "/")
        return decoded

    # Fallback if format is unexpected
    return encoded


def decode_project_name(encoded: str) -> str:
    """Decode project name to original path. Public wrapper for _decode_project_name.

    Args:
        encoded: Encoded project name (e.g., "-root-work-teleclaude")

    Returns:
        Decoded path (e.g., "/root/work/teleclaude")
    """
    return _decode_project_name(encoded)


def encode_project_path(path: str) -> str:
    """Encode project path to Claude Code directory format.

    Claude Code encodes project paths by replacing '/' with '-'.
    For example: "/root/work/teleclaude" -> "-root-work-teleclaude"

    Args:
        path: Project path (e.g., "/root/work/teleclaude")

    Returns:
        Encoded name (e.g., "-root-work-teleclaude")
    """
    # Replace slashes with dashes
    if path.startswith("/"):
        return "-" + path[1:].replace("/", "-")
    return path.replace("/", "-")


def relative_time(dt: datetime) -> str:
    """Format datetime as relative time string.

    Args:
        dt: Datetime to format

    Returns:
        Human-readable relative time (e.g., "2h ago", "1d ago")
    """
    now = datetime.now()
    diff = now - dt

    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "just now"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"

    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"

    days = hours // 24
    if days < 7:
        return f"{days}d ago"

    weeks = days // 7
    if weeks < 4:
        return f"{weeks}w ago"

    return dt.strftime("%b %d")


def get_session_last_message(
    session_file: str,
    max_length: int = 100,
) -> str | None:
    """Get the last user message from a Claude session file.

    Args:
        session_file: Path to session .jsonl file
        max_length: Maximum length of returned message

    Returns:
        Last user message content, truncated if needed, or None if not found
    """
    path = Path(session_file)
    if not path.exists():
        return None

    try:
        last_user_message = None
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "human":
                        content = entry.get("message", {}).get("content", "")
                        if content:
                            last_user_message = content
                except json.JSONDecodeError:
                    continue

        if last_user_message and len(last_user_message) > max_length:
            return last_user_message[:max_length] + "..."
        return last_user_message

    except Exception:
        return None


def get_session_file_path(project_path: str, claude_session_id: str) -> str | None:
    """Get the path to a Claude session file.

    Args:
        project_path: Path to the project
        claude_session_id: Claude session UUID

    Returns:
        Full path to session .jsonl file, or None if not found
    """
    encoded = encode_project_path(project_path)
    sessions_dir = Path.home() / ".claude" / "projects" / encoded / "sessions"

    if not sessions_dir.exists():
        return None

    session_file = sessions_dir / f"{claude_session_id}.jsonl"
    if session_file.exists():
        return str(session_file)

    return None
