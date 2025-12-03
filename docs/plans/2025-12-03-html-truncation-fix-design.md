# HTML Truncation Fix Design

## Problem

HTML rendering breaks intermittently on long messages. Users see raw HTML tags like `<b>bold</b>` as literal text instead of rendered formatting. The issue worsens as messages grow longer.

## Root Cause

`safe_truncate_html()` in `src/claude/streaming.py` has two flaws:

1. **Cuts inside HTML entities** - Truncating `&amp;` mid-entity produces `&am` (garbage)
2. **Naive mid-tag detection** - The `first_gt`/`first_lt` logic fails to properly handle tags, leaving orphaned closing tags

## Solution

Replace naive truncation with entity-aware truncation that finds safe cut points.

### New Function: `find_safe_truncate_point()`

```python
def find_safe_truncate_point(text: str, target: int) -> int:
    """Find safe position to truncate, not inside entities or tags.

    Scans backwards from target to find position not inside:
    - HTML entity (&amp; &lt; etc.)
    - HTML tag (<b>, </code>, etc.)

    Returns position <= target that's safe to cut.
    """
    pos = target

    # Check if inside HTML entity (& without closing ;)
    amp_search_start = max(0, pos - 8)  # entities max ~8 chars
    amp_pos = text.rfind('&', amp_search_start, pos)
    if amp_pos != -1:
        semicolon_pos = text.find(';', amp_pos, pos + 1)
        if semicolon_pos == -1 or semicolon_pos >= pos:
            pos = amp_pos

    # Check if inside HTML tag (< without closing >)
    lt_pos = text.rfind('<', 0, pos)
    if lt_pos != -1:
        gt_pos = text.find('>', lt_pos, pos + 1)
        if gt_pos == -1 or gt_pos >= pos:
            pos = lt_pos

    # Nudge to natural boundary (newline or space)
    for boundary in ['\n', ' ']:
        bound_pos = text.rfind(boundary, max(0, pos - 50), pos)
        if bound_pos != -1:
            return bound_pos + 1

    return pos
```

### Updated `safe_truncate_html()`

```python
def safe_truncate_html(text: str, max_length: int, prefix: str = "") -> str:
    """Truncate HTML text safely without breaking tags or entities."""
    if len(text) <= max_length:
        return text

    # Reserve space for prefix and tag overhead
    tag_buffer = 60
    available = max_length - len(prefix) - tag_buffer
    if available < 50:
        available = max_length - len(prefix) - 20

    # Find safe truncation point (not inside entity or tag)
    target_point = max(0, len(text) - available)
    truncate_point = find_safe_truncate_point(text, target_point)

    truncated = text[truncate_point:]

    # Find tags that were open at truncation point
    if truncate_point > 0:
        prefix_text = text[:truncate_point]
        open_tags = find_open_tags(prefix_text)

        if open_tags:
            opening = "".join(f"<{tag}>" for tag in open_tags)
            truncated = opening + truncated

    # Balance any unclosed tags at the end
    balanced = balance_tags(truncated)

    return f"{prefix}{balanced}" if prefix else balanced
```

## Files Changed

| File | Change |
|------|--------|
| `src/claude/streaming.py` | Add `find_safe_truncate_point()`, update `safe_truncate_html()` |
| `tests/test_streaming.py` | Add unit tests |

## Edge Cases

| Case | Handling |
|------|----------|
| Text is all one giant tag | Returns from position 0 |
| Many nested tags | `find_open_tags` tracks nesting order |
| Entity at very start | Nudge-to-boundary finds safe spot |
| No natural boundary | Cut at safe point even if mid-word |

## Test Plan

```python
# find_safe_truncate_point tests
def test_safe_point_not_inside_entity():
    text = "Hello &amp; world"
    assert find_safe_truncate_point(text, 8) <= 6

def test_safe_point_not_inside_tag():
    text = "Hello <b>world</b>"
    assert find_safe_truncate_point(text, 7) <= 6

def test_safe_point_prefers_newline():
    text = "Line one\nLine two"
    assert find_safe_truncate_point(text, 12) == 9

def test_safe_point_prefers_space():
    text = "Hello beautiful world"
    assert find_safe_truncate_point(text, 10) == 7

# safe_truncate_html tests
def test_truncate_preserves_formatting():
    text = "<b>Bold</b> " * 500
    result = safe_truncate_html(text, 3800)
    assert "<b>" in result
    assert result.count("<b>") == result.count("</b>")

def test_truncate_doesnt_break_entities():
    text = "A &amp; B " * 500
    result = safe_truncate_html(text, 3800)
    assert "&am" not in result
```

## Manual Testing

1. Send prompt that generates 4000+ char response
2. Verify no garbled tags during streaming
3. Verify formatting renders correctly at end
