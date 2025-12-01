"""Telegram inline keyboard builders."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def project_keyboard(projects: dict[str, str] | None) -> InlineKeyboardMarkup:
    """Create project selection keyboard."""
    buttons = []

    if projects:
        for name, path in projects.items():
            buttons.append(
                [InlineKeyboardButton(name, callback_data=f"project:{name}")]
            )

    # Always add "Other" option for custom path
    buttons.append(
        [InlineKeyboardButton("📁 Other...", callback_data="project:other")]
    )

    return InlineKeyboardMarkup(buttons)


def session_keyboard(sessions: list) -> InlineKeyboardMarkup:
    """Create session selection keyboard."""
    buttons = []

    for session in sessions:
        status_icon = "🟢" if session.status == "active" else "⚪"
        name = session.project_name or session.id[:8]
        text = f"{status_icon} {name}"
        buttons.append(
            [InlineKeyboardButton(text, callback_data=f"session:{session.id}")]
        )

    return InlineKeyboardMarkup(buttons)


def approval_keyboard(request_id: str) -> InlineKeyboardMarkup:
    """Create approval buttons for dangerous operations."""
    buttons = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{request_id}"),
            InlineKeyboardButton("❌ Deny", callback_data=f"deny:{request_id}"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Create cancel button."""
    buttons = [
        [InlineKeyboardButton("🛑 Cancel", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(buttons)


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Create confirmation keyboard for destructive actions."""
    buttons = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm:{action}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)
