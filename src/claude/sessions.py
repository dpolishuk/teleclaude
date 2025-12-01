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

                        if content:
                            # Truncate if longer than 100 chars
                            if len(content) > 100:
                                return content[:100] + "..."
                            return content

                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

    except Exception:
        # Handle any file reading errors gracefully
        pass

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
