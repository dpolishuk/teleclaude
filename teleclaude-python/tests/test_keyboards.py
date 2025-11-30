"""Test keyboard builders."""
import pytest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.utils.keyboards import (
    project_keyboard,
    session_keyboard,
    approval_keyboard,
    cancel_keyboard,
)


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
