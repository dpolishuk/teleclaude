"""Keyboard builders for the resume feature.

This module provides keyboard builders for the /resume command flow:
1. Project selection
2. Session selection (with previews)
3. Fork/Continue mode selection
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.claude.sessions import Project, SessionInfo

# Telegram's maximum button text length
TELEGRAM_BUTTON_TEXT_LIMIT = 64


def build_project_keyboard(projects: list[Project]) -> InlineKeyboardMarkup:
    """Build project selection keyboard.

    Args:
        projects: List of Project objects from scan_projects()

    Returns:
        InlineKeyboardMarkup with one button per project showing display name.
        Callback data pattern: resume_project:<project_name>
    """
    buttons = []

    for project in projects:
        display_text = project.display_name
        if len(display_text) > TELEGRAM_BUTTON_TEXT_LIMIT:
            display_text = display_text[:61] + "..."

        button = InlineKeyboardButton(
            text=display_text,
            callback_data=f"resume_project:{project.name}",
        )
        buttons.append([button])

    return InlineKeyboardMarkup(buttons)


def build_session_keyboard(sessions: list[SessionInfo]) -> InlineKeyboardMarkup:
    """Build session selection keyboard with previews.

    Args:
        sessions: List of SessionInfo objects from scan_sessions()

    Returns:
        InlineKeyboardMarkup with one button per session showing preview.
        Callback data pattern: resume_session:<session_id>
    """
    buttons = []

    for session in sessions:
        preview_text = session.preview
        if len(preview_text) > TELEGRAM_BUTTON_TEXT_LIMIT:
            preview_text = preview_text[:61] + "..."

        button = InlineKeyboardButton(
            text=preview_text,
            callback_data=f"resume_session:{session.session_id}",
        )
        buttons.append([button])

    return InlineKeyboardMarkup(buttons)


def build_mode_keyboard(session_id: str) -> InlineKeyboardMarkup:
    """Build Fork/Continue mode selection keyboard.

    Args:
        session_id: The session ID to resume

    Returns:
        InlineKeyboardMarkup with two buttons side by side:
        - Fork (safe): Creates new branch from session history
        - Continue (same): Continues exact same session thread
        Callback data pattern: resume_mode:<session_id>:<fork|continue>
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="Fork (safe)",
                callback_data=f"resume_mode:{session_id}:fork",
            ),
            InlineKeyboardButton(
                text="Continue (same)",
                callback_data=f"resume_mode:{session_id}:continue",
            ),
        ]
    ]

    return InlineKeyboardMarkup(buttons)
