import { useEffect, useMemo, useRef, useState } from 'react';
import { Bot, CircleStop, Headphones, Mic, MicIcon, MicOff, PhoneCall, PhoneOff, Radio, ShieldCheck, Sparkles, Volume2, Wifi, WifiOff, X } from 'lucide-react';
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

function recognitionLanguage(language: VoiceLanguage) {
  if (language === 'Sinhala') return 'si-LK';
  // The working reference project uses ta-IN for Chrome speech recognition.
  if (language === 'Tamil') return 'ta-IN';
  return 'en-US';
}

function greetingFor(language: VoiceLanguage) {
  if (language === 'Sinhala') return 'ආයුබෝවන්! මම මිහිමුර. ඔබේ ගොවිපල ගැන මොනවද දැනගන්න ඕනේ?';
  if (language === 'Tamil') return 'வணக்கம்! நான் மிஹிமுர. உங்கள் பண்ணையைப் பற்றி என்ன தெரிந்துகொள்ள விரும்புகிறீர்கள்?';
  return 'Hello! I am MihiMura. What would you like to know about your farm?';
}

function errorSpeechFor(language: VoiceLanguage) {
  if (language === 'Sinhala') return 'සමාවන්න, පිළිතුර ලබාගැනීමේදී ගැටලුවක් ඇති වුණා. කරුණාකර නැවත උත්සාහ කරන්න.';
  if (language === 'Tamil') return 'மன்னிக்கவும், பதிலைப் பெறுவதில் சிக்கல் ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.';
  return 'Sorry, I had trouble getting that answer. Please try again.';
}

function statusCopy(status: VoiceStatus, muted: boolean) {
  if (muted) return 'Microphone muted';
  if (status === 'connecting') return 'Starting voice conversation…';
  if (status === 'thinking') return 'Understanding your question…';
  if (status === 'tool') return 'Checking farm, weather and safety evidence…';
  if (status === 'speaking') return 'MihiMura is speaking';
  if (status === 'error') return 'Voice connection needs attention';
  if (status === 'listening') return 'Listening — speak naturally';
  return 'Ready';
}

export function VoiceAgent({ language, project, profile, onDecision }: VoiceAgentProps) {
  const [open, setOpen] = useState(false);
  const [sessionActive, setSessionActive] = useState(false);
  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState('');
  const [voiceName] = useState('Gacrux');
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [liveUser, setLiveUser] = useState('');
  const [liveAssistant, setLiveAssistant] = useState('');
  const [sessionStartedAt, setSessionStartedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const recognitionRef = useRef<any>(null);
  const silenceTimeoutRef = useRef<number | null>(null);
  const sessionActiveRef = useRef(false);
  const mutedRef = useRef(false);
  const processingRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);
  const liveUserRef = useRef('');
  const liveAssistantRef = useRef('');
  const processQuestionRef = useRef<(question: string) => void>(() => undefined);

  const contextLabel = useMemo(() => project
    ? `${project.farm_name || 'Farm'} · ${project.crop || 'Crop'} · ${project.stage || 'Current stage'}`
    : `${profile?.district || 'Sri Lanka'} · General context`, [project, profile]);

  useEffect(() => {
    if (!sessionStartedAt) return;
    const id = window.setInterval(() => setElapsed(Math.floor((Date.now() - sessionStartedAt) / 1000)), 1000);
    return () => window.clearInterval(id);
  }, [sessionStartedAt]);

  useEffect(() => { liveUserRef.current = liveUser; }, [liveUser]);
  useEffect(() => { liveAssistantRef.current = liveAssistant; }, [liveAssistant]);

  const clearSilenceTimer = () => {
    if (silenceTimeoutRef.current !== null) {
      window.clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }
  };

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

  const finalizeAssistant = (fallback = '') => {
    const text = (liveAssistantRef.current || fallback).trim();
    if (text) pushTranscript('assistant', text);
    setLiveAssistant('');
    liveAssistantRef.current = '';
    return text;
  };

  const stopRecognition = (abort = true) => {
    clearSilenceTimer();
    const recognition = recognitionRef.current;
    recognitionRef.current = null;
    if (!recognition) return;
    try {
      if (abort) recognition.abort();
      else recognition.stop();
    } catch {
      // Recognition may already have ended.
    }
  };

  const stopPlayback = () => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    if (audioRef.current) {
      try { audioRef.current.pause(); } catch { /* ignore */ }
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  };

  const playBlob = (blob: Blob) => new Promise<void>((resolve, reject) => {
    stopPlayback();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audioUrlRef.current = url;
    audioRef.current = audio;

    const cleanup = () => {
      if (audioRef.current === audio) audioRef.current = null;
      if (audioUrlRef.current === url) {
        URL.revokeObjectURL(url);
        audioUrlRef.current = null;
      }
    };

    audio.onended = () => { cleanup(); resolve(); };
    audio.onerror = () => { cleanup(); reject(new Error('Audio playback failed')); };
    audio.play().catch(err => { cleanup(); reject(err); });
  });

  const speakWithBrowserFallback = (text: string) => new Promise<void>((resolve) => {
    if (!('speechSynthesis' in window)) {
      resolve();
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language === 'Sinhala' ? 'si-LK' : language === 'Tamil' ? 'ta-LK' : 'en-LK';
    utterance.rate = 1;
    utterance.onend = () => resolve();
    utterance.onerror = () => resolve();
    window.speechSynthesis.speak(utterance);
  });

  const speakText = async (text: string) => {
    if (!text.trim()) return;
    console.log('[VOICE] Requesting Gemini TTS');
    try {
      const blob = await platformApi.voiceTts(text, language);
      console.log('[VOICE] Gemini TTS audio received', { bytes: blob.size, type: blob.type });
      await playBlob(blob);
      console.log('[VOICE] Gemini TTS playback completed');
    } catch (exc) {
      console.warn('[VOICE] Gemini TTS failed; using browser speech fallback', exc);
      await speakWithBrowserFallback(text);
    }
  };

  const startListening = () => {
    if (!sessionActiveRef.current || mutedRef.current || processingRef.current || recognitionRef.current) return;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError('Realtime speech recognition is not supported in this browser. Please use Chrome or Edge.');
      setStatus('error');
      setSessionActive(false);
      sessionActiveRef.current = false;
      return;
    }

    stopPlayback();
    clearSilenceTimer();
    setError('');
    setLiveUser('');
    liveUserRef.current = '';

    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = recognitionLanguage(language);
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    let finalTranscript = '';

    recognition.onstart = () => {
      console.log('[VOICE] SpeechRecognition started', recognition.lang);
      setStatus('listening');
      clearSilenceTimer();
      silenceTimeoutRef.current = window.setTimeout(() => {
        if (recognitionRef.current === recognition && !finalTranscript.trim()) {
          console.log('[VOICE] Initial silence timeout');
          try { recognition.stop(); } catch { /* ignore */ }
        }
      }, 7000);
    };

    recognition.onresult = (event: any) => {
      clearSilenceTimer();
      let finalText = '';
      let interimText = '';

      for (let i = 0; i < event.results.length; i += 1) {
        const text = String(event.results[i][0]?.transcript || '');
        if (event.results[i].isFinal) finalText += text;
        else interimText += text;
      }

      const currentText = `${finalText} ${interimText}`.replace(/\s+/g, ' ').trim();
      finalTranscript = currentText;
      liveUserRef.current = currentText;
      setLiveUser(currentText);

      if (currentText) {
        console.log('[VOICE] Heard:', currentText);
        silenceTimeoutRef.current = window.setTimeout(() => {
          if (recognitionRef.current === recognition) {
            console.log('[VOICE] End-of-speech silence detected; submitting');
            try { recognition.stop(); } catch { /* ignore */ }
          }
        }, 1800);
      }
    };

    recognition.onend = () => {
      clearSilenceTimer();
      if (recognitionRef.current === recognition) recognitionRef.current = null;
      const question = finalTranscript.trim();
      console.log('[VOICE] SpeechRecognition ended', { hasQuestion: Boolean(question), question });

      if (!sessionActiveRef.current || mutedRef.current) return;

      if (question) {
        processQuestionRef.current(question);
      } else {
        window.setTimeout(() => startListening(), 450);
      }
    };

    recognition.onerror = (event: any) => {
      clearSilenceTimer();
      if (recognitionRef.current === recognition) recognitionRef.current = null;
      console.error('[VOICE] SpeechRecognition error:', event.error);

      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setError('Microphone access was denied. Allow microphone permission in your browser and start Voice Mode again.');
        setStatus('error');
        setSessionActive(false);
        sessionActiveRef.current = false;
        return;
      }

      if (event.error === 'network') {
        setError('Browser speech recognition reported a network error. Check the connection and try again.');
      } else if (event.error !== 'no-speech' && event.error !== 'aborted') {
        setError(`Voice recognition error: ${event.error || 'unknown error'}`);
      }

      if (sessionActiveRef.current && !mutedRef.current) {
        window.setTimeout(() => startListening(), 650);
      }
    };

    try {
      recognition.start();
    } catch (exc) {
      recognitionRef.current = null;
      console.error('[VOICE] Could not start SpeechRecognition', exc);
      setError('Could not start browser speech recognition. Try Chrome or Edge and check microphone permission.');
      setStatus('error');
    }
  };

  const processQuestion = async (question: string) => {
    if (!sessionActiveRef.current || processingRef.current) return;
    processingRef.current = true;
    stopRecognition(true);
    finalizeUser(question);
    setError('');
    setStatus('tool');
    console.log('[VOICE] Sending question to existing MihiMura /ask-ai:', question);

    try {
      const result = await platformApi.ask(question, projectContext(project, profile, language));
      console.log('[VOICE] MihiMura /ask-ai completed', { provider: result?.provider, confidence: result?.confidence });
      onDecision?.(result, question);

      const answer = String(result?.summary || result?.recommended_action || 'MihiMura completed the analysis.').trim();
      liveAssistantRef.current = answer;
      setLiveAssistant(answer);
      setStatus('speaking');
      await speakText(answer);
      finalizeAssistant(answer);
    } catch (exc) {
      console.error('[VOICE] MihiMura voice question failed', exc);
      const message = exc instanceof Error ? exc.message : 'Could not reach the AI service';
      setError(message);
      const spoken = errorSpeechFor(language);
      liveAssistantRef.current = spoken;
      setLiveAssistant(spoken);
      setStatus('speaking');
      await speakWithBrowserFallback(spoken);
      finalizeAssistant(spoken);
    } finally {
      processingRef.current = false;
      if (sessionActiveRef.current && !mutedRef.current) {
        setStatus('listening');
        window.setTimeout(() => startListening(), 400);
      }
    }
  };

  processQuestionRef.current = processQuestion;

  const startSession = async () => {
    if (sessionActiveRef.current) {
      setOpen(true);
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setOpen(true);
      setError('Voice recognition is not supported in this browser. Please use Chrome or Edge.');
      setStatus('error');
      return;
    }

    console.log('[VOICE] Starting reference-style voice mode (Browser STT → /ask-ai → Gemini TTS)');
    setOpen(true);
    setError('');
    setSessionActive(true);
    sessionActiveRef.current = true;
    setStatus('connecting');
    setSessionStartedAt(Date.now());
    setElapsed(0);
    mutedRef.current = false;
    setMuted(false);

    const greeting = greetingFor(language);
    liveAssistantRef.current = greeting;
    setLiveAssistant(greeting);
    setStatus('speaking');
    await speakText(greeting);
    finalizeAssistant(greeting);

    if (sessionActiveRef.current && !mutedRef.current) {
      setStatus('listening');
      startListening();
    }
  };

  const endSession = async (closePanel = false) => {
    console.log('[VOICE] Ending voice session');
    sessionActiveRef.current = false;
    setSessionActive(false);
    processingRef.current = false;
    stopRecognition(true);
    stopPlayback();
    finalizeUser();
    finalizeAssistant();
    mutedRef.current = false;
    setMuted(false);
    setStatus('idle');
    setSessionStartedAt(null);
    if (closePanel) setOpen(false);
  };

  const toggleMute = async () => {
    const next = !mutedRef.current;
    mutedRef.current = next;
    setMuted(next);

    if (next) {
      stopRecognition(true);
    } else if (sessionActiveRef.current && !processingRef.current) {
      setStatus('listening');
      startListening();
    }
  };

  useEffect(() => () => {
    sessionActiveRef.current = false;
    stopRecognition(true);
    stopPlayback();
  }, []);

  const previousLanguage = useRef(language);
  useEffect(() => {
    if (previousLanguage.current !== language) {
      previousLanguage.current = language;
      if (sessionActiveRef.current) {
        void endSession(false);
        setError('Language changed. Start voice mode again to continue in the selected language.');
      }
    }
  }, [language]);

  const timer = `${String(Math.floor(elapsed / 60)).padStart(2, '0')}:${String(elapsed % 60).padStart(2, '0')}`;
  const active = sessionActive && status !== 'error';

  return <>
    <button type="button" className="voice-launch" onClick={() => active ? setOpen(true) : void startSession()}>
      <span><Mic /></span>
      <div><b>Voice conversation</b><small>Hands-free · Gemini TTS · {language}</small></div>
    </button>

    {open && <div className="voice-modal-backdrop" role="presentation">
      <section className="voice-modal" role="dialog" aria-modal="true" aria-label="MihiMura voice agent">
        <header className="voice-modal-head">
          <div className="voice-brand"><span><Bot /></span><div><b>MihiMura Voice</b><small></small></div></div>
          <div className="voice-head-actions">
            <span className={`voice-live-pill ${active ? 'online' : ''}`}><i />{active ? 'Live' : 'Offline'}</span>
            <button type="button" onClick={() => void endSession(true)} aria-label="End and close voice session"><X /></button>
          </div>
        </header>

        <div className="voice-session-body">
          <div className="voice-orb-zone">
            <div className={`voice-orb ${status}`}><span className="voice-orb-ring one"/><span className="voice-orb-ring two"/><div>{status === 'speaking' ? <Volume2 /> : status === 'tool' || status === 'thinking' ? <MicIcon/> : muted ? <MicOff /> : <Mic />}</div></div>
            <h2>{statusCopy(status, muted)}</h2>
            <p>{contextLabel}</p>
            <div className="voice-session-meta"><span><Radio /> {voiceName}</span><span><Headphones /> {language}</span><span>{timer}</span></div>
          </div>

          {error && <div className="voice-error"><WifiOff/><div><b>Voice session issue</b><p>{error}</p></div></div>}

          <div className="voice-tool-strip">
            <span className={status === 'tool' ? 'active' : ''}><ShieldCheck/> Multi-agent grounding</span>
            <span><Wifi/> Browser speech input</span>
            <span><CircleStop/> Auto turn detection</span>
          </div>

          <div className="voice-transcript" aria-live="polite">
            {transcript.length === 0 && !liveUser && !liveAssistant && <div className="voice-transcript-empty"><Mic/><b>Start speaking naturally</b><p>MihiMura detects a short pause, submits the transcript to the existing AI agents, and speaks the grounded answer.</p></div>}
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
