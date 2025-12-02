"""Test HTML utility functions."""
import re
from src.utils.html import detect_content_type, smart_truncate


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


class TestSmartTruncate:
    """Tests for smart_truncate function."""

    def test_no_truncation_under_limit(self):
        """Short content returned unchanged."""
        lines = ["line 1", "line 2", "line 3"]
        result = smart_truncate(lines, max_lines=10, interesting=[])
        assert result == "line 1\nline 2\nline 3"

    def test_shows_context_around_interesting(self):
        """Shows lines around interesting regions."""
        lines = [f"line {i}" for i in range(20)]
        result = smart_truncate(lines, max_lines=10, interesting=[10], context=2)
        assert "line 8" in result
        assert "line 10" in result
        assert "line 12" in result
        assert "line 0" not in result or "skipped" in result

    def test_merges_adjacent_regions(self):
        """Adjacent interesting regions merged."""
        lines = [f"line {i}" for i in range(30)]
        result = smart_truncate(lines, max_lines=15, interesting=[10, 12], context=2)
        # Should show 8-14 as one region, not split
        assert "line 10" in result
        assert "line 12" in result

    def test_head_tail_fallback(self):
        """No interesting lines uses head+tail."""
        lines = [f"line {i}" for i in range(50)]
        result = smart_truncate(lines, max_lines=20, interesting=[])
        assert "line 0" in result  # Head
        assert "line 49" in result  # Tail
        assert "skipped" in result.lower()

    def test_skip_indicator_shows_count(self):
        """Skip indicator shows line count."""
        lines = [f"line {i}" for i in range(100)]
        result = smart_truncate(lines, max_lines=20, interesting=[50], context=3)
        # Should indicate how many lines skipped
        assert re.search(r"\d+ lines", result)

    def test_enforces_max_lines_with_interesting(self):
        """Output never exceeds max_lines even with many interesting regions."""
        lines = [f"line {i}" for i in range(100)]
        result = smart_truncate(lines, max_lines=20, interesting=[10, 30, 50, 70], context=5)
        result_lines = result.split("\n")
        assert len(result_lines) <= 20, f"Expected <=20 lines, got {len(result_lines)}"

    def test_reduces_context_to_fit_max_lines(self):
        """Context is reduced when regions exceed max_lines."""
        lines = [f"line {i}" for i in range(100)]
        # With context=5, this would exceed max_lines=15
        result = smart_truncate(lines, max_lines=15, interesting=[10, 50], context=5)
        result_lines = result.split("\n")
        assert len(result_lines) <= 15
        # Should still include the interesting lines
        assert "line 10" in result
        assert "line 50" in result

    def test_selects_fewer_regions_if_needed(self):
        """Selects fewer regions when context reduction isn't enough."""
        lines = [f"line {i}" for i in range(100)]
        # Many regions with low max_lines should reduce region count
        result = smart_truncate(lines, max_lines=10, interesting=[5, 15, 25, 35, 45], context=2)
        result_lines = result.split("\n")
        assert len(result_lines) <= 10
