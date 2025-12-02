"""Test HTML utility functions."""
from src.utils.html import detect_content_type


class TestDetectContentType:
    """Tests for detect_content_type function."""

    def test_detects_git_diff(self):
        """Git diff header detected as diff."""
        content = "diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py"
        assert detect_content_type(content) == "diff"

    def test_detects_unified_diff(self):
        """Unified diff markers detected as diff."""
        content = "--- a/old.py\n+++ b/new.py\n@@ -1,3 +1,4 @@"
        assert detect_content_type(content) == "diff"

    def test_detects_plain_diff_lines(self):
        """Lines starting with +/- detected as diff."""
        content = " context\n-removed\n+added\n context"
        assert detect_content_type(content) == "diff"

    def test_ignores_increment_operators(self):
        """++ and -- operators not detected as diff."""
        content = "for (i = 0; i < n; i++) {\n  count++;\n}"
        assert detect_content_type(content) == "code"

    def test_detects_code_by_indentation(self):
        """Indented content detected as code."""
        content = "def foo():\n    return 42\n\nfoo()"
        assert detect_content_type(content) == "code"

    def test_plain_text_default(self):
        """Plain text returns plain."""
        content = "This is just some plain text."
        assert detect_content_type(content) == "plain"
