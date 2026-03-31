"""Tests for SmartPause VAD-based pause detection."""

from __future__ import annotations

import time

from app.services.voice.smart_pause import PauseAction, SmartPause


def test_check_returns_none_when_inactive() -> None:
    """check() before activate() always returns NONE."""
    sp = SmartPause()
    assert sp.check() == PauseAction.NONE


def test_activate_enables_detection() -> None:
    """activate() sets _active = True."""
    sp = SmartPause()
    sp.activate()
    assert sp._active is True


def test_deactivate_stops_detection() -> None:
    """deactivate() makes check() return NONE again."""
    sp = SmartPause()
    sp.activate()
    sp.deactivate()
    assert sp.check() == PauseAction.NONE


def test_check_none_when_user_still_speaking() -> None:
    """check() returns NONE when a partial arrived recently (within 2s)."""
    sp = SmartPause()
    sp.activate()
    sp.on_partial()  # resets _last_partial_ts to now
    assert sp.check() == PauseAction.NONE


def test_check_soft_prompt_after_long_silence() -> None:
    """After SOFT_PROMPT_MS silence, check() returns SOFT_PROMPT."""
    sp = SmartPause()
    sp.activate()
    # Simulate silence longer than SOFT_PROMPT_MS by backdating timestamps
    sp._silence_start = time.monotonic() - 15  # 15s silence (> 12s threshold)
    sp._last_partial_ts = time.monotonic() - 10  # no recent partial (> 2s timeout)
    assert sp.check() == PauseAction.SOFT_PROMPT


def test_check_re_engage_after_very_long_silence() -> None:
    """After RE_ENGAGE_MS silence, check() returns RE_ENGAGE."""
    sp = SmartPause()
    sp.activate()
    sp._silence_start = time.monotonic() - 25  # 25s silence (> 20s threshold)
    sp._last_partial_ts = time.monotonic() - 10  # no recent partial
    assert sp.check() == PauseAction.RE_ENGAGE


def test_soft_prompt_only_fires_once() -> None:
    """SOFT_PROMPT is not returned twice in the same pause window."""
    sp = SmartPause()
    sp.activate()
    sp._silence_start = time.monotonic() - 15
    sp._last_partial_ts = time.monotonic() - 10
    assert sp.check() == PauseAction.SOFT_PROMPT
    assert sp.check() == PauseAction.NONE  # already fired


def test_on_final_resets_state() -> None:
    """on_final() resets silence_start and fired flags."""
    sp = SmartPause()
    sp.activate()
    sp._soft_prompt_fired = True
    sp.on_final()
    assert sp._soft_prompt_fired is False
