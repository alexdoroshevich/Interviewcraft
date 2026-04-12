# ADR-005: Provider Abstractions

**Status:** Accepted
**Date:** 2026-02-24
**Authors:** Lead Dev + Architect

---

## Problem

The system uses multiple AI providers (Anthropic, Deepgram, ElevenLabs) for different tasks.
How do we structure the code so we can:
1. Swap providers without changing business logic.
2. Route to different models based on quality profile.
3. Test without real API keys.

---

## Options Considered

### Option A: Direct provider calls everywhere

- Each module calls `anthropic.messages.create(...)` directly.
- Simple but tightly coupled.
- Swapping providers = searching for all call sites.
- **Rejected**: No testability, no routing.

### Option B: Abstract base classes (ABCs) + ProviderSet

- `STTProvider`, `LLMProvider`, `TTSProvider` as ABCs.
- `ProviderSet` contains per-task LLM instances:
  `voice_llm`, `scoring_llm`, `diff_llm`, `memory_llm`.
- Factory selects concrete implementations based on config.
- **Selected** ✅

### Option C: Plugin/registry system

- Providers self-register via entry points.
- Dynamic loading at startup.
- Over-engineering for MVP with 3 providers.
- **Rejected**: Too complex for 3 fixed providers.

---

## Decision

**ABCs + ProviderSet. Per-task LLM routing based on quality profile.**

### Interface design

```python
# app/services/voice/interfaces.py

class STTProvider(ABC):
    @abstractmethod
    async def transcribe_stream(self, audio_chunks: AsyncIterator[bytes]
                                ) -> AsyncIterator[TranscriptChunk]: ...

class LLMProvider(ABC):
    @abstractmethod
    async def generate_stream(self, messages: list[dict],
                               system: str) -> AsyncIterator[str]: ...

    @abstractmethod
    async def generate_json(self, messages: list[dict],
                             schema: dict) -> dict: ...

class TTSProvider(ABC):
    @abstractmethod
    async def synthesize_stream(self, text_chunks: AsyncIterator[str]
                                 ) -> AsyncIterator[bytes]: ...
```

### ProviderSet

```python
@dataclass
class ProviderSet:
    stt: STTProvider          # Deepgram Nova-2
    tts: TTSProvider          # ElevenLabs Turbo (Quality) / Deepgram Aura (Budget)
    voice_llm: LLMProvider    # Sonnet for all profiles (voice needs quality)
    scoring_llm: LLMProvider  # Sonnet (Quality) / Haiku (Balanced/Budget)
    diff_llm: LLMProvider     # Sonnet (Quality) / Haiku (Balanced/Budget)
    memory_llm: LLMProvider   # Haiku for all profiles (cheap, async OK)
```

### Quality profiles

| Profile | STT | Voice LLM | Scoring LLM | TTS |
|---|---|---|---|---|
| Quality | Deepgram Nova-2 | Sonnet 4.6 | Sonnet 4.6 | ElevenLabs Turbo |
| Balanced | Deepgram Nova-2 | Sonnet 4.6 | Haiku 4.5 | ElevenLabs Turbo |
| Budget | Deepgram Nova-2 | Sonnet 4.6 | Haiku 4.5 | Deepgram Aura |

Note: Voice LLM always Sonnet — latency and quality matter most for real-time conversation.
Scoring/diff/memory can use Haiku since they're async and lower-stakes.

### Current implementation status

The scoring module directly instantiates `AsyncAnthropic` (bypasses ABC for MVP simplicity).
The voice pipeline uses Pipecat which handles provider abstraction internally.

The ABCs in `interfaces.py` are defined and ready for:
- Unit testing with mock providers.
- Swapping providers without changing business logic.
- BYOK (✅ shipped Phase 2): user-supplied provider credentials, encrypted at rest.

---

## Tradeoffs Accepted

| Tradeoff | Rationale |
|---|---|
| Scoring bypasses ABC (direct Anthropic client) | The scoring module is complex enough; adding an ABC layer adds indirection with no immediate benefit. ABCs live in `interfaces.py` for Phase 2. |
| Voice LLM always Sonnet (not profile-selectable) | Haiku voice quality noticeably worse in real-time conversation. User experience > cost savings for voice. |
| No local model support in MVP | Provider ABCs make it possible, but local inference (Ollama, llama.cpp) requires different async patterns. Phase 2. |
| ProviderSet created per-session (not singleton) | Clean, no shared state. Cost: minimal instantiation overhead. |

---

## Phase 2 — Shipped

- **BYOK** ✅ — User-supplied provider credentials encrypted at rest via `app/services/byok.py`. Decrypted in-memory per WebSocket session only.
- **Interviewer personas** ✅ — Routed via ProviderSet per session config.
- **TTS fallback chain** ✅ — Primary TTS failure triggers automatic fallback to secondary provider.

## Future Work (Phase 3+)

- Local mode: Ollama/llama.cpp implementation of LLMProvider.
