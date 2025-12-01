"""Streaming responses to Telegram with throttling and HTML tag balancing."""
import asyncio
import re
import time
from typing import Optional

from telegram import Message
from telegram.error import BadRequest, TimedOut

from src.utils.html import escape, balance_tags, find_open_tags

# Re-export for backwards compatibility
escape_html = escape
balance_html = balance_tags


def safe_truncate_html(text: str, max_length: int, prefix: str = "") -> str:
    """Truncate HTML text safely without breaking tags.

    Args:
        text: HTML text to truncate.
        max_length: Maximum length including prefix.
        prefix: Text to prepend (e.g., "[...truncated...]").

    Returns:
        Truncated and balanced HTML.
    """
    if len(text) <= max_length:
        return text

    # Reserve space for prefix and tag overhead
    tag_buffer = 60  # Space for opening + closing tags
    available = max_length - len(prefix) - tag_buffer

    # Ensure we have at least some content
    if available < 50:
        available = max_length - len(prefix) - 20

    # Take from the end for streaming (show latest content)
    truncate_point = max(0, len(text) - available)
    truncated = text[truncate_point:]

    # Find a safe break point (not in middle of a tag)
    # Look for start of incomplete tag at beginning
    first_gt = truncated.find(">")
    first_lt = truncated.find("<")

    if first_lt != -1 and (first_gt == -1 or first_gt < first_lt):
        # We might be starting mid-tag, skip to after first complete tag
        if first_gt != -1:
            truncated = truncated[first_gt + 1:]

    # Find what tags were open at the truncation point
    # by analyzing the text before truncation
    if truncate_point > 0:
        prefix_text = text[:truncate_point]
        open_at_truncation = find_open_tags(prefix_text)

        # Add opening tags that were open before truncation
        if open_at_truncation:
            opening_tags = "".join(f"<{tag}>" for tag in open_at_truncation)
            truncated = opening_tags + truncated

    # Balance any unclosed tags in the truncated text
    balanced = balance_html(truncated)

    return f"{prefix}{balanced}" if prefix else balanced


class MessageStreamer:
    """Streams Claude responses to a Telegram message with throttling.

    Accumulates text and periodically updates the Telegram message,
    respecting rate limits and handling message size limits.

    Features:
    - HTML tag balancing to prevent parse errors
    - Graceful fallback to plain text on errors
    - Rate-limited updates
    """

    def __init__(
        self,
        message: Message,
        throttle_ms: int = 1000,
        chunk_size: int = 3800,
        parse_mode: str | None = "HTML",
    ):
        """Initialize streamer.

        Args:
            message: Telegram message to edit with updates.
            throttle_ms: Minimum milliseconds between message edits.
            chunk_size: Maximum characters to display (Telegram limit ~4096).
            parse_mode: Telegram parse mode (HTML or None).
        """
        self.message = message
        self.throttle_ms = throttle_ms
        self.chunk_size = chunk_size
        self.parse_mode = parse_mode
        self.current_text = ""
        self._last_edit_time: float = 0
        self._pending_flush: bool = False
        self._lock = asyncio.Lock()
        self._fallback_to_plain: bool = False  # If HTML fails repeatedly, stay plain

    async def append_text(self, text: str) -> None:
        """Append text and schedule flush if throttle allows.

        Args:
            text: Text to append to current content.
        """
        async with self._lock:
            self.current_text += text
            await self._maybe_flush()

    async def _maybe_flush(self) -> None:
        """Flush if enough time has passed since last edit."""
        now = time.time() * 1000  # ms
        elapsed = now - self._last_edit_time

        if elapsed >= self.throttle_ms:
            await self._do_flush()
        elif not self._pending_flush:
            self._pending_flush = True
            asyncio.create_task(self._delayed_flush())

    async def _delayed_flush(self) -> None:
        """Flush after throttle period expires."""
        await asyncio.sleep(self.throttle_ms / 1000)
        try:
            async with self._lock:
                if self._pending_flush:
                    await self._do_flush()
        except Exception:
            # Silently ignore flush errors - next flush will retry
            pass

    async def _do_flush(self) -> None:
        """Actually send the edit to Telegram."""
        if not self.current_text:
            return

        display_text = self._get_display_text()

        # Determine parse mode (may fallback to None)
        current_parse_mode = None if self._fallback_to_plain else self.parse_mode

        try:
            await self.message.edit_text(display_text, parse_mode=current_parse_mode)
            self._last_edit_time = time.time() * 1000
            self._pending_flush = False
        except BadRequest as e:
            error_msg = str(e).lower()
            # Message content unchanged - ignore
            if "not modified" in error_msg:
                self._pending_flush = False
                return
            # HTML parsing error - fallback to plain text
            if "parse entities" in error_msg or "can't parse" in error_msg:
                self._fallback_to_plain = True
                try:
                    # Strip HTML tags for plain text display
                    plain_text = re.sub(r"<[^>]+>", "", display_text)
                    await self.message.edit_text(plain_text, parse_mode=None)
                    self._last_edit_time = time.time() * 1000
                    self._pending_flush = False
                except Exception:
                    pass  # Give up, will retry on next flush
            else:
                raise
        except TimedOut:
            # Telegram timeout, will retry on next flush
            pass

    def _get_display_text(self) -> str:
        """Get text for display, truncated and balanced if needed."""
        text = self.current_text

        # If using HTML parse mode and not in fallback, balance tags
        if self.parse_mode == "HTML" and not self._fallback_to_plain:
            if len(text) <= self.chunk_size:
                return balance_html(text)
            else:
                return safe_truncate_html(
                    text,
                    self.chunk_size,
                    prefix="[...]\n"
                )
        else:
            # Plain text or other modes
            if len(text) <= self.chunk_size:
                return text
            # Simple truncation for non-HTML
            truncated = text[-(self.chunk_size - 10):]
            return f"[...]\n{truncated}"

    async def flush(self) -> None:
        """Force flush current content to Telegram."""
        async with self._lock:
            await self._do_flush()

    async def finish(self, final_text: Optional[str] = None) -> None:
        """Finalize streaming with optional final text.

        Args:
            final_text: Optional text to replace current content.
        """
        async with self._lock:
            if final_text is not None:
                self.current_text = final_text
            # On final flush, try HTML one more time even if we fell back
            self._fallback_to_plain = False
            await self._do_flush()

    async def set_text(self, text: str) -> None:
        """Replace current text entirely."""
        async with self._lock:
            self.current_text = text
