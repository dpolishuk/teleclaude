# HTML Rendering Improvements Design

## Overview

Improve TeleClaude's HTML rendering for Telegram to better display:
1. **Code diffs** - Unified diff style with emoji indicators
2. **Code snippets** - Smart truncation showing context around interesting parts
3. **Todo lists** - Hierarchical grouping with indentation

## Design Decisions

| Area | Decision |
|------|----------|
| Code diffs | Unified diff style (`+`/`-` lines) with emoji indicators |
| Code snippets | Smart truncation showing context around interesting parts |
| Todos | Hierarchical grouping with indentation |
| Visual style | Emoji indicators (`✅`, `❌`, `📄`, `🔧`) used sparingly |
| Streaming | Real-time formatting as content arrives |

## Telegram HTML Limitations

- Supported tags: `<b>`, `<i>`, `<u>`, `<s>`, `<code>`, `<pre>`, `<a>`, `<blockquote>`, `<tg-spoiler>`
- `<pre><code class="language-X">` for syntax highlighting (but Telegram renders all code the same - no colored syntax)
- No colors, no background colors, no custom fonts
- Max 100 markup elements per message, 4096 chars limit

## Architecture

```
src/claude/formatting.py      # Existing - extend with new formatters
├── format_diff()             # NEW: unified diff with +/- emoji
├── format_code_block()       # NEW: smart truncation with context
├── format_todos()            # MODIFY: add hierarchy support
└── format_tool_result()      # MODIFY: detect diffs/code, route to formatters

src/utils/html.py             # Existing - add helpers
├── smart_truncate()          # NEW: context-aware truncation
└── detect_content_type()     # NEW: identify diff vs code vs plain
```

---

## Code Diff Formatting

### Detection

Identify diff content by patterns:
- Lines starting with `+++ `, `--- `, `@@ `
- Lines starting with `+` or `-` (excluding `++`/`--` operators)
- Git diff headers like `diff --git`

### Format Output

```
📄 src/config.py

  def load_config():
❌    old_value = 42
✅    new_value = 100
      return config
```

### Rules

- `❌` prefix for removed lines (red mental association)
- `✅` prefix for added lines (green mental association)
- Context lines (unchanged) get 2-space indent to align
- File path shown as header with `📄` when available
- Hunk headers (`@@ -10,5 +10,6 @@`) rendered as subtle separator: `── line 10 ──`

### Streaming Behavior

- Detect diff mode when first `diff --git` or `--- ` line arrives
- Buffer until we have complete line (wait for `\n`)
- Format each line as it completes

### Edge Cases

- Multi-file diffs: Show `📄` header for each file
- Binary files: Show `📄 file.png (binary)`
- Large diffs: Apply smart truncation

---

## Smart Code Truncation

### Problem

Long code blocks exceed Telegram's 4096 char limit or become unreadable.

### Smart Context Detection

Identify "interesting" regions:
1. **Error locations**: Lines containing `error`, `Error`, `Exception`, line numbers from stack traces
2. **Change markers**: Lines with `+`, `-`, `>`, `<` in diffs
3. **Search matches**: Lines containing the grep/search pattern
4. **Function boundaries**: `def `, `function `, `class ` declarations

### Truncation Algorithm

```
Input: 200 lines of code, max display: 40 lines
Interesting lines found: [45, 46, 47, 120, 121]

Output:
  ┌─ lines 1-5 ─────────────
  │ first 5 lines...
  ├─ ... 37 lines skipped ...
  │
  │ lines 43-50 (context around match)
  │ interesting content here
  │
  ├─ ... 67 lines skipped ...
  │
  │ lines 118-125 (context around match)
  │ more interesting content
  │
  └─ ... 75 lines skipped ─
```

### Rules

- **Context window**: Show 3 lines before and after each interesting region
- **Fallback** (no interesting regions detected): Head + tail approach - first 15 lines, skip indicator, last 10 lines
- Use `┌`, `│`, `├`, `└` box-drawing for structure
- Skip indicators show count: `├─ ... 37 lines skipped ...`
- All inside `<pre>` block for monospace alignment

---

## Hierarchical Todo Display

### Problem

Flat todo lists don't show task relationships or sub-steps.

### Hierarchy Detection

- Parse todo `content` for indentation hints or numbered prefixes
- Group consecutive related items (e.g., "Fix bug" followed by "Write test for fix")
- Detect parent-child by common prefixes or explicit markers

### Format Output

```
📋 Progress: 4/7

☑ Research Telegram HTML limits
☑ Design diff formatting
  ├ ☑ Detection patterns
  └ ☑ Emoji indicators
⏳ Implement formatters
  ├ ☐ format_diff()
  └ ☐ smart_truncate()
☐ Write tests
```

### Visual Elements

- `📋` header with progress count
- Tree connectors `├`, `└` for sub-items (2-space indent)
- Status symbols unchanged: `☐` pending, `⏳` in-progress, `☑` completed
- In-progress item uses `activeForm` text

### Grouping Rules

1. Items with same prefix → group under first item
2. Sequential items on same topic → infer hierarchy
3. Explicit numbering (1.1, 1.2) → nested structure

### Streaming Behavior

- Re-render entire todo block on each `TodoWrite` update
- Replace previous todo message section (not append)

### Compact Mode (when > 10 items)

- Show only in-progress and next 2 pending items expanded
- Collapse completed items: `☑ 5 completed tasks`

---

## Implementation Details

### File Changes Summary

| File | Changes |
|------|---------|
| `src/claude/formatting.py` | Add `format_diff()`, `format_code_block()`, modify `format_todos()`, `format_tool_result()` |
| `src/utils/html.py` | Add `smart_truncate()`, `detect_content_type()` |
| `src/claude/streaming.py` | Update to use new formatters, handle diff line buffering |

### New Functions

```python
# src/claude/formatting.py

def format_diff(content: str) -> str:
    """Format unified diff with emoji indicators."""

def format_code_block(content: str, context_hints: list[str] = None) -> str:
    """Format code with smart truncation around interesting regions."""

# src/utils/html.py

def detect_content_type(text: str) -> Literal["diff", "code", "plain"]:
    """Detect if content is a diff, code block, or plain text."""

def smart_truncate(lines: list[str], max_lines: int,
                   interesting: list[int], context: int = 3) -> str:
    """Truncate showing context around interesting line numbers."""
```

### Constants

```python
# Limits
MAX_CODE_LINES = 50
MAX_DIFF_LINES = 60
CONTEXT_LINES = 3
COMPACT_TODO_THRESHOLD = 10

# Emoji
DIFF_ADD = "✅"
DIFF_DEL = "❌"
FILE_ICON = "📄"
TODO_ICON = "📋"
```

### Backward Compatibility

- Existing `format_tool_call()` and `format_status()` unchanged
- `format_tool_result()` gains smarter routing but same signature

---

## Error Handling & Edge Cases

### Edge Cases

| Scenario | Solution |
|----------|----------|
| Malformed diff (missing headers) | Fall back to plain `<pre>` block |
| Mixed content (diff + prose) | Detect boundaries, format each section separately |
| Nested code in code | Escape inner backticks, single `<pre>` block |
| Empty interesting regions | Use head+tail fallback truncation |
| Unicode in code | Preserve as-is, only escape HTML entities |
| Very long single line | Wrap at 80 chars with `↩` indicator |

### Streaming Edge Cases

| Scenario | Solution |
|----------|----------|
| Partial diff line | Buffer until `\n`, then format |
| Diff detection mid-stream | Re-render from start with diff formatting |
| Todo update during diff | Keep sections separate, update only todo portion |

### Character Limit Handling

- Telegram limit: 4096 chars per message
- Reserve 200 chars for message overhead (tags, structure)
- If formatted output > 3800 chars → apply truncation
- If still too long after truncation → split into multiple messages

### Graceful Degradation

```
try format_diff()
  → on failure → format_code_block()
    → on failure → plain <pre> with basic truncation
```

---

## Testing Strategy

### Unit Tests (`tests/test_formatting.py`)

```python
# Diff formatting
test_format_diff_basic_add_remove()      # +/- lines get emoji
test_format_diff_with_file_header()      # 📄 header extraction
test_format_diff_multi_file()            # Multiple file sections
test_format_diff_malformed_fallback()    # Graceful degradation

# Smart truncation
test_smart_truncate_with_matches()       # Shows context around hits
test_smart_truncate_no_matches()         # Falls back to head+tail
test_smart_truncate_overlapping()        # Merges adjacent regions
test_smart_truncate_under_limit()        # No truncation needed

# Content detection
test_detect_content_type_diff()          # Identifies diffs
test_detect_content_type_code()          # Identifies code blocks
test_detect_content_type_plain()         # Default to plain

# Todo hierarchy
test_format_todos_with_subtasks()        # Tree rendering
test_format_todos_compact_mode()         # >10 items collapses
test_format_todos_progress_count()       # 📋 4/7 header
```

### Integration Tests (`tests/test_streaming.py`)

```python
test_stream_diff_formatted_realtime()    # Diff formatted as it streams
test_stream_long_code_truncated()        # Truncation during stream
test_stream_todo_updates_section()       # Todo re-renders correctly
```

### Manual Testing Checklist

- [ ] Send real Claude edit → verify diff renders with ✅/❌
- [ ] Request large file read → verify smart truncation
- [ ] Multi-step task → verify todo hierarchy displays
- [ ] Exceed 4096 chars → verify message splits cleanly
