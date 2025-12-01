"""Test keyboard builders."""
import pytest
from pathlib import Path
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.utils.keyboards import (
    project_keyboard,
    session_keyboard,
    approval_keyboard,
    cancel_keyboard,
)
from src.bot.keyboards import (
    build_project_keyboard,
    build_session_keyboard,
    build_mode_keyboard,
)
from src.claude.sessions import Project, SessionInfo


def test_project_keyboard_with_projects():
    """project_keyboard creates buttons for projects."""
    projects = {"myapp": "/home/user/myapp", "api": "/home/user/api"}
    keyboard = project_keyboard(projects)

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 3  # 2 projects + other button
    assert keyboard.inline_keyboard[0][0].text == "myapp"


def test_project_keyboard_empty():
    """project_keyboard with no projects shows only Other."""
    keyboard = project_keyboard({})

    assert len(keyboard.inline_keyboard) == 1
    assert "other" in keyboard.inline_keyboard[0][0].callback_data.lower()


def test_session_keyboard_with_sessions():
    """session_keyboard creates buttons for sessions."""
    sessions = [
        type("Session", (), {"id": "abc123", "project_name": "myapp", "status": "active"}),
        type("Session", (), {"id": "def456", "project_name": "api", "status": "idle"}),
    ]
    keyboard = session_keyboard(sessions)

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 2


def test_approval_keyboard():
    """approval_keyboard creates approve/deny buttons."""
    keyboard = approval_keyboard("req123")

    assert isinstance(keyboard, InlineKeyboardMarkup)
    buttons = keyboard.inline_keyboard[0]
    assert len(buttons) == 2

    texts = [b.text for b in buttons]
    assert any("approve" in t.lower() or "✅" in t for t in texts)
    assert any("deny" in t.lower() or "❌" in t for t in texts)


def test_cancel_keyboard():
    """cancel_keyboard creates cancel button."""
    keyboard = cancel_keyboard()

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 1
    assert "cancel" in keyboard.inline_keyboard[0][0].callback_data.lower()


# Tests for src.bot.keyboards - resume feature keyboards


def test_build_project_keyboard_with_projects():
    """build_project_keyboard creates buttons for each project."""
    projects = [
        Project(
            name="-root-work-teleclaude",
            display_name="/root/work/teleclaude",
            path=Path("/home/user/.claude/projects/-root-work-teleclaude"),
        ),
        Project(
            name="-home-user-myapp",
            display_name="/home/user/myapp",
            path=Path("/home/user/.claude/projects/-home-user-myapp"),
        ),
    ]

    keyboard = build_project_keyboard(projects)

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 2

    # Check first button
    button1 = keyboard.inline_keyboard[0][0]
    assert button1.text == "/root/work/teleclaude"
    assert button1.callback_data == "resume_project:-root-work-teleclaude"

    # Check second button
    button2 = keyboard.inline_keyboard[1][0]
    assert button2.text == "/home/user/myapp"
    assert button2.callback_data == "resume_project:-home-user-myapp"


def test_build_project_keyboard_empty_list():
    """build_project_keyboard handles empty project list."""
    keyboard = build_project_keyboard([])

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 0


def test_build_session_keyboard_with_sessions():
    """build_session_keyboard creates buttons with session previews."""
    sessions = [
        SessionInfo(
            session_id="session1",
            path=Path("/home/user/.claude/projects/proj/session1.jsonl"),
            mtime=datetime(2024, 12, 1, 10, 0, 0),
            preview="fix permission buttons",
        ),
        SessionInfo(
            session_id="session2",
            path=Path("/home/user/.claude/projects/proj/session2.jsonl"),
            mtime=datetime(2024, 12, 1, 9, 0, 0),
            preview="implement MCP support for the bot",
        ),
    ]

    keyboard = build_session_keyboard(sessions)

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 2

    # Check first button shows preview
    button1 = keyboard.inline_keyboard[0][0]
    assert button1.text == "fix permission buttons"
    assert button1.callback_data == "resume_session:session1"

    # Check second button
    button2 = keyboard.inline_keyboard[1][0]
    assert button2.text == "implement MCP support for the bot"
    assert button2.callback_data == "resume_session:session2"


def test_build_session_keyboard_truncates_long_previews():
    """build_session_keyboard truncates previews that are too long."""
    long_preview = "A" * 150  # 150 chars, should already be truncated to 100 + "..."
    sessions = [
        SessionInfo(
            session_id="session1",
            path=Path("/home/user/.claude/projects/proj/session1.jsonl"),
            mtime=datetime(2024, 12, 1, 10, 0, 0),
            preview=long_preview[:100] + "...",  # Already truncated by parse_session_preview
        ),
    ]

    keyboard = build_session_keyboard(sessions)

    button = keyboard.inline_keyboard[0][0]
    # The preview must be truncated to Telegram's 64-char limit
    assert button.text.endswith("...")
    assert len(button.text) == 64  # Telegram's maximum button text length


def test_build_session_keyboard_empty_list():
    """build_session_keyboard handles empty session list."""
    keyboard = build_session_keyboard([])

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 0


def test_build_project_keyboard_truncates_long_display_names():
    """build_project_keyboard truncates display names that exceed 64 chars."""
    long_path = "/home/user/very/long/path/to/some/deeply/nested/project/directory/structure"
    projects = [
        Project(
            name="-home-user-very-long-path",
            display_name=long_path,  # 78 characters
            path=Path("/home/user/.claude/projects/-home-user-very-long-path"),
        ),
    ]

    keyboard = build_project_keyboard(projects)

    button = keyboard.inline_keyboard[0][0]
    # The display name must be truncated to Telegram's 64-char limit
    assert button.text.endswith("...")
    assert len(button.text) == 64  # Telegram's maximum button text length
    assert button.callback_data == "resume_project:-home-user-very-long-path"


def test_build_mode_keyboard_creates_fork_and_continue_buttons():
    """build_mode_keyboard creates Fork and Continue buttons side by side."""
    keyboard = build_mode_keyboard("session123")

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 1  # Single row

    # Check both buttons are in the same row
    buttons = keyboard.inline_keyboard[0]
    assert len(buttons) == 2

    # Check Fork button
    fork_button = buttons[0]
    assert "fork" in fork_button.text.lower()
    assert "safe" in fork_button.text.lower()
    assert fork_button.callback_data == "resume_mode:session123:fork"

    # Check Continue button
    continue_button = buttons[1]
    assert "continue" in continue_button.text.lower()
    assert "same" in continue_button.text.lower()
    assert continue_button.callback_data == "resume_mode:session123:continue"
