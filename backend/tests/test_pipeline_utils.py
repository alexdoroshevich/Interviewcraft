"""Unit tests for pure pipeline helper functions.

Tests _strip_markdown and SentenceBuffer — the only parts of pipeline.py
that don't require a live WebSocket connection.
"""

from __future__ import annotations

from app.services.voice.pipeline import SentenceBuffer, _strip_markdown

# ── _strip_markdown ────────────────────────────────────────────────────────────


def test_strip_markdown_bold() -> None:
    assert _strip_markdown("This is **bold** text") == "This is bold text"


def test_strip_markdown_italic() -> None:
    assert _strip_markdown("This is *italic* text") == "This is italic text"


def test_strip_markdown_code_inline() -> None:
    assert _strip_markdown("Use `redis.get()` here") == "Use redis.get() here"


def test_strip_markdown_code_block() -> None:
    assert _strip_markdown("Use ```code block``` here") == "Use code block here"


def test_strip_markdown_bullet_list() -> None:
    result = _strip_markdown("- first item")
    assert result == "first item"


def test_strip_markdown_numbered_list() -> None:
    result = _strip_markdown("1. first item")
    assert result == "first item"


def test_strip_markdown_plain_text_unchanged() -> None:
    text = "Just a normal sentence with no markdown."
    assert _strip_markdown(text) == text


def test_strip_markdown_empty_string() -> None:
    assert _strip_markdown("") == ""


# ── SentenceBuffer ────────────────────────────────────────────────────────────


def test_sentence_buffer_flushes_complete_sentence() -> None:
    """A sentence ending with '. ' (space after period) is returned by add()."""
    buf = SentenceBuffer()
    # Boundary regex requires whitespace after punctuation
    result = buf.add("Hello world. ")
    assert len(result) == 1
    assert "Hello world." in result[0]


def test_sentence_buffer_accumulates_incomplete_tokens() -> None:
    """Tokens without sentence boundary are held in buffer."""
    buf = SentenceBuffer()
    result = buf.add("Hello ")
    assert result == []
    result2 = buf.add("world")
    assert result2 == []


def test_sentence_buffer_multiple_sentences() -> None:
    """Two sentences with space-separated boundary return both."""
    buf = SentenceBuffer()
    sentences = buf.add("First sentence. Second sentence. ")
    assert len(sentences) == 2


def test_sentence_buffer_question_mark_boundary() -> None:
    """Question mark followed by space triggers sentence flush."""
    buf = SentenceBuffer()
    result = buf.add("Is this working? ")
    assert len(result) == 1
    assert "?" in result[0]


def test_sentence_buffer_exclamation_mark_boundary() -> None:
    """Exclamation mark followed by space triggers sentence flush."""
    buf = SentenceBuffer()
    result = buf.add("Great answer! ")
    assert len(result) == 1


def test_sentence_buffer_flush_returns_remaining() -> None:
    """flush() returns remaining text even without sentence boundary."""
    buf = SentenceBuffer()
    buf.add("Incomplete sentence")
    remaining = buf.flush()
    assert remaining == "Incomplete sentence"


def test_sentence_buffer_flush_empty_buffer_returns_none() -> None:
    """flush() on empty buffer returns None."""
    buf = SentenceBuffer()
    assert buf.flush() is None


def test_sentence_buffer_flush_clears_buffer() -> None:
    """After flush(), buffer is empty."""
    buf = SentenceBuffer()
    buf.add("Some text")
    buf.flush()
    assert buf.flush() is None
