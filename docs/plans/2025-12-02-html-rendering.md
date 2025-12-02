# HTML Rendering Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve Telegram HTML rendering with emoji-annotated diffs, smart code truncation, and hierarchical todo display.

**Architecture:** Extend existing `src/claude/formatting.py` with new formatters. Add helpers to `src/utils/html.py`. The `MessageStreamer` continues to call formatters; formatters now produce richer output. TDD throughout.

**Tech Stack:** Python 3.10+, python-telegram-bot, pytest, asyncio

---

## Task 1: Add Content Detection Helper

**Files:**
- Modify: `src/utils/html.py`
- Test: `tests/test_html_utils.py` (create)

**Step 1: Write the failing test**

Create `tests/test_html_utils.py`:

```python
"""Test HTML utility functions."""
import pytest
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_html_utils.py -v`
Expected: FAIL with "cannot import name 'detect_content_type'"

**Step 3: Write minimal implementation**

Add to `src/utils/html.py`:

```python
import re
from typing import Literal


def detect_content_type(text: str) -> Literal["diff", "code", "plain"]:
    """Detect if content is a diff, code block, or plain text.

    Args:
        text: Content to analyze

    Returns:
        "diff" for unified diffs, "code" for code blocks, "plain" otherwise
    """
    lines = text.split("\n")

    # Check for diff indicators
    diff_markers = 0
    for line in lines[:20]:  # Check first 20 lines
        # Git diff header
        if line.startswith("diff --git "):
            return "diff"
        # Unified diff file markers
        if line.startswith("--- ") or line.startswith("+++ "):
            diff_markers += 1
        # Hunk header
        if line.startswith("@@ ") and " @@" in line:
            return "diff"
        # Added/removed lines (but not ++ or --)
        if re.match(r"^[+-][^+-]", line):
            diff_markers += 1

    if diff_markers >= 2:
        return "diff"

    # Check for code indicators
    code_indicators = 0
    for line in lines[:20]:
        # Common code patterns
        if re.match(r"^\s{2,}", line):  # Indentation
            code_indicators += 1
        if re.search(r"(def |class |function |const |let |var |import |from )", line):
            code_indicators += 2
        if re.search(r"[{}\[\]();]$", line.rstrip()):
            code_indicators += 1

    if code_indicators >= 3:
        return "code"

    return "plain"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_html_utils.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add src/utils/html.py tests/test_html_utils.py
git commit -m "feat(html): add detect_content_type helper"
```

---

## Task 2: Add Smart Truncation Helper

**Files:**
- Modify: `src/utils/html.py`
- Modify: `tests/test_html_utils.py`

**Step 1: Write the failing test**

Add to `tests/test_html_utils.py`:

```python
from src.utils.html import smart_truncate


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_html_utils.py::TestSmartTruncate -v`
Expected: FAIL with "cannot import name 'smart_truncate'"

**Step 3: Write minimal implementation**

Add to `src/utils/html.py`:

```python
def smart_truncate(
    lines: list[str],
    max_lines: int,
    interesting: list[int],
    context: int = 3
) -> str:
    """Truncate showing context around interesting line numbers.

    Args:
        lines: List of text lines
        max_lines: Maximum lines to output
        interesting: Line indices (0-based) to show context around
        context: Lines before/after each interesting line

    Returns:
        Truncated text with skip indicators
    """
    if len(lines) <= max_lines:
        return "\n".join(lines)

    if not interesting:
        # Head + tail fallback
        head_lines = max_lines * 3 // 5  # 60% head
        tail_lines = max_lines - head_lines - 1  # Rest for tail + skip line
        head = lines[:head_lines]
        tail = lines[-tail_lines:] if tail_lines > 0 else []
        skipped = len(lines) - head_lines - tail_lines
        return "\n".join(head) + f"\n├─ ... {skipped} lines skipped ...\n" + "\n".join(tail)

    # Build regions around interesting lines
    regions: list[tuple[int, int]] = []
    for idx in sorted(set(interesting)):
        start = max(0, idx - context)
        end = min(len(lines), idx + context + 1)
        regions.append((start, end))

    # Merge overlapping regions
    merged: list[tuple[int, int]] = []
    for start, end in regions:
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # Build output
    output_parts: list[str] = []
    prev_end = 0

    for start, end in merged:
        if start > prev_end:
            skipped = start - prev_end
            output_parts.append(f"├─ ... {skipped} lines skipped ...")
        output_parts.extend(lines[start:end])
        prev_end = end

    if prev_end < len(lines):
        skipped = len(lines) - prev_end
        output_parts.append(f"└─ ... {skipped} lines skipped ...")

    return "\n".join(output_parts)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_html_utils.py::TestSmartTruncate -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add src/utils/html.py tests/test_html_utils.py
git commit -m "feat(html): add smart_truncate helper"
```

---

## Task 3: Add Diff Formatter

**Files:**
- Modify: `src/claude/formatting.py`
- Create: `tests/test_diff_formatting.py`

**Step 1: Write the failing test**

Create `tests/test_diff_formatting.py`:

```python
"""Test diff formatting."""
import pytest
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_diff_formatting.py -v`
Expected: FAIL with "cannot import name 'format_diff'"

**Step 3: Write minimal implementation**

Add to `src/claude/formatting.py`:

```python
import re

# Diff formatting constants
DIFF_ADD = "✅"
DIFF_DEL = "❌"
FILE_ICON = "📄"


def format_diff(content: str) -> str:
    """Format unified diff with emoji indicators.

    Args:
        content: Unified diff text

    Returns:
        HTML-formatted diff with ✅/❌ markers
    """
    lines = content.split("\n")
    output: list[str] = []
    current_file: str | None = None

    for line in lines:
        # Git diff header - extract filename
        if line.startswith("diff --git "):
            match = re.search(r"b/(.+)$", line)
            if match:
                current_file = match.group(1)
                output.append(f"\n{FILE_ICON} <b>{escape_html(current_file)}</b>\n")
            continue

        # Skip --- and +++ headers (already got filename)
        if line.startswith("--- ") or line.startswith("+++ "):
            continue

        # Hunk header
        if line.startswith("@@ ") and " @@" in line:
            match = re.search(r"@@ -(\d+)", line)
            line_num = match.group(1) if match else "?"
            output.append(f"<code>── line {line_num} ──</code>")
            continue

        # Added line (but not +++)
        if line.startswith("+") and not line.startswith("+++"):
            output.append(f"{DIFF_ADD} <code>{escape_html(line[1:])}</code>")
            continue

        # Removed line (but not ---)
        if line.startswith("-") and not line.startswith("---"):
            output.append(f"{DIFF_DEL} <code>{escape_html(line[1:])}</code>")
            continue

        # Context line
        if line.startswith(" "):
            output.append(f"   <code>{escape_html(line[1:])}</code>")
            continue

        # Other lines (empty, etc)
        if line.strip():
            output.append(f"<code>{escape_html(line)}</code>")

    return "\n".join(output)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_diff_formatting.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add src/claude/formatting.py tests/test_diff_formatting.py
git commit -m "feat(formatting): add format_diff with emoji indicators"
```

---

## Task 4: Add Code Block Formatter

**Files:**
- Modify: `src/claude/formatting.py`
- Create: `tests/test_code_formatting.py`

**Step 1: Write the failing test**

Create `tests/test_code_formatting.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_code_formatting.py -v`
Expected: FAIL with "cannot import name 'format_code_block'"

**Step 3: Write minimal implementation**

Add to `src/claude/formatting.py`:

```python
# Code formatting constants
MAX_CODE_LINES = 50
CONTEXT_LINES = 3

# Import at top of file
from src.utils.html import smart_truncate


def format_code_block(content: str, context_hints: list[str] | None = None) -> str:
    """Format code with smart truncation around interesting regions.

    Args:
        content: Code text
        context_hints: Patterns to search for when truncating (e.g., ["error", "TODO"])

    Returns:
        HTML-formatted code block
    """
    if not content.strip():
        return "<pre></pre>"

    lines = content.split("\n")

    if len(lines) <= MAX_CODE_LINES:
        return f"<pre>{escape_html(content)}</pre>"

    # Find interesting line indices
    interesting: list[int] = []
    hints = context_hints or ["error", "Error", "Exception", "TODO", "FIXME"]

    for i, line in enumerate(lines):
        for hint in hints:
            if hint.lower() in line.lower():
                interesting.append(i)
                break

    # Smart truncate
    truncated = smart_truncate(
        lines,
        max_lines=MAX_CODE_LINES,
        interesting=interesting,
        context=CONTEXT_LINES
    )

    return f"<pre>{escape_html(truncated)}</pre>"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_code_formatting.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add src/claude/formatting.py tests/test_code_formatting.py
git commit -m "feat(formatting): add format_code_block with smart truncation"
```

---

## Task 5: Update format_tool_result to Route Content

**Files:**
- Modify: `src/claude/formatting.py`
- Modify: `tests/test_diff_formatting.py`

**Step 1: Write the failing test**

Add to `tests/test_diff_formatting.py`:

```python
from src.claude.formatting import format_tool_result


class TestFormatToolResultRouting:
    """Tests for format_tool_result content routing."""

    def test_routes_diff_content(self):
        """Diff content uses format_diff."""
        content = "diff --git a/file.py b/file.py\n+added line"
        result = format_tool_result(content)
        assert DIFF_ADD in result  # Uses diff formatter

    def test_routes_code_content(self):
        """Code content uses format_code_block."""
        content = "def foo():\n    return 42\n\nclass Bar:\n    pass"
        result = format_tool_result(content)
        assert "<pre>" in result

    def test_error_flag_still_works(self):
        """Error flag adds error indicator."""
        content = "Something failed"
        result = format_tool_result(content, is_error=True)
        assert "✗" in result

    def test_plain_text_in_pre(self):
        """Plain text wrapped in pre."""
        content = "Just some output text"
        result = format_tool_result(content)
        assert "<pre>" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_diff_formatting.py::TestFormatToolResultRouting -v`
Expected: FAIL - diff content not routed to format_diff

**Step 3: Modify implementation**

Update `format_tool_result` in `src/claude/formatting.py`:

```python
from src.utils.html import detect_content_type


def format_tool_result(content: str | list | None, is_error: bool = False) -> str:
    """Format a tool result in minimalistic style.

    Routes content to appropriate formatter based on content type detection.

    Args:
        content: Tool result content
        is_error: Whether this is an error result

    Returns:
        Formatted HTML string for Telegram
    """
    if content is None:
        return ""

    # Convert list/structured content to string
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                text_parts.append(str(item["text"]))
            else:
                text_parts.append(str(item))
        result_text = "\n".join(text_parts)
    else:
        result_text = str(content)

    result_text = result_text.strip()

    if not result_text:
        return ""

    # Detect content type and route to formatter
    content_type = detect_content_type(result_text)

    if is_error:
        # Error output - simple pre with error marker
        truncated = _truncate_result(result_text, 1500)
        return f"\n<pre>✗ {escape_html(truncated)}</pre>\n"

    if content_type == "diff":
        return f"\n{format_diff(result_text)}\n"

    if content_type == "code":
        return f"\n{format_code_block(result_text)}\n"

    # Plain text - use simple pre
    truncated = _truncate_result(result_text, 1500)
    return f"\n<pre>{escape_html(truncated)}</pre>\n"


def _truncate_result(text: str, max_len: int) -> str:
    """Truncate result text with line-aware indicator."""
    if len(text) <= max_len:
        return text

    lines = text.split("\n")
    truncated = text[:max_len]
    last_newline = truncated.rfind("\n")
    if last_newline > max_len // 2:
        truncated = truncated[:last_newline]
    remaining = len(lines) - truncated.count("\n") - 1
    if remaining > 0:
        return f"{truncated}\n⋯ {remaining} more lines"
    return f"{truncated}…"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_diff_formatting.py::TestFormatToolResultRouting -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add src/claude/formatting.py tests/test_diff_formatting.py
git commit -m "feat(formatting): route tool results to type-specific formatters"
```

---

## Task 6: Add Hierarchical Todo Formatting

**Files:**
- Modify: `src/claude/formatting.py`
- Create: `tests/test_todo_formatting.py`

**Step 1: Write the failing test**

Create `tests/test_todo_formatting.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_todo_formatting.py -v`
Expected: Some tests FAIL (existing format_todos doesn't have all features)

**Step 3: Update implementation**

Replace `format_todos` in `src/claude/formatting.py`:

```python
# Todo constants (update existing)
TODO_COMPLETED = "☑"
TODO_IN_PROGRESS = "⏳"
TODO_PENDING = "☐"
TODO_ICON = "📋"
COMPACT_TODO_THRESHOLD = 10


def format_todos(todos: list[dict]) -> str:
    """Format a todo list with hierarchy and progress.

    Args:
        todos: List of todo items with 'content', 'status', and optional 'activeForm'

    Returns:
        Formatted HTML string with checkbox-style todos
    """
    if not todos:
        return ""

    # Calculate progress
    completed = sum(1 for t in todos if t.get("status") == "completed")
    total = len(todos)

    lines = [f"{TODO_ICON} <b>Progress: {completed}/{total}</b>\n"]

    # Detect parent-child relationships
    groups = _group_todos(todos)

    # Compact mode if too many items
    if total > COMPACT_TODO_THRESHOLD:
        lines.extend(_format_compact_todos(groups))
    else:
        lines.extend(_format_full_todos(groups))

    return "\n".join(lines)


def _group_todos(todos: list[dict]) -> list[tuple[dict, list[dict]]]:
    """Group todos by detecting parent-child relationships.

    Returns list of (parent, children) tuples.
    """
    groups: list[tuple[dict, list[dict]]] = []
    i = 0

    while i < len(todos):
        parent = todos[i]
        children: list[dict] = []
        parent_content = parent.get("content", "").lower()

        # Look for children (items with parent content as prefix)
        j = i + 1
        while j < len(todos):
            child_content = todos[j].get("content", "").lower()
            # Check if child starts with parent content or has ": " pattern
            if (child_content.startswith(parent_content + ":") or
                child_content.startswith(parent_content + " -")):
                children.append(todos[j])
                j += 1
            else:
                break

        groups.append((parent, children))
        i = j if children else i + 1

    return groups


def _format_full_todos(groups: list[tuple[dict, list[dict]]]) -> list[str]:
    """Format todos with full hierarchy."""
    lines: list[str] = []

    for parent, children in groups:
        lines.append(_format_todo_item(parent))

        for idx, child in enumerate(children):
            is_last = idx == len(children) - 1
            connector = "└" if is_last else "├"
            lines.append(f"  {connector} {_format_todo_item(child, inline=True)}")

    return lines


def _format_compact_todos(groups: list[tuple[dict, list[dict]]]) -> list[str]:
    """Format todos in compact mode."""
    lines: list[str] = []

    completed_count = 0
    in_progress_shown = False
    pending_shown = 0

    for parent, children in groups:
        status = parent.get("status", "pending")

        if status == "completed":
            completed_count += 1
            for child in children:
                if child.get("status") == "completed":
                    completed_count += 1
        elif status == "in_progress":
            if not in_progress_shown:
                lines.append(_format_todo_item(parent))
                for idx, child in enumerate(children):
                    is_last = idx == len(children) - 1
                    connector = "└" if is_last else "├"
                    lines.append(f"  {connector} {_format_todo_item(child, inline=True)}")
                in_progress_shown = True
        elif status == "pending" and pending_shown < 2:
            lines.append(_format_todo_item(parent))
            pending_shown += 1

    if completed_count > 0:
        lines.insert(0, f"{TODO_COMPLETED} <i>{completed_count} completed tasks</i>")

    return lines


def _format_todo_item(todo: dict, inline: bool = False) -> str:
    """Format a single todo item."""
    content = todo.get("content", "")
    status = todo.get("status", "pending")

    if status == "completed":
        symbol = TODO_COMPLETED
    elif status == "in_progress":
        symbol = TODO_IN_PROGRESS
        active_form = todo.get("activeForm")
        if active_form:
            content = active_form
    else:
        symbol = TODO_PENDING

    if inline:
        return f"{symbol} {escape_html(content)}"
    return f"{symbol} {escape_html(content)}"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_todo_formatting.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add src/claude/formatting.py tests/test_todo_formatting.py
git commit -m "feat(formatting): add hierarchical todo display with progress"
```

---

## Task 7: Integration - Update Streaming to Use New Formatters

**Files:**
- Modify: `src/claude/streaming.py`
- Modify: `tests/test_streaming.py`

**Step 1: Write the failing test**

Add to `tests/test_streaming.py`:

```python
from src.claude.streaming import MessageStreamer


class TestStreamerFormatting:
    """Tests for streamer formatting integration."""

    @pytest.mark.asyncio
    async def test_streamer_formats_diff_content(self, mock_message):
        """Diff content in streamer uses diff formatting."""
        streamer = MessageStreamer(mock_message, throttle_ms=10)
        streamer.current_text = "diff --git a/f.py b/f.py\n+added"

        display = streamer._get_display_text()

        # Should have diff emoji
        assert "✅" in display or "❌" in display or "📄" in display

    @pytest.mark.asyncio
    async def test_streamer_handles_long_diff(self, mock_message):
        """Long diff content is truncated."""
        streamer = MessageStreamer(mock_message, throttle_ms=10, chunk_size=500)
        lines = ["diff --git a/f.py b/f.py"] + [f"+line {i}" for i in range(100)]
        streamer.current_text = "\n".join(lines)

        display = streamer._get_display_text()

        assert len(display) <= 600  # chunk_size + buffer
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_streaming.py::TestStreamerFormatting -v`
Expected: FAIL - streamer doesn't use diff formatting yet

**Step 3: Modify implementation**

The current `MessageStreamer._get_display_text()` already handles HTML. The formatters are called from the handler layer (where `format_tool_result` is invoked), not from the streamer itself. The streamer just handles raw text accumulation and tag balancing.

Actually, reviewing the architecture, the formatting happens before text is appended to the streamer. So this integration test should verify that when formatted text (with diff emojis) is passed to the streamer, it's preserved correctly.

Update the test to reflect this:

```python
class TestStreamerFormatting:
    """Tests for streamer formatting integration."""

    @pytest.mark.asyncio
    async def test_streamer_preserves_diff_formatting(self, mock_message):
        """Streamer preserves pre-formatted diff content."""
        streamer = MessageStreamer(mock_message, throttle_ms=10)
        # Pre-formatted content (as it would come from format_diff)
        streamer.current_text = "📄 <b>file.py</b>\n✅ <code>added line</code>"

        display = streamer._get_display_text()

        assert "📄" in display
        assert "✅" in display
        assert "<b>file.py</b>" in display

    @pytest.mark.asyncio
    async def test_streamer_truncates_long_formatted_content(self, mock_message):
        """Long formatted content is truncated safely."""
        streamer = MessageStreamer(mock_message, throttle_ms=10, chunk_size=200)
        # Long pre-formatted content
        lines = ["📄 <b>file.py</b>"] + [f"✅ <code>line {i}</code>" for i in range(50)]
        streamer.current_text = "\n".join(lines)

        display = streamer._get_display_text()

        assert len(display) <= 300  # chunk_size + buffer for tags
        # Tags should be balanced
        assert display.count("<code>") == display.count("</code>")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_streaming.py::TestStreamerFormatting -v`
Expected: PASS (existing tag balancing handles this)

**Step 5: Commit**

```bash
git add tests/test_streaming.py
git commit -m "test(streaming): verify formatter integration with streamer"
```

---

## Task 8: Run Full Test Suite

**Files:**
- None (verification only)

**Step 1: Run all tests**

```bash
pytest tests/ -v --tb=short
```

Expected: All new tests pass, existing tests still pass

**Step 2: Run linting**

```bash
ruff check src/claude/formatting.py src/utils/html.py
```

Expected: No errors

**Step 3: Fix any issues found**

If tests fail, debug and fix. If linting errors, fix them.

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve test/lint issues"
```

---

## Task 9: Update Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update CLAUDE.md**

Add to the "Message Formatting" section in `CLAUDE.md`:

```markdown
### Message Formatting
- Minimalistic Claude Code style with `⏵` symbol for tool calls
- Compact inline format: `⏵ Tool filename` or `⏵ Command args`
- Smart HTML tag balancing for streamed messages
- Tool result formatting with error indicators
- **Code diffs**: Unified diff style with ✅ (added) / ❌ (removed) emoji indicators
- **Smart truncation**: Long code shows context around errors, matches, and interesting regions
- **Hierarchical todos**: Tree structure with 📋 progress header, compact mode for >10 items
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with new formatting features"
```

---

## Task 10: Final Verification and Push

**Files:**
- None (verification only)

**Step 1: Run full test suite one more time**

```bash
pytest tests/ -v
```

**Step 2: Check git status**

```bash
git status
git log --oneline -10
```

**Step 3: Push branch**

```bash
git push origin feature/html-rendering
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Content detection helper | `src/utils/html.py`, `tests/test_html_utils.py` |
| 2 | Smart truncation helper | `src/utils/html.py`, `tests/test_html_utils.py` |
| 3 | Diff formatter | `src/claude/formatting.py`, `tests/test_diff_formatting.py` |
| 4 | Code block formatter | `src/claude/formatting.py`, `tests/test_code_formatting.py` |
| 5 | Route tool results | `src/claude/formatting.py`, `tests/test_diff_formatting.py` |
| 6 | Hierarchical todos | `src/claude/formatting.py`, `tests/test_todo_formatting.py` |
| 7 | Streaming integration | `tests/test_streaming.py` |
| 8 | Full test suite | - |
| 9 | Documentation | `CLAUDE.md` |
| 10 | Final push | - |

Total: ~10 commits, each small and focused.
