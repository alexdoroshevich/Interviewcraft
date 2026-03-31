"""Smart pause detection — VAD-based, no NLP required.

Spec (Component 1):
  - If Deepgram still sending partials (<700ms since last partial) → do NOT interrupt
  - Silence 5s with no new partials → soft prompt ("take your time...")
  - Silence > 10s → re-engage ("shall I ask the next question?")
  - NEVER cut off mid-thought. Better to wait too long than interrupt.
"""

import time
from enum import StrEnum


class PauseAction(StrEnum):
    NONE = "none"
    SOFT_PROMPT = "soft_prompt"  # 5s silence
    RE_ENGAGE = "re_engage"  # >10s silence


PARTIAL_TIMEOUT_MS = (
    2000  # Still speaking if partial within this window (generous for thinking pauses)
)
SOFT_PROMPT_MS = 12000  # 12s silence → "take your time"
RE_ENGAGE_MS = 20000  # 20s silence → gentle re-engage


class SmartPause:
    """Tracks partial transcript timing to implement smart pause behavior.

    Call on_partial() whenever Deepgram sends any partial transcript.
    Call on_final() when a final transcript arrives.
    Call check() periodically to determine what action to take.
    """

    def __init__(self) -> None:
        self._last_partial_ts: float = time.monotonic()
        self._last_final_ts: float = time.monotonic()
        self._silence_start: float = time.monotonic()
        self._soft_prompt_fired: bool = False
        self._re_engage_fired: bool = False
        self._active: bool = False  # Only active after first bot turn completes

    def activate(self) -> None:
        """Enable pause detection — call after bot finishes speaking."""
        self._active = True
        self._silence_start = time.monotonic()
        self._soft_prompt_fired = False
        self._re_engage_fired = False

    def deactivate(self) -> None:
        """Disable pause detection — call when bot starts speaking/processing."""
        self._active = False

    def on_partial(self) -> None:
        """Update the last-seen-partial timestamp."""
        self._last_partial_ts = time.monotonic()
        self._soft_prompt_fired = False
        self._re_engage_fired = False

    def on_final(self) -> None:
        """Reset state after a final transcript arrives."""
        self._last_final_ts = time.monotonic()
        self._silence_start = time.monotonic()
        self._soft_prompt_fired = False
        self._re_engage_fired = False

    def is_user_still_speaking(self) -> bool:
        """Return True if a Deepgram partial arrived within the last 700ms."""
        elapsed_ms = (time.monotonic() - self._last_partial_ts) * 1000
        return elapsed_ms < PARTIAL_TIMEOUT_MS

    def check(self) -> PauseAction:
        """Return the action to take based on current silence duration.

        Call this periodically (e.g., every 500ms) when in LISTENING state.
        """
        if not self._active:
            return PauseAction.NONE

        if self.is_user_still_speaking():
            return PauseAction.NONE

        silence_ms = (time.monotonic() - self._silence_start) * 1000

        if silence_ms >= RE_ENGAGE_MS and not self._re_engage_fired:
            self._re_engage_fired = True
            return PauseAction.RE_ENGAGE

        if silence_ms >= SOFT_PROMPT_MS and not self._soft_prompt_fired:
            self._soft_prompt_fired = True
            return PauseAction.SOFT_PROMPT

        return PauseAction.NONE
