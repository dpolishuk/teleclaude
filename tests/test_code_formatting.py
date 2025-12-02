"""Test code block formatting."""
import pytest
from src.claude.formatting import format_code_block, MAX_CODE_LINES


class TestFormatCodeBlock:
    """Tests for format_code_block function."""

    def test_short_code_unchanged(self):
        """Code under limit returned in pre block."""
        code = "def foo():\n    return 42"
        result = format_code_block(code)
        assert "<pre>" in result
        assert "def foo():" in result
        assert "return 42" in result

    def test_long_code_truncated(self):
        """Code over limit is truncated."""
        code = "\n".join([f"line {i}" for i in range(100)])
        result = format_code_block(code)
        assert "skipped" in result.lower()

    def test_shows_context_around_errors(self):
        """Error lines get context."""
        lines = [f"line {i}" for i in range(100)]
        lines[50] = "    raise ValueError('error here')"
        code = "\n".join(lines)
        result = format_code_block(code, context_hints=["error"])
        assert "ValueError" in result
        assert "line 48" in result or "line 52" in result  # Context shown

    def test_shows_context_around_patterns(self):
        """Custom patterns get context."""
        lines = [f"line {i}" for i in range(100)]
        lines[30] = "# TODO: fix this"
        code = "\n".join(lines)
        result = format_code_block(code, context_hints=["TODO"])
        assert "TODO" in result

    def test_html_escaped(self):
        """HTML in code is escaped."""
        code = "<div>test</div>"
        result = format_code_block(code)
        assert "&lt;div&gt;" in result
        assert "<div>" not in result.replace("<pre>", "").replace("</pre>", "")

    def test_empty_code_handled(self):
        """Empty code returns empty pre block."""
        result = format_code_block("")
        assert "<pre>" in result
