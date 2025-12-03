"""Test streaming to Telegram."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.claude.streaming import MessageStreamer, find_safe_truncate_point, safe_truncate_html


@pytest.fixture
def mock_message():
    """Create mock Telegram message."""
    msg = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.message_id = 123
    return msg


@pytest.fixture
def streamer(mock_message):
    """Create MessageStreamer instance."""
    return MessageStreamer(
        message=mock_message,
        throttle_ms=100,
        chunk_size=100,
    )


@pytest.mark.asyncio
async def test_streamer_init(streamer, mock_message):
    """Streamer initializes with message."""
    assert streamer.message == mock_message
    assert streamer.current_text == ""


@pytest.mark.asyncio
async def test_streamer_append_text(streamer):
    """append_text accumulates text."""
    await streamer.append_text("Hello ")
    await streamer.append_text("World")

    assert streamer.current_text == "Hello World"


@pytest.mark.asyncio
async def test_streamer_flush_updates_message(streamer, mock_message):
    """flush sends edit to Telegram."""
    streamer.current_text = "Test content"
    await streamer.flush()

    mock_message.edit_text.assert_called()


@pytest.mark.asyncio
async def test_streamer_truncates_long_text(streamer):
    """Long text is truncated with indicator."""
    streamer.chunk_size = 50
    streamer.current_text = "x" * 100

    display = streamer._get_display_text()

    assert len(display) <= 60  # chunk_size + some buffer for truncation marker
    assert "..." in display or "[truncated]" in display


@pytest.mark.asyncio
async def test_streamer_throttles_edits(streamer, mock_message):
    """Multiple rapid appends don't spam edits."""
    streamer.throttle_ms = 500

    for i in range(10):
        await streamer.append_text(f"chunk{i} ")
        await asyncio.sleep(0.01)

    # Should have fewer edits than appends due to throttling
    assert mock_message.edit_text.call_count < 10


@pytest.mark.asyncio
async def test_streamer_delayed_flush(streamer, mock_message):
    """Pending content is eventually flushed after throttle expires."""
    streamer.throttle_ms = 100  # 100ms throttle

    # First append triggers immediate flush (no throttle yet)
    await streamer.append_text("First")
    await asyncio.sleep(0.01)  # Brief wait for async processing
    initial_call_count = mock_message.edit_text.call_count

    # Second append should schedule delayed flush (within throttle period)
    await streamer.append_text(" Second")
    await asyncio.sleep(0.01)  # Brief wait

    # Should not have flushed yet (throttled)
    assert mock_message.edit_text.call_count == initial_call_count

    # Wait for throttle period to expire + buffer
    await asyncio.sleep(0.15)  # 150ms total

    # Delayed flush should have executed
    assert mock_message.edit_text.call_count > initial_call_count
    assert streamer.current_text == "First Second"


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
        # Should have truncation indicator
        assert "[...]" in display
        # Should preserve emoji formatting in visible content
        assert "✅" in display
        # <b> tags should be balanced (from header)
        assert display.count("<b>") == display.count("</b>")


class TestFindSafeTruncatePoint:
    """Tests for find_safe_truncate_point function."""

    def test_safe_point_not_inside_entity(self):
        """Target inside &amp; should move before &."""
        text = "Hello &amp; world"
        # Position 8 is inside &amp; (& is at 6, ; is at 10)
        result = find_safe_truncate_point(text, 8)
        assert result <= 6

    def test_safe_point_not_inside_tag(self):
        """Target inside <b> should move before <."""
        text = "Hello <b>world</b>"
        # Position 7 is inside <b> (< is at 6, > is at 8)
        result = find_safe_truncate_point(text, 7)
        assert result <= 6

    def test_safe_point_prefers_newline(self):
        """Should snap to after newline when available."""
        text = "Line one\nLine two"
        # Newline is at position 8, so safe point should be 9 (after newline)
        result = find_safe_truncate_point(text, 12)
        assert result == 9

    def test_safe_point_prefers_space(self):
        """Should snap to after space when no newline."""
        text = "Hello beautiful world"
        # Space after "Hello" is at 5, after "beautiful" is at 15
        result = find_safe_truncate_point(text, 10)
        assert result == 6  # After "Hello "

    def test_safe_point_outside_entity_unchanged(self):
        """Position outside entity stays near target."""
        text = "Hello &amp; world test"
        # Position 18 is well past the entity
        result = find_safe_truncate_point(text, 18)
        # Should find a space boundary nearby
        assert result <= 18

    def test_safe_point_handles_multiple_entities(self):
        """Handles text with multiple entities."""
        text = "A &lt; B &gt; C &amp; D"
        # Position 5 is inside &lt;
        result = find_safe_truncate_point(text, 5)
        assert result <= 2  # Before the &


class TestSafeTruncateHtml:
    """Tests for safe_truncate_html function."""

    def test_short_text_unchanged(self):
        """Text under max_length returned as-is."""
        text = "<b>Hello</b> world"
        result = safe_truncate_html(text, 100)
        assert result == text

    def test_truncate_preserves_formatting(self):
        """Long text preserves HTML formatting after truncation."""
        text = "<b>Bold</b> " * 500  # ~6000 chars
        result = safe_truncate_html(text, 3800)
        assert "<b>" in result
        assert result.count("<b>") == result.count("</b>")

    def test_truncate_doesnt_break_entities(self):
        """Truncation doesn't break HTML entities."""
        text = "A &amp; B " * 500
        result = safe_truncate_html(text, 3800)
        # Should not have broken entity like "&am" or "amp;"
        assert "&am" not in result or "&amp;" in result
        # Check we don't have orphaned semicolons from broken entities
        import re
        broken = re.findall(r'&[a-z]{1,3}[^;a-z]', result)
        assert len(broken) == 0, f"Found broken entities: {broken}"

    def test_truncate_adds_prefix(self):
        """Truncation adds prefix indicator."""
        text = "x" * 5000
        result = safe_truncate_html(text, 3800, prefix="[...]\n")
        assert result.startswith("[...]\n")

    def test_truncate_balances_nested_tags(self):
        """Nested tags are properly balanced."""
        text = "<b><i><code>" + "x" * 5000 + "</code></i></b>"
        result = safe_truncate_html(text, 3800)
        # Should have balanced tags
        assert result.count("<b>") == result.count("</b>")
        assert result.count("<i>") == result.count("</i>")
        assert result.count("<code>") == result.count("</code>")
