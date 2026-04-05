/**
 * useVoiceSession — WebSocket + MediaRecorder hook for the voice pipeline.
 *
 * Week 2 additions:
 *   - Auto-reconnect: 3 attempts with exponential backoff (1s, 2s, 4s)
 *   - VAD noise gate: AnalyserNode pauses MediaRecorder during silence
 *     (reduces Deepgram STT cost; reuses analyser data for waveform viz)
 *   - Low-confidence fallback: after 3 consecutive weak STT finals,
 *     sets textMode=true so the UI shows a text input instead of mic
 *   - Provider-level timeout: each audio chunk capped at 30s before re-try
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type SessionState =
  | "idle"
  | "connecting"
  | "reconnecting"
  | "listening"
  | "processing"
  | "speaking"
  | "error";

export interface TranscriptEntry {
  role: "user" | "assistant";
  text: string;
  isFinal: boolean;
}

export interface LatencyStats {
  sttMs?: number;
  llmTtftMs?: number;
  ttsMs?: number;
  e2eMs?: number;
}

interface UseVoiceSessionOptions {
  sessionId: string;
  accessToken: string;
  apiBaseUrl?: string;
  onTimeLimitReached?: () => void;
}

interface UseVoiceSessionReturn {
  state: SessionState;
  transcript: TranscriptEntry[];
  latency: LatencyStats;
  waveformData: Uint8Array | null;
  textMode: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  sendText: (text: string) => void;
  updateToolContext: (context: string | null) => void;
  error: string | null;
  softPrompt: string | null;
}

const RECONNECT_DELAYS_MS = [1000, 2000, 4000];
const AUDIO_CHUNK_MS = 250;
const SILENCE_THRESHOLD = 8;        // AnalyserNode byte value (0–255); below = silence
const LOW_CONFIDENCE_LIMIT = 1;     // Switch to text mode after backend sends low_confidence_fallback
const BARGE_IN_AMPLITUDE = 80;      // AnalyserNode byte value threshold for barge-in detection
const BARGE_IN_FRAME_COUNT = 3;     // Consecutive loud frames required to trigger barge-in
const VAD_INTERVAL_MS = 100;        // VAD polling interval in milliseconds

export function useVoiceSession({
  sessionId,
  accessToken,
  apiBaseUrl = "",
  onTimeLimitReached,
}: UseVoiceSessionOptions): UseVoiceSessionReturn {
  const [state, setState] = useState<SessionState>("idle");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [latency, setLatency] = useState<LatencyStats>({});
  const [waveformData, setWaveformData] = useState<Uint8Array | null>(null);
  const [textMode, setTextMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [softPrompt, setSoftPrompt] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const playingRef = useRef(false);
  const activeSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const reconnectCountRef = useRef(0);
  const intentionalDisconnectRef = useRef(false);
  const lowConfCountRef = useRef(0);
  const waveformRafRef = useRef<number | null>(null);
  const vadIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stateRef = useRef<SessionState>("idle");
  const bargeInCountRef = useRef(0);
  const softPromptTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onTimeLimitReachedRef = useRef(onTimeLimitReached);
  useEffect(() => { onTimeLimitReachedRef.current = onTimeLimitReached; }, [onTimeLimitReached]);

  // ── Audio playback ─────────────────────────────────────────────────────────

  const playNextChunk = useCallback(async () => {
    if (playingRef.current || audioQueueRef.current.length === 0) return;
    const ctx = audioContextRef.current;
    if (!ctx) return;
    playingRef.current = true;
    const buf = audioQueueRef.current.shift()!;
    try {
      // Resume AudioContext if browser suspended it (tab switch, headset reconnect, inactivity)
      if (ctx.state === "suspended") await ctx.resume();
      const decoded = await ctx.decodeAudioData(buf);
      const src = ctx.createBufferSource();
      src.buffer = decoded;
      src.connect(ctx.destination);
      activeSourceRef.current = src;
      setState("speaking");
      stateRef.current = "speaking";
      src.onended = () => {
        activeSourceRef.current = null;
        playingRef.current = false;
        if (audioQueueRef.current.length === 0) {
          setState("listening");
          stateRef.current = "listening";
        }
        playNextChunk();
      };
      src.start();
    } catch {
      activeSourceRef.current = null;
      playingRef.current = false;
      playNextChunk();
    }
  }, []);

  // Barge-in: stop all audio playback immediately
  const stopAudioPlayback = useCallback(() => {
    audioQueueRef.current = [];
    if (activeSourceRef.current) {
      try { activeSourceRef.current.stop(); } catch { /* already stopped */ }
      activeSourceRef.current = null;
    }
    playingRef.current = false;
  }, []);

  const enqueueAudio = useCallback((b64: string) => {
    const bin = atob(b64);
    const buf = new ArrayBuffer(bin.length);
    const view = new Uint8Array(buf);
    for (let i = 0; i < bin.length; i++) view[i] = bin.charCodeAt(i);
    audioQueueRef.current.push(buf);
    playNextChunk();
  }, [playNextChunk]);

  // ── Waveform animation ─────────────────────────────────────────────────────

  const startWaveform = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      analyser.getByteFrequencyData(data);
      setWaveformData(new Uint8Array(data));
      waveformRafRef.current = requestAnimationFrame(tick);
    };
    waveformRafRef.current = requestAnimationFrame(tick);
  }, []);

  const stopWaveform = useCallback(() => {
    if (waveformRafRef.current !== null) {
      cancelAnimationFrame(waveformRafRef.current);
      waveformRafRef.current = null;
    }
    setWaveformData(null);
  }, []);

  // ── VAD silence gate ───────────────────────────────────────────────────────
  // Pauses MediaRecorder during silence — reduces Deepgram STT cost.

  const startVADGate = useCallback(() => {
    const analyser = analyserRef.current;
    const recorder = mediaRecorderRef.current;
    if (!analyser || !recorder) return;
    const buf = new Uint8Array(analyser.frequencyBinCount);

    vadIntervalRef.current = setInterval(() => {
      analyser.getByteFrequencyData(buf);
      const avg = buf.reduce((s, v) => s + v, 0) / buf.length;
      const isSilent = avg < SILENCE_THRESHOLD;

      // Barge-in: if user speaks while bot is speaking, stop playback
      if (stateRef.current === "speaking") {
        if (avg > BARGE_IN_AMPLITUDE) {
          bargeInCountRef.current += 1;
          if (bargeInCountRef.current >= BARGE_IN_FRAME_COUNT) {
            bargeInCountRef.current = 0;
            stopAudioPlayback();
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ type: "interrupt" }));
            }
          }
        } else {
          bargeInCountRef.current = 0;
        }
      } else {
        bargeInCountRef.current = 0;
      }

      // Note: we do NOT pause/resume MediaRecorder anymore.
      // Keeping audio flowing prevents Deepgram STT from timing out.
    }, VAD_INTERVAL_MS);
  }, [stopAudioPlayback]);

  const stopVADGate = useCallback(() => {
    if (vadIntervalRef.current !== null) {
      clearInterval(vadIntervalRef.current);
      vadIntervalRef.current = null;
    }
  }, []);

  // ── WebSocket message handler ──────────────────────────────────────────────

  const handleMessage = useCallback((msg: MessageEvent) => {
    const data = JSON.parse(msg.data as string);

    switch (data.type) {
      case "session_state": {
        if (data.state === "time_limit_reached") {
          // Session duration limit expired — trigger the same graceful end as pressing End Session
          onTimeLimitReachedRef.current?.();
          break;
        }
        const newState = data.state as SessionState;
        // Don't let backend "speaking" override — frontend sets "speaking" when audio actually plays
        // Only accept "listening", "processing", and error-like states from backend
        if (newState !== "speaking") {
          setState(newState);
          stateRef.current = newState;
        }
        break;
      }

      case "transcript_interim":
      case "transcript_partial":
        // Backend sends full cumulative turn text. Replace the last user bubble if it exists
        // (even if isFinal — multiple transcript_final events are merged into one visual bubble
        // until the bot actually responds). Create a new bubble only after a bot response.
        setTranscript((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "user") {
            return [...prev.slice(0, -1), { role: "user", text: data.text, isFinal: false }];
          }
          return [...prev, { role: "user", text: data.text, isFinal: false }];
        });
        break;

      case "transcript_final":
        // Silence gap detected — update (or create) the user bubble with the latest text.
        // Still marked isFinal: true, but the next interim/partial will un-final it if the
        // user continues speaking before the bot responds.
        setSoftPrompt(null);
        setTranscript((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "user") {
            return [...prev.slice(0, -1), { role: "user", text: data.text, isFinal: true }];
          }
          return [...prev, { role: "user", text: data.text, isFinal: true }];
        });
        if (data.x_latency?.stt_ms) setLatency((l) => ({ ...l, sttMs: data.x_latency.stt_ms }));
        lowConfCountRef.current = 0;
        break;

      case "transcript_rollback":
        // LLM decided the answer was incomplete ([WAIT] signal) — remove the
        // premature user bubble so it doesn't clutter the chat.
        setTranscript((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "user") {
            return prev.slice(0, -1);
          }
          return prev;
        });
        break;

      case "low_confidence_fallback":
        lowConfCountRef.current += 1;
        if (lowConfCountRef.current >= LOW_CONFIDENCE_LIMIT) {
          setTextMode(true);
        }
        break;

      case "llm_chunk":
        if (data.is_final) {
          // Mark assistant entry as final
          setTranscript((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === "assistant") {
              return [...prev.slice(0, -1), { ...last, isFinal: true }];
            }
            return prev;
          });
          break;
        }
        setTranscript((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && !last.isFinal) {
            return [
              ...prev.slice(0, -1),
              { role: "assistant", text: last.text + data.text, isFinal: false },
            ];
          }
          return [...prev, { role: "assistant", text: data.text, isFinal: false }];
        });
        if (data.x_latency?.llm_ttft_ms) {
          setLatency((l) => ({ ...l, llmTtftMs: data.x_latency.llm_ttft_ms }));
        }
        break;

      case "audio_chunk":
        enqueueAudio(data.data);
        if (data.x_latency) {
          setLatency((l) => ({
            ...l,
            ttsMs: data.x_latency.tts_first_byte_ms ?? l.ttsMs,
            e2eMs: data.x_latency.e2e_ms ?? l.e2eMs,
          }));
        }
        break;

      case "soft_prompt":
        // Show as a dismissing toast — does NOT insert into chat transcript,
        // which would cause the next user speech to create a new bubble.
        if (softPromptTimerRef.current) clearTimeout(softPromptTimerRef.current);
        setSoftPrompt(data.text);
        softPromptTimerRef.current = setTimeout(() => setSoftPrompt(null), 5000);
        break;

      case "error":
        setError(data.message);
        // Non-recoverable errors — stop reconnecting
        if (
          data.message?.includes("pipeline") ||
          data.message?.includes("API") ||
          data.message?.includes("provider") ||
          data.message?.includes("key") ||
          data.message?.includes("not active") ||
          data.message?.includes("not found") ||
          data.message?.includes("Unauthorized")
        ) {
          intentionalDisconnectRef.current = true;
        }
        setState("error");
        break;
    }
  }, [enqueueAudio]);

  // ── Core connect ───────────────────────────────────────────────────────────

  const _connectInternal = useCallback(async () => {
    // Guard: prevent duplicate connections — if already open or connecting, bail out
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    setState(reconnectCountRef.current > 0 ? "reconnecting" : "connecting");
    setError(null);

    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext();
    }
    // Resume AudioContext for Safari (requires user gesture)
    if (audioContextRef.current.state === "suspended") {
      await audioContextRef.current.resume();
    }

    // Mic stream — use ideal constraints so any mic/headset works
    // Don't force sampleRate — Deepgram auto-detects from webm/opus container
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    } catch {
      setError("Microphone access denied — please allow mic access and retry.");
      setState("error");
      return;
    }
    streamRef.current = stream;

    // AnalyserNode for VAD gate + waveform
    const ctx = audioContextRef.current;
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;
    source.connect(analyser);
    analyserRef.current = analyser;

    // WebSocket
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const host = apiBaseUrl || `${proto}://${window.location.hostname}:8080`;
    const ws = new WebSocket(`${host}/api/v1/sessions/${sessionId}/voice?token=${accessToken}`);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectCountRef.current = 0;
      lowConfCountRef.current = 0;
      setSoftPrompt(null);
      setTextMode(false);

      // MediaRecorder — webm/opus preferred, fallback for Safari/other browsers
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : MediaRecorder.isTypeSupported("audio/mp4")
            ? "audio/mp4"
            : "";  // No supported format

      let recorder: MediaRecorder;
      try {
        if (!mimeType) {
          throw new Error("No supported audio recording format found in this browser.");
        }
        recorder = new MediaRecorder(stream, { mimeType });
      } catch (err) {
        setError(`Cannot start audio recording: ${err instanceof Error ? err.message : String(err)}. Try a different browser or check audio device.`);
        setState("error");
        stream.getTracks().forEach((t) => t.stop());
        ws.close();
        return;
      }
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (ws.readyState === WebSocket.OPEN && e.data.size > 0) {
          const reader = new FileReader();
          reader.onloadend = () => {
            const b64 = (reader.result as string).split(",")[1];
            ws.send(JSON.stringify({ type: "audio", data: b64 }));
          };
          reader.readAsDataURL(e.data);
        }
      };

      try {
        recorder.start(AUDIO_CHUNK_MS);
      } catch (err) {
        setError(`Failed to start recording: ${err instanceof Error ? err.message : String(err)}. Try reconnecting or check your audio device.`);
        setState("error");
        stream.getTracks().forEach((t) => t.stop());
        ws.close();
        return;
      }
      startVADGate();
      startWaveform();
    };

    ws.onmessage = handleMessage;

    ws.onerror = () => setError("Connection error — retrying...");

    ws.onclose = (ev) => {
      stopVADGate();
      stopWaveform();
      mediaRecorderRef.current?.stop();
      stream.getTracks().forEach((t) => t.stop());

      if (intentionalDisconnectRef.current) {
        intentionalDisconnectRef.current = false;
        setState("idle");
        return;
      }

      // Auto-reconnect
      if (reconnectCountRef.current < RECONNECT_DELAYS_MS.length) {
        const delay = RECONNECT_DELAYS_MS[reconnectCountRef.current++];
        setTimeout(() => _connectInternal(), delay);
      } else {
        setError(`Connection lost after ${reconnectCountRef.current} retries.`);
        setState("error");
      }
    };
  }, [sessionId, accessToken, apiBaseUrl, handleMessage, startVADGate, startWaveform, stopVADGate, stopWaveform]);

  const connect = useCallback(async () => {
    reconnectCountRef.current = 0;
    intentionalDisconnectRef.current = false;
    await _connectInternal();
  }, [_connectInternal]);

  // ── Disconnect ─────────────────────────────────────────────────────────────

  const disconnect = useCallback(() => {
    intentionalDisconnectRef.current = true;
    stopVADGate();
    stopWaveform();
    mediaRecorderRef.current?.stop();
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "end_audio" }));
      wsRef.current.close(1000, "user_ended");
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    setState("idle");
  }, [stopVADGate, stopWaveform]);

  // ── Text mode input ────────────────────────────────────────────────────────

  const sendText = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "text_input", text }));
    setTranscript((prev) => [...prev, { role: "user", text, isFinal: true }]);
  }, []);

  const updateToolContext = useCallback((context: string | null) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "tool_context", context: context ?? "" }));
  }, []);

  // ── Cleanup ────────────────────────────────────────────────────────────────

  useEffect(() => {
    return () => {
      intentionalDisconnectRef.current = true;
      wsRef.current?.close();
      audioContextRef.current?.close();
      stopVADGate();
      stopWaveform();
    };
  }, [stopVADGate, stopWaveform]);

  return { state, transcript, latency, waveformData, textMode, connect, disconnect, sendText, updateToolContext, error, softPrompt };
}
