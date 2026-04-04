"""Smart pause detection — VAD-based, no NLP required.

Spec (Component 1):
  - If Deepgram still sending partials within VOICE_PARTIAL_TIMEOUT_MS → do NOT interrupt
  - Silence >= VOICE_SOFT_PROMPT_MS → soft prompt ("take your time...")
  - Silence >= VOICE_RE_ENGAGE_MS → re-engage ("shall I ask the next question?")
  - NEVER cut off mid-thought. Better to wait too long than interrupt.
"""

import time
from enum import StrEnum

from app.services.voice import tuning


class PauseAction(StrEnum):
    NONE = "none"
    SOFT_PROMPT = "soft_prompt"
    RE_ENGAGE = "re_engage"


PARTIAL_TIMEOUT_MS = tuning.PARTIAL_TIMEOUT_MS
SOFT_PROMPT_MS = tuning.SOFT_PROMPT_MS
RE_ENGAGE_MS = tuning.RE_ENGAGE_MS


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
