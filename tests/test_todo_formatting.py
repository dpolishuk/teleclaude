"""Test todo list formatting."""
import pytest
from src.claude.formatting import (
    format_todos,
    TODO_ICON,
    TODO_COMPLETED,
    TODO_IN_PROGRESS,
    TODO_PENDING,
)


class TestFormatTodos:
    """Tests for format_todos function."""

    def test_shows_progress_header(self):
        """Header shows completion progress."""
        todos = [
            {"content": "Task 1", "status": "completed", "activeForm": "Doing 1"},
            {"content": "Task 2", "status": "pending", "activeForm": "Doing 2"},
        ]
        result = format_todos(todos)
        assert TODO_ICON in result
        assert "1/2" in result or "1 / 2" in result

    def test_completed_items_have_checkmark(self):
        """Completed items show ☑."""
        todos = [{"content": "Done task", "status": "completed", "activeForm": ""}]
        result = format_todos(todos)
        assert TODO_COMPLETED in result
        assert "Done task" in result

    def test_in_progress_uses_active_form(self):
        """In-progress items show activeForm text."""
        todos = [{"content": "Task", "status": "in_progress", "activeForm": "Doing task"}]
        result = format_todos(todos)
        assert TODO_IN_PROGRESS in result
        assert "Doing task" in result

    def test_pending_items_have_empty_box(self):
        """Pending items show ☐."""
        todos = [{"content": "Future task", "status": "pending", "activeForm": ""}]
        result = format_todos(todos)
        assert TODO_PENDING in result
        assert "Future task" in result

    def test_groups_subtasks(self):
        """Related tasks grouped with tree connectors."""
        todos = [
            {"content": "Main task", "status": "in_progress", "activeForm": "Working"},
            {"content": "Main task: subtask 1", "status": "pending", "activeForm": ""},
            {"content": "Main task: subtask 2", "status": "pending", "activeForm": ""},
        ]
        result = format_todos(todos)
        # Should have tree structure
        assert "├" in result or "└" in result

    def test_compact_mode_over_threshold(self):
        """Many items trigger compact mode."""
        todos = [
            {"content": f"Task {i}", "status": "completed", "activeForm": ""}
            for i in range(15)
        ]
        todos.append({"content": "Current", "status": "in_progress", "activeForm": "Working"})
        result = format_todos(todos)
        # Should collapse completed items
        assert "completed" in result.lower() or len(result.split("\n")) < 17

    def test_empty_todos(self):
        """Empty list returns empty string."""
        result = format_todos([])
        assert result == ""
