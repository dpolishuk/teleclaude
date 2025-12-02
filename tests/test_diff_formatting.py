"""Test diff formatting."""
from src.claude.formatting import format_diff, DIFF_ADD, DIFF_DEL, FILE_ICON


class TestFormatDiff:
    """Tests for format_diff function."""

    def test_adds_emoji_to_added_lines(self):
        """Added lines get ✅ prefix."""
        diff = "+new line"
        result = format_diff(diff)
        assert DIFF_ADD in result
        assert "new line" in result

    def test_adds_emoji_to_removed_lines(self):
        """Removed lines get ❌ prefix."""
        diff = "-old line"
        result = format_diff(diff)
        assert DIFF_DEL in result
        assert "old line" in result

    def test_context_lines_indented(self):
        """Context lines get spacing to align."""
        diff = " context line"
        result = format_diff(diff)
        assert "context line" in result
        # Should have leading space for alignment
        assert result.strip().startswith(" ") or "  " in result

    def test_extracts_file_header(self):
        """File path extracted from diff header."""
        diff = "diff --git a/src/main.py b/src/main.py\n--- a/src/main.py\n+++ b/src/main.py"
        result = format_diff(diff)
        assert FILE_ICON in result
        assert "src/main.py" in result

    def test_formats_hunk_header(self):
        """Hunk header rendered as separator."""
        diff = "@@ -10,5 +10,6 @@ def foo():"
        result = format_diff(diff)
        # Should show line number context
        assert "10" in result or "──" in result

    def test_multi_file_diff(self):
        """Multiple files each get headers."""
        diff = """diff --git a/file1.py b/file1.py
--- a/file1.py
+++ b/file1.py
+line1
diff --git a/file2.py b/file2.py
--- a/file2.py
+++ b/file2.py
+line2"""
        result = format_diff(diff)
        assert "file1.py" in result
        assert "file2.py" in result

    def test_returns_html_safe(self):
        """Output is HTML escaped."""
        diff = "+<script>alert('xss')</script>"
        result = format_diff(diff)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
