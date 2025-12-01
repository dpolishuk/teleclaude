"""Tests for /resume command and callback handlers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from pathlib import Path

from telegram import Update, Message, User, Chat, CallbackQuery
from telegram.ext import ContextTypes

from src.bot.handlers import resume_cmd
from src.bot.callbacks import (
    _handle_resume_project,
    _handle_resume_session,
    _handle_resume_mode,
)
from src.claude.sessions import Project, SessionInfo


@pytest.fixture
def mock_update():
    """Create a mock Update object."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.message = AsyncMock(spec=Message)
    return update


@pytest.fixture
def mock_callback_update():
    """Create a mock Update object for callback queries."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 12345
    update.callback_query = AsyncMock(spec=CallbackQuery)
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock ContextTypes.DEFAULT_TYPE object."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot_data = {}
    context.user_data = {}
    context.args = []
    return context


class TestResumeCmd:
    """Tests for /resume command handler."""

    @pytest.mark.asyncio
    async def test_resume_cmd_no_projects(self, mock_update, mock_context):
        """Test /resume when no projects are found."""
        with patch("src.bot.handlers.scan_projects", return_value=[]):
            await resume_cmd(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once_with(
                "❌ No Claude Code sessions found in ~/.claude/projects/"
            )

    @pytest.mark.asyncio
    async def test_resume_cmd_with_projects(self, mock_update, mock_context):
        """Test /resume with available projects."""
        mock_projects = [
            Project(
                name="-root-work-teleclaude",
                display_name="/root/work/teleclaude",
                path=Path("/home/user/.claude/projects/-root-work-teleclaude"),
            ),
            Project(
                name="-home-user-myproject",
                display_name="/home/user/myproject",
                path=Path("/home/user/.claude/projects/-home-user-myproject"),
            ),
        ]

        with patch("src.bot.handlers.scan_projects", return_value=mock_projects):
            with patch("src.bot.handlers.build_project_keyboard") as mock_keyboard:
                mock_keyboard.return_value = MagicMock()

                await resume_cmd(mock_update, mock_context)

                mock_keyboard.assert_called_once_with(mock_projects)
                mock_update.message.reply_text.assert_called_once()
                call_args = mock_update.message.reply_text.call_args
                assert "Select a project to resume:" in call_args[0][0]
                assert "reply_markup" in call_args[1]


class TestResumeProjectCallback:
    """Tests for resume_project callback handler."""

    @pytest.mark.asyncio
    async def test_handle_resume_project_no_value(self, mock_callback_update, mock_context):
        """Test resume_project callback with no value."""
        await _handle_resume_project(mock_callback_update, mock_context, None)

        mock_callback_update.callback_query.edit_message_text.assert_called_once_with(
            "❌ Invalid project selection."
        )

    @pytest.mark.asyncio
    async def test_handle_resume_project_no_sessions(self, mock_callback_update, mock_context):
        """Test resume_project callback when no sessions are found."""
        with patch("src.bot.callbacks.scan_sessions", return_value=[]):
            await _handle_resume_project(
                mock_callback_update, mock_context, "-root-work-teleclaude"
            )

            mock_callback_update.callback_query.edit_message_text.assert_called_once_with(
                "❌ No sessions found for this project."
            )

    @pytest.mark.asyncio
    async def test_handle_resume_project_with_sessions(self, mock_callback_update, mock_context):
        """Test resume_project callback with available sessions."""
        mock_sessions = [
            SessionInfo(
                session_id="session123",
                path=Path("/home/user/.claude/projects/-root-work-teleclaude/session123.jsonl"),
                mtime=datetime(2025, 12, 1, 10, 0, 0),
                preview="Fix bug in login handler",
            ),
        ]

        with patch("src.bot.callbacks.scan_sessions", return_value=mock_sessions):
            with patch("src.bot.callbacks.build_session_keyboard") as mock_keyboard:
                mock_keyboard.return_value = MagicMock()

                await _handle_resume_project(
                    mock_callback_update, mock_context, "-root-work-teleclaude"
                )

                mock_keyboard.assert_called_once_with(mock_sessions)
                mock_callback_update.callback_query.edit_message_text.assert_called_once()
                call_args = mock_callback_update.callback_query.edit_message_text.call_args
                assert "Select a session to resume:" in call_args[0][0]
                assert "reply_markup" in call_args[1]


class TestResumeSessionCallback:
    """Tests for resume_session callback handler."""

    @pytest.mark.asyncio
    async def test_handle_resume_session_no_value(self, mock_callback_update, mock_context):
        """Test resume_session callback with no value."""
        await _handle_resume_session(mock_callback_update, mock_context, None)

        mock_callback_update.callback_query.edit_message_text.assert_called_once_with(
            "❌ Invalid session selection."
        )

    @pytest.mark.asyncio
    async def test_handle_resume_session_with_value(self, mock_callback_update, mock_context):
        """Test resume_session callback with valid session ID."""
        session_id = "session123"
        mock_context.user_data["resume_project_name"] = "-root-work-teleclaude"

        with patch("src.bot.callbacks.build_mode_keyboard") as mock_keyboard, \
             patch("src.bot.callbacks.scan_sessions") as mock_scan:

            mock_keyboard.return_value = MagicMock()
            # Mock session info with preview
            mock_session = MagicMock()
            mock_session.session_id = session_id
            mock_session.preview = "test preview"
            mock_scan.return_value = [mock_session]

            await _handle_resume_session(mock_callback_update, mock_context, session_id)

            # Check that session_id and preview were stored
            assert mock_context.user_data["resume_session_id"] == session_id
            assert mock_context.user_data["resume_session_preview"] == "test preview"

            # Check that mode keyboard was built
            mock_keyboard.assert_called_once_with(session_id)

            # Check that message was edited with preview
            mock_callback_update.callback_query.edit_message_text.assert_called_once()
            call_args = mock_callback_update.callback_query.edit_message_text.call_args
            assert "Choose resume mode:" in call_args[0][0]
            assert "test preview" in call_args[0][0]
            assert "reply_markup" in call_args[1]


class TestResumeModeCallback:
    """Tests for resume_mode callback handler."""

    @pytest.mark.asyncio
    async def test_handle_resume_mode_no_value(self, mock_callback_update, mock_context):
        """Test resume_mode callback with no value."""
        await _handle_resume_mode(mock_callback_update, mock_context, None)

        mock_callback_update.callback_query.edit_message_text.assert_called_once_with(
            "❌ Invalid mode selection."
        )

    @pytest.mark.asyncio
    async def test_handle_resume_mode_invalid_format(self, mock_callback_update, mock_context):
        """Test resume_mode callback with invalid format."""
        await _handle_resume_mode(mock_callback_update, mock_context, "invalid")

        mock_callback_update.callback_query.edit_message_text.assert_called_once_with(
            "❌ Invalid mode data format."
        )

    @pytest.mark.asyncio
    async def test_handle_resume_mode_invalid_mode(self, mock_callback_update, mock_context):
        """Test resume_mode callback with invalid mode."""
        await _handle_resume_mode(mock_callback_update, mock_context, "session123:invalid_mode")

        mock_callback_update.callback_query.edit_message_text.assert_called_once_with(
            "❌ Invalid mode selection."
        )

    @pytest.mark.asyncio
    async def test_handle_resume_mode_fork(self, mock_callback_update, mock_context):
        """Test resume_mode callback with fork mode."""
        from unittest.mock import AsyncMock

        mock_context.user_data["resume_project_name"] = "-root-work-teleclaude"
        mock_registry = MagicMock()
        mock_registry.refresh = AsyncMock(return_value=5)
        mock_context.bot_data = {"command_registry": mock_registry}

        with patch("src.bot.callbacks.decode_project_name") as mock_decode, \
             patch("src.bot.callbacks.get_session") as mock_db:

            mock_decode.return_value = "/root/work/teleclaude"
            # Mock database session
            mock_db_session = MagicMock()
            mock_db_session.__aenter__.return_value = mock_db_session
            mock_db_session.__aexit__.return_value = None
            mock_db.return_value = mock_db_session

            # Mock repository with AsyncMock
            mock_repo = MagicMock()
            mock_session_obj = MagicMock()
            from unittest.mock import AsyncMock
            mock_repo.create_session = AsyncMock(return_value=mock_session_obj)

            with patch("src.bot.callbacks.SessionRepository", return_value=mock_repo):
                await _handle_resume_mode(mock_callback_update, mock_context, "session123:fork")

                # Check that session_id and mode were stored
                assert mock_context.user_data["resume_session_id"] == "session123"
                assert mock_context.user_data["resume_mode"] == "fork"
                assert mock_context.user_data["current_session"] == mock_session_obj

                # Check message
                mock_callback_update.callback_query.edit_message_text.assert_called_once()
                call_args = mock_callback_update.callback_query.edit_message_text.call_args
                assert "forked" in call_args[0][0]
                assert "Session resumed!" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_resume_mode_continue(self, mock_callback_update, mock_context):
        """Test resume_mode callback with continue mode."""
        from unittest.mock import AsyncMock

        mock_context.user_data["resume_project_name"] = "-root-work-teleclaude"
        mock_registry = MagicMock()
        mock_registry.refresh = AsyncMock(return_value=5)
        mock_context.bot_data = {"command_registry": mock_registry}

        with patch("src.bot.callbacks.decode_project_name") as mock_decode, \
             patch("src.bot.callbacks.get_session") as mock_db:

            mock_decode.return_value = "/root/work/teleclaude"
            # Mock database session
            mock_db_session = MagicMock()
            mock_db_session.__aenter__.return_value = mock_db_session
            mock_db_session.__aexit__.return_value = None
            mock_db.return_value = mock_db_session

            # Mock repository with AsyncMock
            mock_repo = MagicMock()
            mock_session_obj = MagicMock()
            from unittest.mock import AsyncMock
            mock_repo.create_session = AsyncMock(return_value=mock_session_obj)

            with patch("src.bot.callbacks.SessionRepository", return_value=mock_repo):
                await _handle_resume_mode(mock_callback_update, mock_context, "session123:continue")

                # Check that session_id and mode were stored
                assert mock_context.user_data["resume_session_id"] == "session123"
                assert mock_context.user_data["resume_mode"] == "continue"
                assert mock_context.user_data["current_session"] == mock_session_obj

                # Check message
                mock_callback_update.callback_query.edit_message_text.assert_called_once()
                call_args = mock_callback_update.callback_query.edit_message_text.call_args
                assert "continued" in call_args[0][0]
                assert "Session resumed!" in call_args[0][0]
