# ADR-005: Provider interfaces and their current boundary

Status: accepted design, implementation notes reviewed 6 November 2026.

The custom asyncio voice pipeline uses `STTProvider`, `LLMProvider`, `TTSProvider` ABCs and a per-session `ProviderSet`. ProviderFactory selects concrete implementations. This is an application integration boundary, not a universal multi-agent platform or a complete plugin system. Pipecat is a declared dependency, not the current voice orchestrator.

## Factory routing

| Profile | Voice LLM | Task LLM fields | Primary TTS |
|---|---|---|---|
| quality | Sonnet | Sonnet | ElevenLabs |
| balanced | Sonnet | Haiku | ElevenLabs |
| budget | Haiku | Haiku | Deepgram Aura |

An OpenAI BYOK adapter can be selected for the voice/provider set; its secondary model routing differs. This table describes the default Anthropic factory route, not every call in the application. Scorer instantiates AsyncAnthropic directly and memory components also make direct Anthropic calls. They do not all consume the ProviderSet task fields. Voice usage accounting is not fully provider-neutral, so an OpenAI adapter must not be sold as verified full-application interchangeability.

## Credential ownership and fallback

The factory resolves Deepgram once: a supplied user key takes precedence, otherwise the configured platform key is used. That key constructs STT, budget TTS and the session's fallback TTS. The pipeline receives `fallback_tts` explicitly and never reloads Settings or constructs a platform-key fallback during a primary-provider failure. Quality/balanced can switch ElevenLabs→that configured Deepgram instance. Budget already uses Deepgram and has no second fallback. Invalid BYOK credentials must fail, not transfer spending to a platform key. Owner-supplied keys for different providers are still separate credentials; this does not mean all providers have one account owner.

Tests in `backend/tests/test_provider_factory.py`, `test_voice_providers.py` and `test_portfolio_regressions.py` use fake providers/credentials, including BYOK and failure paths. They verify routing and cancellation/failure mechanics without API calls; real audio quality, authorization and invoices remain live checks.
