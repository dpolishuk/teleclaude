"""Test streaming to Telegram."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.claude.streaming import MessageStreamer


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
