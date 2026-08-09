import { useEffect, useMemo, useRef, useState } from 'react';
import { Bot, CircleStop, Headphones, Mic, MicOff, PhoneCall, PhoneOff, Radio, ShieldCheck, Sparkles, Volume2, Wifi, WifiOff, X } from 'lucide-react';
import { Button } from '../common/UI';
import { platformApi } from '../../services/platformApi';
import './VoiceAgent.css';

export type VoiceLanguage = 'English' | 'Sinhala' | 'Tamil';

type VoiceStatus = 'idle' | 'connecting' | 'listening' | 'thinking' | 'tool' | 'speaking' | 'error';
type TranscriptItem = { id: string; role: 'user' | 'assistant' | 'system'; text: string };

type VoiceAgentProps = {
  language: VoiceLanguage;
  project: any;
  profile: any;
  onDecision?: (result: any, question: string) => void;
};

type VoiceTokenResponse = {
  token: string;
  expires_at: string;
  new_session_expires_at: string;
  model: string;
  voice: string;
  language: VoiceLanguage;
  system_instruction: string;
};

const LIVE_URL = 'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained';

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  const stride = 0x8000;
  for (let i = 0; i < bytes.length; i += stride) {
    binary += String.fromCharCode(...bytes.subarray(i, Math.min(i + stride, bytes.length)));
  }
  return btoa(binary);
}

function base64ToInt16(base64: string): Int16Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new Int16Array(bytes.buffer);
}

function mergeTranscript(previous: string, incoming: string): string {
  const next = incoming.trim();
  if (!next) return previous;
  if (!previous) return next;
  if (next.startsWith(previous)) return next;
  if (previous.endsWith(next)) return previous;
  return `${previous} ${next}`.replace(/\s+/g, ' ').trim();
}

function projectContext(project: any, profile: any, language: VoiceLanguage) {
  return {
    province: project?.province || '',
    location: project?.district || profile?.district || 'Sri Lanka',
    project_id: project?.id || '',
    farm_id: project?.farm_id || '',
    lat: project?.lat || profile?.lat || 7.291,
    lon: project?.lon || profile?.lon || 81.674,
    crop: project?.crop || '',
    stage: project?.stage || '',
    language,
  };
}

class PcmPlayer {
  private context: AudioContext | null = null;
  private nextStart = 0;
  private sources = new Set<AudioBufferSourceNode>();

  async ensure() {
    if (!this.context || this.context.state === 'closed') this.context = new AudioContext();
    if (this.context.state === 'suspended') await this.context.resume();
    this.nextStart = Math.max(this.nextStart, this.context.currentTime);
    return this.context;
  }

  async enqueue(base64: string) {
    const context = await this.ensure();
    const pcm = base64ToInt16(base64);
    if (!pcm.length) return;

    const buffer = context.createBuffer(1, pcm.length, 24000);
    const channel = buffer.getChannelData(0);
    for (let i = 0; i < pcm.length; i += 1) channel[i] = pcm[i] / 32768;

    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);
    const startAt = Math.max(context.currentTime + 0.015, this.nextStart);
    source.start(startAt);
    this.nextStart = startAt + buffer.duration;
    this.sources.add(source);
    source.onended = () => this.sources.delete(source);
  }

  clear() {
    for (const source of this.sources) {
      try { source.stop(); } catch { /* already stopped */ }
    }
    this.sources.clear();
    if (this.context) this.nextStart = this.context.currentTime;
  }

  async close() {
    this.clear();
    if (this.context && this.context.state !== 'closed') await this.context.close();
    this.context = null;
    this.nextStart = 0;
  }
}

function statusCopy(status: VoiceStatus, muted: boolean) {
  if (muted) return 'Microphone muted';
  if (status === 'connecting') return 'Connecting securely…';
  if (status === 'thinking') return 'Understanding your question…';
  if (status === 'tool') return 'Checking farm, weather and safety evidence…';
  if (status === 'speaking') return 'MihiMura is speaking';
  if (status === 'error') return 'Voice connection needs attention';
  if (status === 'listening') return 'Listening — speak naturally';
  return 'Ready';
}

export function VoiceAgent({ language, project, profile, onDecision }: VoiceAgentProps) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState('');
  const [voiceName, setVoiceName] = useState('Gacrux');
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [liveUser, setLiveUser] = useState('');
  const [liveAssistant, setLiveAssistant] = useState('');
  const [sessionStartedAt, setSessionStartedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const captureContextRef = useRef<AudioContext | null>(null);
  const captureNodeRef = useRef<AudioWorkletNode | null>(null);
  const silentGainRef = useRef<GainNode | null>(null);
  const playerRef = useRef(new PcmPlayer());
  const liveUserRef = useRef('');
  const liveAssistantRef = useRef('');
  const closedByUserRef = useRef(false);
  const mutedRef = useRef(false);
  const setupCompleteRef = useRef(false);
  const toolBusyRef = useRef(false);

  const contextLabel = useMemo(() => project
    ? `${project.farm_name || 'Farm'} · ${project.crop || 'Crop'} · ${project.stage || 'Current stage'}`
    : `${profile?.district || 'Sri Lanka'} · General context`, [project, profile]);

  useEffect(() => {
    if (!sessionStartedAt) return;
    const id = window.setInterval(() => setElapsed(Math.floor((Date.now() - sessionStartedAt) / 1000)), 1000);
    return () => window.clearInterval(id);
  }, [sessionStartedAt]);

  useEffect(() => {
    liveUserRef.current = liveUser;
  }, [liveUser]);

  useEffect(() => {
    liveAssistantRef.current = liveAssistant;
  }, [liveAssistant]);

  const pushTranscript = (role: TranscriptItem['role'], text: string) => {
    const clean = text.trim();
    if (!clean) return;
    setTranscript(items => [...items, { id: `${Date.now()}-${Math.random()}`, role, text: clean }].slice(-40));
  };

  const finalizeUser = (fallback = '') => {
    const text = (liveUserRef.current || fallback).trim();
    if (text) pushTranscript('user', text);
    setLiveUser('');
    liveUserRef.current = '';
    return text;
  };

  const finalizeAssistant = () => {
    const text = liveAssistantRef.current.trim();
    if (text) pushTranscript('assistant', text);
    setLiveAssistant('');
    liveAssistantRef.current = '';
  };

  const stopCapture = async (sendEnd = true) => {
    const ws = wsRef.current;
    if (sendEnd && ws?.readyState === WebSocket.OPEN && setupCompleteRef.current) {
      try { ws.send(JSON.stringify({ realtimeInput: { audioStreamEnd: true } })); } catch { /* ignore */ }
    }
    captureNodeRef.current?.disconnect();
    silentGainRef.current?.disconnect();
    micStreamRef.current?.getTracks().forEach(track => track.stop());
    micStreamRef.current = null;
    captureNodeRef.current = null;
    silentGainRef.current = null;
    if (captureContextRef.current && captureContextRef.current.state !== 'closed') {
      await captureContextRef.current.close().catch(() => undefined);
    }
    captureContextRef.current = null;
  };

  const startCapture = async () => {
    if (micStreamRef.current) return;
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !setupCompleteRef.current) return;

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
      },
    });

    const context = new AudioContext({ latencyHint: 'interactive' });
    await context.audioWorklet.addModule('/pcm-capture-worklet.js');
    const source = context.createMediaStreamSource(stream);
    const node = new AudioWorkletNode(context, 'mihimura-pcm-capture');
    const silent = context.createGain();
    silent.gain.value = 0;

    node.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
      const socket = wsRef.current;
      if (mutedRef.current || toolBusyRef.current || !event.data || socket?.readyState !== WebSocket.OPEN) return;
      socket.send(JSON.stringify({
        realtimeInput: {
          audio: {
            data: arrayBufferToBase64(event.data),
            mimeType: 'audio/pcm;rate=16000',
          },
        },
      }));
    };

    source.connect(node);
    node.connect(silent);
    silent.connect(context.destination);

    micStreamRef.current = stream;
    captureContextRef.current = context;
    captureNodeRef.current = node;
    silentGainRef.current = silent;
    if (context.state === 'suspended') await context.resume();
  };

  const handleToolCall = async (toolCall: any) => {
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    const calls = Array.isArray(toolCall?.functionCalls) ? toolCall.functionCalls : [];
    if (!calls.length) return;

    toolBusyRef.current = true;
    setStatus('tool');
    const responses: any[] = [];

    for (const call of calls) {
      if (call.name !== 'consult_mihimura') {
        responses.push({ name: call.name, id: call.id, response: { error: 'Unsupported tool' } });
        continue;
      }

      const question = String(call.args?.question || liveUserRef.current || '').trim();
      finalizeUser(question);

      try {
        const result = await platformApi.ask(question, projectContext(project, profile, language));
        onDecision?.(result, question);
        responses.push({
          name: call.name,
          id: call.id,
          response: {
            result: {
              summary: result.summary,
              recommended_action: result.recommended_action,
              why: result.why,
              confidence: result.confidence,
              risk_level: result.risk_level,
              alternatives: result.alternatives || [],
              do_not_do: result.do_not_do || [],
              confirmation_required: Boolean(result.confirmation_required),
              follow_up: result.follow_up,
              counterfactual: result.counterfactual,
              sources: (result.sources || []).slice(0, 5),
            },
          },
        });
      } catch (exc) {
        const message = exc instanceof Error ? exc.message : 'MihiMura tool request failed';
        responses.push({ name: call.name, id: call.id, response: { error: message } });
      }
    }

    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ toolResponse: { functionResponses: responses } }));
      setStatus('thinking');
    }
    toolBusyRef.current = false;
  };

  const handleMessage = async (event: MessageEvent) => {
    let message: any;
    try { message = JSON.parse(String(event.data)); } catch { return; }

    if (message.setupComplete) {
      setupCompleteRef.current = true;
      setStatus('listening');
      setSessionStartedAt(Date.now());
      setElapsed(0);
      await startCapture();
      const greeting = language === 'Sinhala'
        ? 'කෙටි ස්වභාවික ආයුබෝවන් පණිවිඩයක් කියලා, මම කතා කරනකම් අහගෙන ඉන්න.'
        : language === 'Tamil'
          ? 'ஒரு சுருக்கமான இயல்பான வணக்கத்தைச் சொல்லி, நான் பேசும் வரை கேட்டு இருங்கள்.'
          : 'Give one short natural greeting, then listen until I speak.';
      wsRef.current?.send(JSON.stringify({ realtimeInput: { text: greeting } }));
      return;
    }

    if (message.toolCall) {
      void handleToolCall(message.toolCall);
    }

    const content = message.serverContent;
    if (!content) return;

    if (content.interrupted) {
      playerRef.current.clear();
      finalizeAssistant();
      setStatus('listening');
    }

    if (content.inputTranscription?.text) {
      const next = mergeTranscript(liveUserRef.current, content.inputTranscription.text);
      liveUserRef.current = next;
      setLiveUser(next);
      if (status !== 'tool') setStatus('listening');
    }

    if (content.outputTranscription?.text) {
      if (liveUserRef.current) finalizeUser();
      const next = mergeTranscript(liveAssistantRef.current, content.outputTranscription.text);
      liveAssistantRef.current = next;
      setLiveAssistant(next);
    }

    if (content.modelTurn?.parts) {
      for (const part of content.modelTurn.parts) {
        if (part.inlineData?.data) {
          if (liveUserRef.current) finalizeUser();
          setStatus('speaking');
          void playerRef.current.enqueue(part.inlineData.data);
        }
      }
    }

    if (content.turnComplete) {
      finalizeAssistant();
      setStatus('listening');
    }
  };

  const endSession = async (closePanel = false) => {
    closedByUserRef.current = true;
    setupCompleteRef.current = false;
    toolBusyRef.current = false;
    await stopCapture(false);
    await playerRef.current.close();
    if (wsRef.current) {
      try { wsRef.current.close(1000, 'User ended voice session'); } catch { /* ignore */ }
    }
    wsRef.current = null;
    finalizeUser();
    finalizeAssistant();
    setStatus('idle');
    mutedRef.current = false;
    setMuted(false);
    setSessionStartedAt(null);
    if (closePanel) setOpen(false);
  };

  const startSession = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('This browser does not provide microphone access. Use a current Chrome, Edge, Safari, or supported mobile browser.');
      setStatus('error');
      return;
    }

    setOpen(true);
    setError('');
    setStatus('connecting');
    closedByUserRef.current = false;
    setupCompleteRef.current = false;

    try {
      const session = await platformApi.voiceSessionToken({ language, project_id: project?.id || '' }) as VoiceTokenResponse;
      setVoiceName(session.voice || 'Gacrux');
      const socket = new WebSocket(`${LIVE_URL}?access_token=${encodeURIComponent(session.token)}`);
      wsRef.current = socket;

      socket.onopen = () => {
        const setup = {
          setup: {
            model: `models/${session.model}`,
            responseModalities: ['AUDIO'],
            systemInstruction: { parts: [{ text: session.system_instruction }] },
            speechConfig: {
              voiceConfig: {
                prebuiltVoiceConfig: { voiceName: session.voice || 'Gacrux' },
              },
            },
            inputAudioTranscription: {},
            outputAudioTranscription: {},
            realtimeInputConfig: {
              automaticActivityDetection: {
                disabled: false,
                startOfSpeechSensitivity: 'START_SENSITIVITY_LOW',
                endOfSpeechSensitivity: 'END_SENSITIVITY_LOW',
                prefixPaddingMs: 300,
                silenceDurationMs: 1000,
              },
              activityHandling: 'START_OF_ACTIVITY_INTERRUPTS',
            },
            tools: [{
              functionDeclarations: [{
                name: 'consult_mihimura',
                description: 'Use this for every agriculture, farm, crop, weather, irrigation, fertilizer, pesticide, disease, task, field operation, safety, or recommendation question. It runs MihiMura\'s authenticated multi-agent decision pipeline and returns grounded evidence.',
                parameters: {
                  type: 'OBJECT',
                  properties: {
                    question: {
                      type: 'STRING',
                      description: 'The farmer\'s complete question, preserving crop, timing, quantities and conditions they mentioned.',
                    },
                  },
                  required: ['question'],
                },
              }],
            }],
          },
        };
        socket.send(JSON.stringify(setup));
      };

      socket.onmessage = event => { void handleMessage(event); };
      socket.onerror = () => {
        setError('The realtime voice connection failed. Check the backend Gemini configuration and network connection.');
        setStatus('error');
      };
      socket.onclose = event => {
        setupCompleteRef.current = false;
        void stopCapture(false);
        playerRef.current.clear();
        if (!closedByUserRef.current) {
          setError(event.reason || 'The live voice session ended. Start a new session to continue.');
          setStatus('error');
        }
      };
    } catch (exc) {
      const message = exc instanceof Error ? exc.message : 'Could not start voice mode';
      setError(message);
      setStatus('error');
    }
  };

  const toggleMute = async () => {
    const next = !muted;
    mutedRef.current = next;
    setMuted(next);
    if (next) {
      await stopCapture(true);
    } else {
      try {
        await startCapture();
        setStatus('listening');
      } catch (exc) {
        setError(exc instanceof Error ? exc.message : 'Could not reopen microphone');
        setStatus('error');
      }
    }
  };

  useEffect(() => () => { void endSession(false); }, []);

  // A live session is language-bound through its system instruction. End it if
  // the global app language changes so the next session starts cleanly.
  const previousLanguage = useRef(language);
  useEffect(() => {
    if (previousLanguage.current !== language) {
      previousLanguage.current = language;
      if (wsRef.current) {
        void endSession(false);
        setError('Language changed. Start voice mode again to continue in the new language.');
      }
    }
  }, [language]);

  const timer = `${String(Math.floor(elapsed / 60)).padStart(2, '0')}:${String(elapsed % 60).padStart(2, '0')}`;
  const active = status !== 'idle' && status !== 'error';

  return <>
    <button type="button" className="voice-launch" onClick={() => active ? setOpen(true) : void startSession()}>
      <span><Mic /></span>
      <div><b>Voice conversation</b><small>Hands-free · native audio · {language}</small></div>
    </button>

    {open && <div className="voice-modal-backdrop" role="presentation">
      <section className="voice-modal" role="dialog" aria-modal="true" aria-label="MihiMura realtime voice agent">
        <header className="voice-modal-head">
          <div className="voice-brand"><span><Bot /></span><div><b>MihiMura Voice</b><small>Realtime agricultural companion</small></div></div>
          <div className="voice-head-actions">
            <span className={`voice-live-pill ${active ? 'online' : ''}`}><i />{active ? 'Live' : 'Offline'}</span>
            <button type="button" onClick={() => void endSession(true)} aria-label="End and close voice session"><X /></button>
          </div>
        </header>

        <div className="voice-session-body">
          <div className="voice-orb-zone">
            <div className={`voice-orb ${status}`}><span className="voice-orb-ring one"/><span className="voice-orb-ring two"/><div>{status === 'speaking' ? <Volume2 /> : status === 'tool' || status === 'thinking' ? <Sparkles /> : muted ? <MicOff /> : <Mic />}</div></div>
            <h2>{statusCopy(status, muted)}</h2>
            <p>{contextLabel}</p>
            <div className="voice-session-meta"><span><Radio /> {voiceName}</span><span><Headphones /> {language}</span><span>{timer}</span></div>
          </div>

          {error && <div className="voice-error"><WifiOff/><div><b>Voice session issue</b><p>{error}</p></div></div>}

          <div className="voice-tool-strip">
            <span className={status === 'tool' ? 'active' : ''}><ShieldCheck/> Multi-agent grounding</span>
            <span><Wifi/> Live audio</span>
            <span><CircleStop/> Barge-in enabled</span>
          </div>

          <div className="voice-transcript" aria-live="polite">
            {transcript.length === 0 && !liveUser && !liveAssistant && <div className="voice-transcript-empty"><Mic/><b>Start speaking naturally</b><p>You do not need to press Send. MihiMura detects the end of your turn and answers by voice.</p></div>}
            {transcript.map(item => <div key={item.id} className={`voice-line ${item.role}`}><span>{item.role === 'assistant' ? 'MihiMura' : item.role === 'user' ? 'You' : 'System'}</span><p>{item.text}</p></div>)}
            {liveUser && <div className="voice-line user live"><span>You · listening</span><p>{liveUser}</p></div>}
            {liveAssistant && <div className="voice-line assistant live"><span>MihiMura · speaking</span><p>{liveAssistant}</p></div>}
          </div>
        </div>

        <footer className="voice-controls">
          {!active ? <Button onClick={() => void startSession()}><PhoneCall/> Start voice conversation</Button> : <>
            <button type="button" className={`voice-control ${muted ? 'danger' : ''}`} onClick={() => void toggleMute()}>{muted ? <MicOff/> : <Mic/>}<span>{muted ? 'Unmute' : 'Mute'}</span></button>
            <button type="button" className="voice-end" onClick={() => void endSession(true)}><PhoneOff/><span>End</span></button>
          </>}
        </footer>
      </section>
    </div>}
  </>;
}
