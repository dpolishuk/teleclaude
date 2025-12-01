"""Streaming responses to Telegram with throttling."""
import asyncio
import html
import time
from typing import Optional

from telegram import Message
from telegram.error import BadRequest, TimedOut


def escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return html.escape(text)


class MessageStreamer:
    """Streams Claude responses to a Telegram message with throttling.

    Accumulates text and periodically updates the Telegram message,
    respecting rate limits and handling message size limits.
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
            parse_mode: Telegram parse mode (HTML, MarkdownV2, or None).
        """
        self.message = message
        self.throttle_ms = throttle_ms
        self.chunk_size = chunk_size
        self.parse_mode = parse_mode
        self.current_text = ""
        self._last_edit_time: float = 0
        self._pending_flush: bool = False
        self._lock = asyncio.Lock()

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
        async with self._lock:
            if self._pending_flush:
                await self._do_flush()

    async def _do_flush(self) -> None:
        """Actually send the edit to Telegram."""
        if not self.current_text:
            return

        display_text = self._get_display_text()

        try:
            await self.message.edit_text(display_text, parse_mode=self.parse_mode)
            self._last_edit_time = time.time() * 1000
            self._pending_flush = False
        except BadRequest as e:
            # Message content unchanged or other Telegram error
            if "not modified" not in str(e).lower():
                raise
        except TimedOut:
            # Telegram timeout, will retry on next flush
            pass

    def _get_display_text(self) -> str:
        """Get text for display, truncated if needed."""
        if len(self.current_text) <= self.chunk_size:
            return self.current_text

        # Truncate with indicator
        truncated = self.current_text[-(self.chunk_size - 20):]
        return f"[...truncated...]\n{truncated}"

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
            await self._do_flush()

    async def set_text(self, text: str) -> None:
        """Replace current text entirely."""
        async with self._lock:
            self.current_text = text
