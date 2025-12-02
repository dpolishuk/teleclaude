"""HTML formatting utilities for Telegram messages.

Provides safe HTML formatting with automatic tag balancing.
All messages should use HTML parse_mode for consistency.
"""
import html as html_lib
import re
from typing import Literal


# Supported HTML tags for Telegram
SUPPORTED_TAGS = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
                  "code", "pre", "a", "tg-spoiler", "blockquote"}

# Regex for finding tags
TAG_PATTERN = re.compile(r"<(/?)([\w-]+)(?:\s[^>]*)?>")


def escape(text: str) -> str:
    """Escape HTML special characters for Telegram.

    Args:
        text: Raw text that may contain <, >, &

    Returns:
        Text safe for HTML rendering
    """
    return html_lib.escape(str(text))


def find_open_tags(text: str) -> list[str]:
    """Find all unclosed HTML tags in text.

    Returns list of tag names that are opened but not closed,
    in the order they were opened (for proper nesting).
    """
    tag_stack = []

    for match in TAG_PATTERN.finditer(text):
        is_closing = match.group(1) == "/"
        tag_name = match.group(2).lower()

        # Only track supported tags
        if tag_name not in SUPPORTED_TAGS:
            continue

        if is_closing:
            # Remove matching open tag from stack
            if tag_stack and tag_stack[-1] == tag_name:
                tag_stack.pop()
            # Handle mismatched tags - find and remove if exists
            elif tag_name in tag_stack:
                tag_stack.remove(tag_name)
        else:
            tag_stack.append(tag_name)

    return tag_stack


def balance_tags(text: str) -> str:
    """Balance HTML tags by closing any unclosed tags at the end.

    Args:
        text: HTML text that may have unclosed tags.

    Returns:
        Text with all tags properly closed.
    """
    open_tags = find_open_tags(text)

    if not open_tags:
        return text

    # Close tags in reverse order (LIFO for proper nesting)
    closing_tags = "".join(f"</{tag}>" for tag in reversed(open_tags))
    return text + closing_tags


def safe_html(text: str) -> str:
    """Escape text and balance any HTML tags.

    Use this for user-provided content that shouldn't contain HTML.

    Args:
        text: Raw text

    Returns:
        Escaped and balanced HTML
    """
    return balance_tags(escape(text))


# --- Helper functions for common formatting ---

def bold(text: str) -> str:
    """Wrap text in bold tags.

    Args:
        text: Text to make bold (will be escaped)

    Returns:
        <b>escaped text</b>
    """
    return f"<b>{escape(text)}</b>"


def italic(text: str) -> str:
    """Wrap text in italic tags.

    Args:
        text: Text to italicize (will be escaped)

    Returns:
        <i>escaped text</i>
    """
    return f"<i>{escape(text)}</i>"


def code(text: str) -> str:
    """Wrap text in inline code tags.

    Args:
        text: Text for inline code (will be escaped)

    Returns:
        <code>escaped text</code>
    """
    return f"<code>{escape(text)}</code>"


def pre(text: str, language: str = "") -> str:
    """Wrap text in preformatted block tags.

    Args:
        text: Text for code block (will be escaped)
        language: Optional language for syntax highlighting

    Returns:
        <pre>escaped text</pre> or <pre><code class="language-X">text</code></pre>
    """
    escaped = escape(text)
    if language:
        return f'<pre><code class="language-{escape(language)}">{escaped}</code></pre>'
    return f"<pre>{escaped}</pre>"


def link(text: str, url: str) -> str:
    """Create a hyperlink.

    Args:
        text: Link text (will be escaped)
        url: URL (will be escaped)

    Returns:
        <a href="url">text</a>
    """
    return f'<a href="{escape(url)}">{escape(text)}</a>'


def underline(text: str) -> str:
    """Wrap text in underline tags.

    Args:
        text: Text to underline (will be escaped)

    Returns:
        <u>escaped text</u>
    """
    return f"<u>{escape(text)}</u>"


def strike(text: str) -> str:
    """Wrap text in strikethrough tags.

    Args:
        text: Text to strike through (will be escaped)

    Returns:
        <s>escaped text</s>
    """
    return f"<s>{escape(text)}</s>"


def spoiler(text: str) -> str:
    """Wrap text in spoiler tags.

    Args:
        text: Text to hide as spoiler (will be escaped)

    Returns:
        <tg-spoiler>escaped text</tg-spoiler>
    """
    return f"<tg-spoiler>{escape(text)}</tg-spoiler>"


# --- Utility functions ---

def chunk_text(text: str, max_size: int = 3800) -> list[str]:
    """Split text into chunks respecting max size.

    Args:
        text: Text to split
        max_size: Maximum characters per chunk

    Returns:
        List of text chunks
    """
    if len(text) <= max_size:
        return [text]

    chunks = []
    current = ""

    for char in text:
        if len(current) >= max_size:
            chunks.append(current)
            current = ""
        current += char

    if current:
        chunks.append(current)

    return chunks


def truncate(text: str, max_len: int = 4096, suffix: str = "...") -> str:
    """Truncate text with suffix if too long.

    Args:
        text: Text to truncate
        max_len: Maximum length including suffix
        suffix: String to append when truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)] + suffix


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

    # Build regions around interesting lines with dynamic context reduction
    current_context = context
    merged: list[tuple[int, int]] = []

    while current_context >= 0:
        # Build regions with current context
        regions: list[tuple[int, int]] = []
        for idx in sorted(set(interesting)):
            start = max(0, idx - current_context)
            end = min(len(lines), idx + current_context + 1)
            regions.append((start, end))

        # Merge overlapping regions
        merged = []
        for start, end in regions:
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        # Calculate total lines needed (content + skip indicators)
        total_content_lines = sum(end - start for start, end in merged)
        skip_indicators = 0

        # Count skip indicators needed
        prev_end = 0
        for start, end in merged:
            if start > prev_end:
                skip_indicators += 1
            prev_end = end
        if prev_end < len(lines):
            skip_indicators += 1

        total_lines = total_content_lines + skip_indicators

        # If we fit within max_lines, use this result
        if total_lines <= max_lines:
            break

        # Otherwise reduce context or select fewer regions
        if current_context > 0:
            current_context -= 1
        else:
            # Context is 0, select fewer interesting regions
            # Prioritize regions in the middle or truncate to fit
            interesting = sorted(set(interesting))
            if len(interesting) > 1:
                # Remove every other region until we fit
                interesting = interesting[::2]
                current_context = 0  # Stay at 0 context but retry with fewer regions
                # Rebuild with reduced interesting list
                regions = []
                for idx in interesting:
                    start = max(0, idx - current_context)
                    end = min(len(lines), idx + current_context + 1)
                    regions.append((start, end))
                merged = []
                for start, end in regions:
                    if merged and start <= merged[-1][1] + 1:
                        merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                    else:
                        merged.append((start, end))
                break
            else:
                # Only one region left, can't reduce further
                break

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
