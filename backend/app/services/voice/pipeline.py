"""VoicePipeline — orchestrates STT → LLM → TTS for one interview session.

Flow (per voice turn):
  Browser mic → WebSocket → Deepgram STT (partials + finals)
  → Claude LLM (streaming) → ElevenLabs TTS (streaming)
  → WebSocket → Browser speaker

Key optimisation: stream first complete sentence to TTS while LLM still generates.
This is what drives p50 < 800ms E2E latency.

Smart pause (VAD-based, no NLP):
  recent partials              → still speaking, do NOT commit
  VOICE_COMMIT_SHORT_S silence → commit short answer
  VOICE_COMMIT_LONG_S silence  → commit long answer
  VOICE_SOFT_PROMPT_MS         → soft prompt toast
  VOICE_RE_ENGAGE_MS           → re-engage toast

Audio is NEVER stored to disk. Lives only in asyncio.Queue memory.
"""

from __future__ import annotations

import asyncio
import base64
import re
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview_session import InterviewSession
from app.models.session_metrics import SessionMetrics
from app.models.transcript_word import TranscriptWord
from app.services.usage import log_usage
from app.services.voice import tuning
from app.services.voice.costs import (
    calc_anthropic_cost,
    calc_deepgram_stt_cost,
    calc_deepgram_tts_cost,
    calc_elevenlabs_cost,
)
from app.services.voice.interfaces import ProviderSet
from app.services.voice.prompts import RE_ENGAGE_TEXT, SOFT_PROMPT_TEXT, get_system_prompt
from app.services.voice.providers.deepgram_tts import DeepgramTTSProvider
from app.services.voice.smart_pause import PauseAction, SmartPause
from app.services.voice.types import LatencySnapshot, PipelineState, TranscriptChunk

logger = structlog.get_logger(__name__)

_WORD_TTL_DAYS = 14
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])\s+")

# Markdown patterns to strip before TTS (defense in depth — prompts also say "no markdown")
_MD_PATTERNS = [
    (re.compile(r"#{1,6}\s*"), ""),  # # headings
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),  # **bold**
    (re.compile(r"\*(.+?)\*"), r"\1"),  # *italic*
    (re.compile(r"`{1,3}(.+?)`{1,3}"), r"\1"),  # `code` or ```code```
    (re.compile(r"^[-*]\s+", re.MULTILINE), ""),  # - bullet points
    (re.compile(r"^\d+\.\s+", re.MULTILINE), ""),  # 1. numbered lists
]


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting so TTS doesn't speak special characters."""
    for pattern, repl in _MD_PATTERNS:
        text = pattern.sub(repl, text)
    return text.strip()


class SentenceBuffer:
    """Accumulate LLM tokens and flush on sentence boundaries."""

    def __init__(self) -> None:
        self._buf = ""

    def add(self, token: str) -> list[str]:
        """Add a token; return any complete sentences ready for TTS."""
        self._buf += token
        sentences: list[str] = []
        while True:
            m = _SENTENCE_BOUNDARY.search(self._buf)
            if not m:
                break
            sentence = self._buf[: m.start() + 1].strip()
            self._buf = self._buf[m.end() :]
            if sentence:
                sentences.append(sentence)
        return sentences

    def flush(self) -> str | None:
        text = self._buf.strip()
        self._buf = ""
        return text or None


class VoicePipeline:  # pragma: no cover
    """Stateful pipeline for one interview session's voice loop."""

    def __init__(
        self,
        providers: ProviderSet,
        db: AsyncSession,
        session: InterviewSession,
        user_id: uuid.UUID,
        company_questions: list[str] | None = None,
        candidate_context: str | None = None,
        duration_limit_minutes: int | None = None,
    ) -> None:
        self._providers = providers
        self._db = db
        self._session = session
        self._user_id = user_id
        self._state = PipelineState.IDLE
        self._smart_pause = SmartPause()
        self._conversation: list[dict[str, str]] = []
        base_prompt = get_system_prompt(
            session.type,
            persona=getattr(session, "persona", "neutral"),
            company=getattr(session, "company", None),
            focus_skill=getattr(session, "focus_skill", None),
            candidate_context=candidate_context,
        )
        if company_questions:
            numbered = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(company_questions))
            company = getattr(session, "company", "this company")
            base_prompt += (
                f"\nCOMPANY QUESTION BANK — {company.upper()}:\n"
                f"The following are real interview questions used at {company.title()}. "
                f"Draw from these questions during this session. You may rephrase slightly but preserve the core intent:\n"
                f"{numbered}\n"
            )
        self._system_prompt = base_prompt
        self._total_cost = Decimal("0")
        self._session_start = time.monotonic()
        self._low_confidence_count = 0  # Consecutive low-confidence STT finals
        self._llm_lock = asyncio.Lock()  # Prevent concurrent LLM+TTS turns
        self._interrupted = asyncio.Event()  # Barge-in: user interrupted bot
        self._llm_task: asyncio.Task[None] | None = None  # Cancelable LLM+TTS task
        self._tts_fallback_active = False  # True if primary TTS failed, using Deepgram
        self._tts_fallback_reason = ""  # "auth" if ElevenLabs 401, else "error"
        self._carryover_text = ""  # Cross-loop: text from [WAIT] turn, prepended to next input
        self._wait_count = 0  # Consecutive [WAIT] signals — capped at 2, then force-respond
        self._carryover_set_at: float | None = None  # Monotonic time when carryover was last set
        self._tool_context: str | None = None  # Current board/code state sent by frontend
        self._duration_limit_minutes = duration_limit_minutes

    # ── Public entry point ─────────────────────────────────────────────────────

    async def run(self, websocket: WebSocket) -> None:
        """Main loop — receive audio from client, send audio back.

        WebSocket message protocol:
          Client→Server: {"type":"audio",        "data":"<base64 PCM>"}
          Client→Server: {"type":"end_audio"}
          Client→Server: {"type":"interrupt"}
          Client→Server: {"type":"text_input",   "text":"..."}
          Client→Server: {"type":"tool_context", "context":"..."}
          Server→Client: {"type":"transcript_partial", "text":"...", "x_latency":{...}}
          Server→Client: {"type":"transcript_final",   "text":"...", "x_latency":{...}}
          Server→Client: {"type":"llm_chunk",           "text":"...", "x_latency":{...}}
          Server→Client: {"type":"audio_chunk",         "data":"<base64>", "x_latency":{...}}
          Server→Client: {"type":"session_state",       "state":"listening|processing|speaking"}
          Server→Client: {"type":"soft_prompt",         "text":"..."}
          Server→Client: {"type":"error",               "message":"..."}
        """
        audio_in: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=200)
        text_in: asyncio.Queue[str | None] = asyncio.Queue()
        await self._set_state(websocket, PipelineState.LISTENING)

        # Kick off the interviewer with an opening question
        await self._send_opening(websocket)
        # Warn if ElevenLabs key was rejected — user needs to set up BYOK
        if self._tts_fallback_active and self._tts_fallback_reason == "auth":
            await websocket.send_json(
                {
                    "type": "soft_prompt",
                    "text": "⚠️ ElevenLabs API key invalid — using backup voice. Go to Settings → API Keys to add your own key.",
                }
            )

        receive_task = asyncio.create_task(self._receive_loop(websocket, audio_in, text_in))
        process_task = asyncio.create_task(self._process_loop(websocket, audio_in))
        text_task = asyncio.create_task(self._text_process_loop(websocket, text_in))
        pause_task = asyncio.create_task(self._pause_monitor(websocket, audio_in))

        # Optional: fire-and-forget session timer — sends warning at T-2min, ends at T-0
        _duration_task: asyncio.Task[None] | None = None
        if self._duration_limit_minutes:
            _duration_task = asyncio.create_task(self._duration_guard(websocket))

        try:
            done, pending = await asyncio.wait(
                [receive_task, process_task, text_task, pause_task],
                return_when=asyncio.FIRST_EXCEPTION,
            )
            for t in pending:
                t.cancel()
            for t in done:
                if exc := t.exception():
                    logger.error("pipeline.error", error=str(exc))
                    await self._send_error(websocket, str(exc))
        finally:
            if _duration_task and not _duration_task.done():
                _duration_task.cancel()

        await self._finalize_session()

    # ── Duration guard ─────────────────────────────────────────────────────────

    async def _duration_guard(self, websocket: WebSocket) -> None:
        """Enforce the session time limit.

        At T-2 minutes: send a soft-prompt toast warning.
        At T-0: send session_state=time_limit_reached so the frontend ends gracefully.
        """
        if self._duration_limit_minutes is None:
            return
        total_seconds = self._duration_limit_minutes * 60
        warning_delay = total_seconds - 120
        if warning_delay > 0:
            await asyncio.sleep(warning_delay)
            try:
                await websocket.send_json(
                    {
                        "type": "soft_prompt",
                        "text": "⏱ 2 minutes remaining — please start wrapping up your answer.",
                    }
                )
                logger.info(
                    "pipeline.duration_warning",
                    session_id=str(self._session.id),
                    remaining_s=120,
                )
            except Exception:
                return  # WebSocket already closed — session already ended
            await asyncio.sleep(120)
        else:
            await asyncio.sleep(max(total_seconds, 0))
        try:
            await websocket.send_json({"type": "session_state", "state": "time_limit_reached"})
            logger.info(
                "pipeline.duration_limit_reached",
                session_id=str(self._session.id),
                duration_minutes=self._duration_limit_minutes,
            )
        except Exception:
            pass  # WebSocket already closed — normal if user ended first

    # ── Internal loops ─────────────────────────────────────────────────────────

    async def _receive_loop(
        self,
        websocket: WebSocket,
        audio_in: asyncio.Queue[bytes | None],
        text_in: asyncio.Queue[str | None],
    ) -> None:
        """Receive audio or text from browser and route to the correct queue.

        Message types:
          audio       → audio_in (STT path)
          end_audio   → signals end of audio stream
          interrupt   → abort current turn
          text_input  → text_in (low-confidence STT fallback path)
        """
        try:
            while True:
                msg = await websocket.receive_json()
                msg_type = msg.get("type")

                if msg_type == "audio":
                    raw = base64.b64decode(msg["data"])
                    await audio_in.put(raw)
                elif msg_type == "end_audio":
                    await audio_in.put(None)
                    await text_in.put(None)
                    break
                elif msg_type == "interrupt":
                    logger.info("pipeline.user_interrupt")
                    self._interrupted.set()  # Signal TTS worker to stop
                elif msg_type == "text_input":
                    # User typed instead of speaking (STT confidence fallback)
                    typed = msg.get("text", "").strip()
                    if typed:
                        logger.info("pipeline.text_input_received")
                        await text_in.put(typed)
                elif msg_type == "tool_context":
                    # Frontend sends board/code state whenever it changes.
                    # Store it; injected into next LLM call as visual context.
                    raw = msg.get("context", "").strip()
                    self._tool_context = raw if raw else None
                    logger.debug(
                        "pipeline.tool_context_updated",
                        has_context=bool(self._tool_context),
                        length=len(raw),
                    )
        except Exception as exc:
            logger.error("pipeline.receive_loop_error", error=str(exc))
            await audio_in.put(None)
            await text_in.put(None)

    async def _process_loop(
        self,
        websocket: WebSocket,
        audio_in: asyncio.Queue[bytes | None],
    ) -> None:
        """STT → LLM → TTS chain with short debounce + barge-in recovery.

        Inspired by ChatGPT voice: use a short pause (~1s) to trigger LLM,
        but if the user keeps speaking after the bot starts, the bot stops
        immediately, accumulates the new speech, and re-triggers with the
        full combined message.  This gives fast response times while still
        not cutting the user off.
        """
        # Debounce: wait for natural speech pause before triggering LLM.
        # 2s tolerates natural pauses (breathing, thinking) without splitting the answer.
        min_words_for_llm = tuning.PIPELINE_MIN_WORDS_FOR_LLM

        e2e_start = time.monotonic()
        stt_start = time.monotonic()

        # Cumulative text for the current turn — updated in _stt_reader as finals arrive,
        # reset in _turn_consumer when the turn is committed. This lets the frontend
        # always receive the FULL accumulated text rather than individual sentences,
        # eliminating any frontend-side accumulation state that could de-sync.
        current_turn_text: str = ""

        final_queue: asyncio.Queue[TranscriptChunk | None] = asyncio.Queue()

        async def _audio_gen() -> AsyncGenerator[bytes]:
            while True:
                chunk = await audio_in.get()
                if chunk is None:
                    return
                yield chunk

        async def _stt_reader() -> None:
            """Read STT stream, update SmartPause timing, push finals to queue.

            Partial (non-final) chunks are forwarded to the frontend immediately
            so the user sees their words appearing in real-time while speaking.
            Finals are accumulated into current_turn_text and sent to the debounce queue.
            """
            nonlocal stt_start, current_turn_text
            async for chunk in self._providers.stt.transcribe_stream(_audio_gen()):
                if not chunk.is_final:
                    self._smart_pause.on_partial()
                    # Stream live partial text to frontend (cumulative: confirmed finals + current partial)
                    if chunk.text.strip():
                        display_text = (
                            (current_turn_text + " " + chunk.text).strip()
                            if current_turn_text
                            else chunk.text
                        )
                        await websocket.send_json(
                            {
                                "type": "transcript_partial",
                                "text": display_text,
                            }
                        )
                else:
                    self._smart_pause.on_final()
                    if chunk.text.strip():
                        current_turn_text = (
                            (current_turn_text + " " + chunk.text).strip()
                            if current_turn_text
                            else chunk.text
                        )
                        # Update frontend with confirmed cumulative text
                        await websocket.send_json(
                            {
                                "type": "transcript_partial",
                                "text": current_turn_text,
                            }
                        )
                    await final_queue.put(chunk)

                    # Barge-in: if bot is speaking/processing and user sends a final,
                    # cancel the current LLM+TTS turn immediately
                    if self._llm_task and not self._llm_task.done():
                        logger.info("pipeline.barge_in_cancel", state=self._state.value)
                        self._interrupted.set()
                        self._llm_task.cancel()
                        try:
                            await self._llm_task
                        except (asyncio.CancelledError, Exception):
                            pass
                        self._llm_task = None
                        self._interrupted.clear()

            await final_queue.put(None)

        async def _turn_consumer() -> None:
            """Consume finals with short debounce + barge-in recovery."""
            nonlocal e2e_start, stt_start, current_turn_text

            while True:
                first_final = await final_queue.get()
                if first_final is None:
                    break

                lat = LatencySnapshot()
                lat.stt_latency_ms = int((time.monotonic() - stt_start) * 1000)

                await self._save_transcript_words(first_final)
                if first_final.confidence < DeepgramSTTProvider_THRESHOLD:
                    self._low_confidence_count += 1
                    if self._low_confidence_count >= 3:
                        await websocket.send_json(
                            {
                                "type": "low_confidence_fallback",
                                "message": "Having trouble hearing you — you can type your answer instead.",
                            }
                        )
                    else:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "I didn't catch that clearly — could you repeat?",
                            }
                        )
                    continue
                self._low_confidence_count = 0

                pending_finals: list[TranscriptChunk] = [first_final]
                accumulated_text = first_final.text

                # Adaptive debounce: commit only when the user has been completely
                # silent (no Deepgram partials AND no new finals) long enough.
                #
                # KEY: last_activity resets on every new sound OR new Deepgram final.
                # The hard cap is measured from last_activity, NOT from the first
                # final — so a 60-second answer never triggers the hard cap early.
                #
                # Effective silence before commit (measured after Deepgram endpointing):
                #   Short answers: VOICE_COMMIT_SHORT_S extra silence
                #   Long answers:  VOICE_COMMIT_LONG_S extra silence
                # Hard cap: VOICE_HARD_CAP_S of complete inactivity (STT stall guard only).
                poll_interval_s = tuning.PIPELINE_POLL_INTERVAL_S
                hard_cap_s = tuning.PIPELINE_HARD_CAP_S
                quiet_since: float | None = None
                last_activity = time.monotonic()

                while True:
                    # Hard cap measured from last activity — never fires during speech
                    if time.monotonic() - last_activity > hard_cap_s:
                        break

                    try:
                        next_chunk = await asyncio.wait_for(
                            final_queue.get(), timeout=poll_interval_s
                        )
                    except TimeoutError:
                        if self._smart_pause.is_user_still_speaking():
                            # User is making sounds — reset silence and activity timers
                            quiet_since = None
                            last_activity = time.monotonic()
                        else:
                            # Scale extra wait by answer length so short replies are fast
                            # and long thoughtful answers get more buffer.
                            # Tuned for p95 < 1.5s: short=0.3s silence, long=1.2s silence.
                            commit_extra_s = (
                                tuning.PIPELINE_COMMIT_SHORT_S
                                if len(accumulated_text.split())
                                < tuning.PIPELINE_COMMIT_THRESHOLD_WORDS
                                else tuning.PIPELINE_COMMIT_LONG_S
                            )
                            if quiet_since is None:
                                quiet_since = time.monotonic()
                            elif time.monotonic() - quiet_since >= commit_extra_s:
                                break  # Truly silent long enough — commit
                        continue

                    if next_chunk is None:
                        break

                    # New Deepgram final arrived — user sent more speech; reset all timers
                    quiet_since = None
                    last_activity = time.monotonic()
                    await self._save_transcript_words(next_chunk)
                    if next_chunk.confidence >= DeepgramSTTProvider_THRESHOLD:
                        pending_finals.append(next_chunk)
                        accumulated_text = (accumulated_text + " " + next_chunk.text).strip()

                # Prepend any carryover from a previously interrupted or [WAIT] turn
                if self._carryover_text:
                    accumulated_text = (self._carryover_text + " " + accumulated_text).strip()
                    self._carryover_text = ""
                    self._carryover_set_at = None

                word_count = len(accumulated_text.split())
                if not accumulated_text.strip() or word_count < min_words_for_llm:
                    if accumulated_text.strip():
                        logger.debug(
                            "pipeline.skipped_short_fragment",
                            text_len=len(accumulated_text),
                            words=word_count,
                        )
                        self._carryover_text = accumulated_text
                    continue

                logger.info("pipeline.turn_committed", text_len=len(accumulated_text))

                # Reset E2E clock here — user has finished speaking.
                # This gives us the true AI processing latency (debounce tail +
                # STT final + LLM + TTS), not the user's speaking duration.
                e2e_start = time.monotonic()

                await websocket.send_json(
                    {
                        "type": "transcript_final",
                        "text": accumulated_text,
                        "x_latency": {"stt_ms": lat.stt_latency_ms},
                    }
                )

                # Wrap candidate speech in structural delimiters to prevent prompt injection.
                # A user could speak phrases that look like system instructions; the XML
                # boundary signals to the LLM that this is candidate content, not directives.
                self._conversation.append(
                    {
                        "role": "user",
                        "content": f"<candidate_answer>{accumulated_text}</candidate_answer>",
                    }
                )

                # Launch LLM+TTS as a cancelable task — if user barges in,
                # _stt_reader will cancel this task and we'll re-trigger
                async def _do_llm_turn(
                    lat_snap: LatencySnapshot, finals: list[TranscriptChunk], text: str
                ) -> bool:
                    """Fire LLM+TTS. Returns True if a real response was generated, False if [WAIT]."""
                    nonlocal current_turn_text
                    current_turn_text = ""
                    async with self._llm_lock:
                        await self._set_state(websocket, PipelineState.PROCESSING)
                        llm_ttft, tts_first_byte = await self._llm_tts_turn(websocket, lat_snap)

                    # [WAIT] signal — LLM decided the answer is incomplete
                    if llm_ttft == 0 and tts_first_byte == 0:
                        self._wait_count += 1
                        logger.info(
                            "pipeline.wait_signal_carryover",
                            text_len=len(text),
                            wait_count=self._wait_count,
                        )
                        self._carryover_text = text
                        self._carryover_set_at = time.monotonic()
                        # Remove transcript_final from frontend — answer is still in progress
                        await websocket.send_json({"type": "transcript_rollback"})
                        await self._set_state(websocket, PipelineState.LISTENING)
                        return False
                    self._wait_count = 0

                    lat_snap.llm_ttft_ms = llm_ttft
                    lat_snap.tts_latency_ms = tts_first_byte
                    lat_snap.e2e_latency_ms = int((time.monotonic() - e2e_start) * 1000)
                    await self._log_latency(lat_snap)
                    for fc in finals:
                        await self._log_stt_cost(fc)
                    await self._save_transcript_turn()
                    await self._set_state(websocket, PipelineState.LISTENING)
                    return True

                self._llm_task = asyncio.create_task(
                    _do_llm_turn(lat, pending_finals, accumulated_text)  # type: ignore[arg-type]
                )
                try:
                    await self._llm_task
                except asyncio.CancelledError:
                    # Barge-in happened — bot was interrupted by user continuing to speak.
                    # Roll back any uncommitted DB changes to prevent cascading failures
                    try:
                        await self._db.rollback()
                    except Exception:
                        pass
                    # Remove the partial assistant response from conversation
                    # (it was appended in _llm_tts_turn) and keep user text as carryover
                    if self._conversation and self._conversation[-1]["role"] == "assistant":
                        self._conversation.pop()
                    # The user's text stays in conversation; new speech will extend it
                    self._carryover_text = accumulated_text
                    logger.info(
                        "pipeline.barge_in_recovered", carryover_len=len(self._carryover_text)
                    )
                    await self._set_state(websocket, PipelineState.LISTENING)
                finally:
                    self._llm_task = None

                e2e_start = time.monotonic()
                stt_start = time.monotonic()

        reader_task = asyncio.create_task(_stt_reader())
        consumer_task = asyncio.create_task(_turn_consumer())

        done, pending = await asyncio.wait(
            [reader_task, consumer_task],
            return_when=asyncio.FIRST_EXCEPTION,
        )
        for t in pending:
            t.cancel()
        for t in done:
            if exc := t.exception():
                raise exc

    async def _pause_monitor(
        self,
        websocket: WebSocket,
        audio_in: asyncio.Queue[bytes | None],
    ) -> None:
        """Poll smart pause state every 500ms and send prompts.

        Also recovers from [WAIT] deadlock: if carryover text has been pending
        for > 8s with no new speech, force the LLM to respond anyway.
        """
        carryover_timeout_s = tuning.PIPELINE_CARRYOVER_TIMEOUT_S

        while True:
            await asyncio.sleep(0.5)
            if self._state != PipelineState.LISTENING:
                continue

            # [WAIT] deadlock recovery: user hasn't spoken again but carryover is waiting.
            # Force the LLM to respond so the session doesn't freeze.
            if (
                self._carryover_text
                and self._carryover_set_at is not None
                and time.monotonic() - self._carryover_set_at > carryover_timeout_s
            ):
                text = self._carryover_text
                self._carryover_text = ""
                self._carryover_set_at = None
                self._wait_count = 0
                logger.info("pipeline.carryover_force_respond", text_len=len(text))
                # Re-show the user's message in the frontend (it was rolled back)
                await websocket.send_json(
                    {
                        "type": "transcript_final",
                        "text": text,
                        "x_latency": {},
                    }
                )
                self._conversation.append(
                    {"role": "user", "content": f"<candidate_answer>{text}</candidate_answer>"}
                )
                async with self._llm_lock:
                    await self._set_state(websocket, PipelineState.PROCESSING)
                    lat = LatencySnapshot()
                    await self._llm_tts_turn(websocket, lat)
                await self._set_state(websocket, PipelineState.LISTENING)
                continue

            action = self._smart_pause.check()
            if action == PauseAction.SOFT_PROMPT:
                await websocket.send_json({"type": "soft_prompt", "text": SOFT_PROMPT_TEXT})
            elif action == PauseAction.RE_ENGAGE:
                await websocket.send_json({"type": "soft_prompt", "text": RE_ENGAGE_TEXT})

    # ── LLM + TTS ──────────────────────────────────────────────────────────────

    async def _llm_tts_turn(
        self,
        websocket: WebSocket,
        lat: LatencySnapshot,
    ) -> tuple[int, int]:
        """Run one LLM generation + TTS synthesis turn.

        Returns (llm_ttft_ms, tts_first_byte_ms).
        TTS runs concurrently with LLM via a sentence queue — LLM is never blocked.
        """
        llm_ttft_ms = 0
        tts_first_byte_ms = 0
        sentence_buf = SentenceBuffer()
        full_response = ""
        llm_start = time.monotonic()
        first_token = True

        # Queue for sentences ready for TTS — decouples LLM streaming from TTS
        tts_queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def _tts_worker() -> None:
            """Process sentences from the queue and synthesize audio.

            Each sentence's text is sent to the frontend right after its
            audio finishes — the user sees the bot's response appear
            sentence-by-sentence as they hear it.
            """
            nonlocal tts_first_byte_ms

            while True:
                sentence = await tts_queue.get()
                if sentence is None:
                    break  # Poison pill — LLM done

                # Check if user interrupted before starting TTS for this sentence
                if self._interrupted.is_set():
                    while not tts_queue.empty():
                        try:
                            tts_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    break

                # Strip markdown before TTS and display
                clean_sentence = _strip_markdown(sentence)
                if not clean_sentence:
                    continue

                # Send text BEFORE audio so text and speech appear simultaneously
                await websocket.send_json(
                    {"type": "llm_chunk", "text": clean_sentence, "is_final": False}
                )

                tts_start = time.monotonic()
                fb_ms = 0

                await self._set_state(websocket, PipelineState.SPEAKING)
                async for audio_chunk in self._synthesize_with_fallback(clean_sentence):
                    if self._interrupted.is_set():
                        logger.info("pipeline.tts_interrupted")
                        break
                    if fb_ms == 0:
                        fb_ms = int((time.monotonic() - tts_start) * 1000)
                    encoded = base64.b64encode(audio_chunk).decode()
                    await websocket.send_json(
                        {
                            "type": "audio_chunk",
                            "data": encoded,
                            "x_latency": {
                                "tts_first_byte_ms": fb_ms,
                                "e2e_ms": int((time.monotonic() - llm_start) * 1000),
                            },
                        }
                    )

                await self._log_tts_cost(sentence)
                if tts_first_byte_ms == 0:
                    tts_first_byte_ms = fb_ms

                # Back to processing state if more sentences may come
                await self._set_state(websocket, PipelineState.PROCESSING)

        # Start TTS worker concurrently
        tts_task = asyncio.create_task(_tts_worker())

        # Inject tool context (board or code state) into the last user message
        # so the LLM sees what the candidate has drawn/written — without
        # polluting self._conversation (history stays clean).
        _messages = list(self._conversation)
        if self._tool_context and _messages and _messages[-1]["role"] == "user":
            _messages = _messages[:-1] + [
                {
                    "role": "user",
                    "content": f"{self._tool_context}\n\n---\n{_messages[-1]['content']}",
                }
            ]

        async for token in self._providers.voice_llm.generate_stream(
            messages=_messages,
            system=self._system_prompt,
            max_tokens=tuning.PIPELINE_LLM_MAX_TOKENS,
        ):
            if first_token:
                llm_ttft_ms = int((time.monotonic() - llm_start) * 1000)
                first_token = False
                logger.debug("pipeline.llm_ttft", ms=llm_ttft_ms)

            full_response += token

            # [WAIT] escape hatch — if the LLM thinks the answer was incomplete,
            # it outputs "[WAIT]". We abort TTS and return to listening.
            # Guard: after 2 consecutive [WAIT] signals, stop waiting — the user
            # probably said something complete and the LLM is miscalibrating.
            if (
                full_response.strip().startswith("[WAIT]")
                and self._wait_count < tuning.PIPELINE_MAX_WAIT_COUNT
            ):
                logger.info("pipeline.llm_wait_signal", response_len=len(full_response))
                await tts_queue.put(None)
                await tts_task
                self._interrupted.clear()
                # Remove the user message we just added — it will be carried over
                if self._conversation and self._conversation[-1]["role"] == "user":
                    self._conversation.pop()
                return 0, 0  # Signal to caller: no real turn happened

            # Text is sent by _tts_worker AFTER each sentence's audio finishes

            # Enqueue completed sentences for TTS (non-blocking)
            for sentence in sentence_buf.add(token):
                await tts_queue.put(sentence)

        # Flush remainder
        remainder = sentence_buf.flush()
        if remainder:
            await tts_queue.put(remainder)

        # Signal TTS worker to stop and wait for it
        await tts_queue.put(None)
        await tts_task

        await websocket.send_json({"type": "llm_chunk", "text": "", "is_final": True})

        # Reset interrupt flag for next turn
        self._interrupted.clear()

        # Append assistant turn
        self._conversation.append({"role": "assistant", "content": full_response})

        # Log LLM usage
        metrics = self._providers.voice_llm.get_last_metrics()
        if metrics:
            await self._log_llm_cost(metrics)

        return llm_ttft_ms, tts_first_byte_ms

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _text_process_loop(
        self,
        websocket: WebSocket,
        text_in: asyncio.Queue[str | None],
    ) -> None:
        """Handle text_input messages — bypasses STT, goes straight to LLM+TTS.

        Activated when client sends {type: "text_input", text: "..."} after
        3 consecutive low-confidence STT results, or when the user types manually.

        Text input is ALWAYS treated as a complete answer — [WAIT] is never valid
        here, because the user deliberately submitted the text.
        If the LLM still returns [WAIT] (e.g. for a very short text), we retry
        once with an explicit note to force a real response.
        """
        while True:
            text = await text_in.get()
            if text is None:
                break

            self._low_confidence_count = 0

            # Prepend any carryover from a prior [WAIT] or barge-in
            if self._carryover_text:
                text = (self._carryover_text + " " + text).strip()
                self._carryover_text = ""

            self._conversation.append(
                {"role": "user", "content": f"<candidate_answer>{text}</candidate_answer>"}
            )

            async with self._llm_lock:
                await self._set_state(websocket, PipelineState.PROCESSING)
                lat = LatencySnapshot()
                llm_ttft, tts_fb = await self._llm_tts_turn(websocket, lat)

            # If LLM returned [WAIT] on a text_input, force a real response.
            # Text inputs are always deliberate — the user is done speaking.
            if llm_ttft == 0 and tts_fb == 0:
                logger.warning("pipeline.text_input_got_wait_forcing_response")
                # Re-add user message with an explicit force-respond note
                self._conversation.append(
                    {
                        "role": "user",
                        "content": "[The candidate finished their answer. Please respond now.]",
                    }
                )
                async with self._llm_lock:
                    lat2 = LatencySnapshot()
                    llm_ttft, tts_fb = await self._llm_tts_turn(websocket, lat2)
                    lat.llm_ttft_ms = llm_ttft
                    lat.tts_latency_ms = tts_fb
                # Clean up the injected force note from conversation history
                if self._conversation and self._conversation[-1]["role"] == "user":
                    self._conversation.pop()
            else:
                lat.llm_ttft_ms = llm_ttft
                lat.tts_latency_ms = tts_fb

            self._wait_count = 0
            lat.e2e_latency_ms = (lat.llm_ttft_ms or 0) + (lat.tts_latency_ms or 0)

            await self._log_latency(lat)
            await self._save_transcript_turn()
            await self._set_state(websocket, PipelineState.LISTENING)

    def _activate_tts_fallback(self) -> None:
        """Switch to Deepgram TTS if primary TTS provider fails."""
        if self._tts_fallback_active:
            return
        from app.config import Settings

        settings = Settings()
        self._providers.tts = DeepgramTTSProvider(api_key=settings.deepgram_api_key)
        self._tts_fallback_active = True
        logger.warning("pipeline.tts_fallback_activated", reason="primary TTS provider failed")

    async def _synthesize_with_fallback(self, text: str) -> AsyncGenerator[bytes]:
        """Try primary TTS, fall back to Deepgram on failure."""
        try:
            async for chunk in self._providers.tts.synthesize_stream(text):
                yield chunk
        except Exception as exc:
            if self._tts_fallback_active:
                raise  # Already on fallback, don't loop
            logger.warning("pipeline.tts_error", error=str(exc))
            err_str = str(exc)
            self._tts_fallback_reason = (
                "auth" if ("401" in err_str or "Unauthorized" in err_str) else "error"
            )
            self._activate_tts_fallback()
            async for chunk in self._providers.tts.synthesize_stream(text):
                yield chunk

    async def _send_opening(self, websocket: WebSocket) -> None:
        """Send an AI greeting to kick off the session."""
        opening = "Hello! I'm ready to begin your interview. Whenever you're ready, let's start."
        # Send text first so it appears as audio starts playing
        await websocket.send_json({"type": "llm_chunk", "text": opening, "is_final": False})
        await websocket.send_json({"type": "llm_chunk", "text": "", "is_final": True})
        await self._set_state(websocket, PipelineState.SPEAKING)
        async for audio_chunk in self._synthesize_with_fallback(opening):
            if self._interrupted.is_set():
                break
            encoded = base64.b64encode(audio_chunk).decode()
            await websocket.send_json({"type": "audio_chunk", "data": encoded, "x_latency": {}})
        self._interrupted.clear()
        self._conversation.append({"role": "assistant", "content": opening})
        await self._log_tts_cost(opening)
        await self._set_state(websocket, PipelineState.LISTENING)

    async def _set_state(self, websocket: WebSocket, state: PipelineState) -> None:
        self._state = state
        # Activate/deactivate smart pause based on state
        if state == PipelineState.LISTENING:
            self._smart_pause.activate()
        else:
            self._smart_pause.deactivate()
        await websocket.send_json({"type": "session_state", "state": state.value})

    async def _send_error(self, websocket: WebSocket, message: str) -> None:
        try:
            await websocket.send_json({"type": "error", "message": message})
        except Exception:
            pass

    async def _save_transcript_turn(self) -> None:
        """Sync in-memory conversation to session.transcript JSONB after each turn.

        Called after every complete user-turn + AI-response cycle so that
        a disconnected session has a partial transcript, not an empty one.
        The <candidate_answer> delimiters used in LLM context are stripped here
        so the stored transcript is clean for frontend display and scoring.
        """
        self._session.transcript = [
            {
                "role": msg["role"],
                "content": msg["content"]
                .replace("<candidate_answer>", "")
                .replace("</candidate_answer>", ""),
                "ts_ms": idx * 1000,  # Approximate; real timestamps via transcript_words table
            }
            for idx, msg in enumerate(self._conversation)
        ]
        await self._db.commit()

    async def _save_transcript_words(self, chunk: TranscriptChunk) -> None:
        """Persist word-level timestamps to transcript_words (TTL 14 days)."""
        if not chunk.words:
            return
        try:
            expires = datetime.now(tz=UTC) + timedelta(days=_WORD_TTL_DAYS)
            records = [
                TranscriptWord(
                    session_id=self._session.id,
                    word=w.word,
                    start_ms=w.start_ms,
                    end_ms=w.end_ms,
                    confidence=w.confidence,
                    speaker=w.speaker,
                    expires_at=expires,
                )
                for w in chunk.words
            ]
            self._db.add_all(records)
            await self._db.flush()
        except Exception as exc:
            logger.warning("pipeline.save_words_error", error=str(exc))
            try:
                await self._db.rollback()
            except Exception:
                pass

    async def _log_latency(self, lat: LatencySnapshot) -> None:
        """Write one SessionMetrics row for this voice exchange."""
        logger.info(
            "pipeline.latency",
            session_id=str(self._session.id),
            e2e_ms=lat.e2e_latency_ms,
            stt_ms=lat.stt_latency_ms,
            llm_ttft_ms=lat.llm_ttft_ms,
            tts_ms=lat.tts_latency_ms,
        )
        try:
            metric = SessionMetrics(
                session_id=self._session.id,
                stt_latency_ms=lat.stt_latency_ms,
                llm_ttft_ms=lat.llm_ttft_ms,
                tts_latency_ms=lat.tts_latency_ms,
                e2e_latency_ms=lat.e2e_latency_ms,
            )
            self._db.add(metric)
            await self._db.commit()
        except Exception as exc:
            logger.warning("pipeline.log_latency_error", error=str(exc))
            try:
                await self._db.rollback()
            except Exception:
                pass

    async def _log_stt_cost(self, chunk: TranscriptChunk) -> None:
        """Estimate and log Deepgram STT cost for this audio segment."""
        if chunk.end_ms == 0:
            return
        audio_secs = (chunk.end_ms - chunk.start_ms) / 1000.0
        cost = calc_deepgram_stt_cost(audio_secs)
        self._total_cost += cost
        try:
            await log_usage(
                self._db,
                provider="deepgram",
                operation="stt",
                cost_usd=cost,
                latency_ms=chunk.end_ms - chunk.start_ms,
                session_id=self._session.id,
                user_id=self._user_id,
                audio_seconds=audio_secs,
                quality_profile=self._providers.quality_profile,
            )
        except Exception as exc:
            logger.warning("pipeline.log_stt_cost_error", error=str(exc))

    async def _log_llm_cost(self, metrics) -> None:  # type: ignore[no-untyped-def]
        model = self._providers.voice_llm.model  # type: ignore[attr-defined]
        cost = calc_anthropic_cost(
            model=model,
            input_tokens=metrics.input_tokens,
            output_tokens=metrics.output_tokens,
            cached_tokens=metrics.cached_tokens,
        )
        self._total_cost += cost
        try:
            await log_usage(
                self._db,
                provider="anthropic",
                operation="voice_llm",
                cost_usd=cost,
                latency_ms=metrics.total_latency_ms,
                session_id=self._session.id,
                user_id=self._user_id,
                input_tokens=metrics.input_tokens,
                output_tokens=metrics.output_tokens,
                cached_tokens=metrics.cached_tokens,
                quality_profile=self._providers.quality_profile,
                cached=metrics.cached_tokens > 0,
            )
        except Exception as exc:
            logger.warning("pipeline.log_llm_cost_error", error=str(exc))

    async def _log_tts_cost(self, text: str) -> None:
        characters = len(text)
        provider_name = type(self._providers.tts).__name__
        if "ElevenLabs" in provider_name:
            cost = calc_elevenlabs_cost(characters)
            provider = "elevenlabs"
            operation = "tts"
        else:
            cost = calc_deepgram_tts_cost(characters)
            provider = "deepgram"
            operation = "tts_budget"

        self._total_cost += cost
        try:
            tts_metrics = await self._providers.tts.get_last_metrics()
            await log_usage(
                self._db,
                provider=provider,
                operation=operation,
                cost_usd=cost,
                latency_ms=tts_metrics.total_latency_ms,
                session_id=self._session.id,
                user_id=self._user_id,
                characters=characters,
                quality_profile=self._providers.quality_profile,
            )
        except Exception as exc:
            logger.warning("pipeline.log_tts_cost_error", error=str(exc))

    async def _finalize_session(self) -> None:
        """Mark session completed, save final transcript, commit all pending writes."""
        from app.models.interview_session import SessionStatus

        # Final transcript sync — strip <candidate_answer> delimiters (same as _save_transcript_turn)
        self._session.transcript = [
            {
                "role": msg["role"],
                "content": msg["content"]
                .replace("<candidate_answer>", "")
                .replace("</candidate_answer>", ""),
                "ts_ms": idx * 1000,
            }
            for idx, msg in enumerate(self._conversation)
        ]
        self._session.status = SessionStatus.COMPLETED
        self._session.ended_at = datetime.now(tz=UTC)
        self._session.total_cost_usd = self._total_cost
        await self._db.commit()
        logger.info(
            "pipeline.session_finalized",
            session_id=str(self._session.id),
            turns=len(self._conversation),
            total_cost_usd=str(self._total_cost),
        )


# Threshold reference (defined in deepgram_stt.py but used here for clarity)
DeepgramSTTProvider_THRESHOLD = 0.60
