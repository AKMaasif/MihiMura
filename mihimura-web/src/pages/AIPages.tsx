import { useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { AlertTriangle, ArrowRight, Bot, Camera, CheckCircle2, Download, EyeIcon, FileImage, FileText, Paperclip, Plus, Save, Send, ShieldCheck, Sparkles, Stethoscope, Volume2, VolumeX } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Empty, Notice, Status } from '../components/common/UI';
import { platformApi } from '../services/platformApi';
import { useAuth } from '../context/AuthContext';
import { useLanguage, type AppLanguage } from '../context/LanguageContext';
import { VoiceAgent } from '../components/ai/VoiceAgent';

function projectContext(p: any, profile: any, lang: string, languageMode: 'auto' | AppLanguage = 'auto') {
  return {
    province: p?.province || '',
    location: p?.district || profile?.district || 'Sri Lanka',
    project_id: p?.id || '',
    farm_id: p?.farm_id || '',
    lat: p?.lat || profile?.lat || null,
    lon: p?.lon || profile?.lon || null,
    crop: p?.crop || '',
    stage: p?.stage || '',
    language: lang,
    language_mode: languageMode === 'auto' ? 'auto' : 'manual',
  };
}

function messageText(m: any) {
  return String(m?.content ?? m?.text ?? '');
}

function decisionFromMessage(message: any) {
  const metadata = message?.metadata || {};
  return metadata.decision || null;
}

type AgentMode = 'auto' | 'simple_chat' | 'decision_support' | 'full_report';

const AGENT_MODES: Array<{ id: AgentMode; label: string; description: string }> = [
  { id: 'auto', label: 'Auto', description: 'MihiMura detects the best workflow from each message.' },
  { id: 'simple_chat', label: 'Simple chat', description: 'Natural explanations and general farming conversation without unnecessary live tools.' },
  { id: 'decision_support', label: 'Decision support', description: 'Farm-grounded, current-data and safety-aware operational decisions.' },
  { id: 'full_report', label: 'Full report', description: 'Complete cultivation, equipment, inputs, costs, profit, harvest and marketing planning.' },
];

function modeLabel(mode?: string) {
  return AGENT_MODES.find(x => x.id === mode)?.label || 'Auto';
}

function isAgentMode(value: any): value is AgentMode {
  return AGENT_MODES.some(x => x.id === value);
}

function thinkingCopy(mode: AgentMode) {
  if (mode === 'simple_chat') return 'Reading the conversation and preparing a clear answer…';
  if (mode === 'decision_support') return 'Checking farm context, current evidence and safety constraints…';
  if (mode === 'full_report') return 'Planning agronomy, resources, economics, risks and marketing sections…';
  return 'Understanding your intent and choosing the right MihiMura workflow…';
}

type ChatLanguageMode = 'auto' | AppLanguage;

function detectMessageLanguage(text: string, fallback: AppLanguage): AppLanguage {
  const sinhala = Array.from(text || '').filter(ch => ch >= '\u0D80' && ch <= '\u0DFF').length;
  const tamil = Array.from(text || '').filter(ch => ch >= '\u0B80' && ch <= '\u0BFF').length;
  const latin = (text.match(/[A-Za-z]/g) || []).length;
  if (sinhala >= 2 && sinhala >= tamil) return 'Sinhala';
  if (tamil >= 2 && tamil > sinhala) return 'Tamil';
  if (latin > 0) return 'English';
  return fallback;
}

export function AIPage() {
  const nav = useNavigate();
  const { profile } = useAuth();
  const { language, setLanguage, setDetectedLanguage } = useLanguage();

  const [q, setQ] = useState('');
  const [messages, setMessages] = useState<any[]>([]);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [projectId, setProjectId] = useState('');
  const [notice, setNotice] = useState('');
  const [conversations, setConversations] = useState<any[]>([]);
  const [conversationId, setConversationId] = useState('');
  const [conversationLoading, setConversationLoading] = useState(true);
  const [clarificationAnswers, setClarificationAnswers] = useState<Record<string, any>>({});
  const [reportLoading, setReportLoading] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [mode, setMode] = useState<AgentMode>('auto');
  const [chatLanguageMode, setChatLanguageMode] = useState<ChatLanguageMode>('auto');

  const project = useMemo(() => projects.find(x => x.id === projectId) || null, [projects, projectId]);
  const latestAssistant = useMemo(() => [...messages].reverse().find(m => m.role === 'assistant'), [messages]);
  const activeMemory = result?.conversation_memory || null;

  const refreshConversations = async () => {
    const list = await platformApi.conversations();
    setConversations(list.filter((x: any) => x.status !== 'archived'));
    return list;
  };

  const loadConversation = async (id: string) => {
    if (!id) {
      setConversationId('');
      setMessages([]);
      setResult(null);
      setReport(null);
      setClarificationAnswers({});
      return;
    }
    setConversationLoading(true);
    setNotice('');
    try {
      const [items, memory, storedReports] = await Promise.all([
        platformApi.conversationMessages(id),
        platformApi.conversationMemory(id),
        platformApi.reports(),
      ]);
      setConversationId(id);
      setMessages(items);
      setClarificationAnswers({});
      const memoryLanguage = memory?.known_facts?.language;
      if (chatLanguageMode === 'auto' && ['English', 'Sinhala', 'Tamil'].includes(String(memoryLanguage || ''))) {
        setDetectedLanguage(memoryLanguage as AppLanguage);
      }
      const lastAssistant = [...items].reverse().find((m: any) => m.role === 'assistant');
      const restored = decisionFromMessage(lastAssistant);
      const restoredMode = restored?.requested_mode || lastAssistant?.metadata?.requested_mode;
      if (isAgentMode(restoredMode)) setMode(restoredMode);
      if (restored) setResult({ ...restored, conversation_id: id, conversation_memory: memory });
      else if (lastAssistant?.metadata?.response_type) {
        setResult({
          response_type: lastAssistant.metadata.response_type,
          summary: lastAssistant.content,
          recommended_action: lastAssistant.content,
          clarification_fields: lastAssistant.metadata.clarification_fields || [],
          suggested_actions: lastAssistant.metadata.suggested_actions || [],
          report_ready: Boolean(lastAssistant.metadata.report_ready),
          risk_level: lastAssistant.metadata.risk_level || 'watch',
          confidence: lastAssistant.metadata.confidence || 0,
          conversation_id: id,
          conversation_memory: memory,
        });
      } else setResult(null);
      const freshReport = (storedReports || []).find((r: any) => r.conversation_id === id);
      const reportMessage = [...items].reverse().find((m: any) => m?.metadata?.report);
      setReport(freshReport || reportMessage?.metadata?.report || null);
    } catch (e: any) {
      setNotice(e.message);
    } finally {
      setConversationLoading(false);
    }
  };

  useEffect(() => {
    let alive = true;
    setConversationLoading(true);
    Promise.allSettled([platformApi.projects(), platformApi.conversations()]).then(async r => {
      if (!alive) return;
      if (r[0].status === 'fulfilled') {
        const projectList = r[0].value as any[];
        setProjects(projectList);
      }
      if (r[1].status === 'fulfilled') {
        const list = (r[1].value as any[]).filter(x => x.status !== 'archived');
        setConversations(list);
        if (list[0]) {
          await loadConversation(list[0].id);
          if (list[0].project_id) setProjectId(list[0].project_id);
        } else {
          setConversationLoading(false);
        }
      } else setConversationLoading(false);
    });
    return () => { alive = false; };
  }, []);

  const reloadMessages = async (id: string) => {
    const items = await platformApi.conversationMessages(id);
    setMessages(items);
    return items;
  };

  const askQuestion = async (
    question: string,
    answers: Record<string, any> = {},
    modeOverride: AgentMode = mode,
    allowModeMismatch = false,
    resumeRoute = false,
  ) => {
    const trimmed = question.trim();
    if ((!trimmed && !Object.keys(answers).length) || loading) return;
    setLoading(true);
    setNotice('');

    if (trimmed && !resumeRoute) {
      setMessages(current => [...current, { id: `optimistic-${Date.now()}`, role: 'user', content: trimmed, created_at: new Date().toISOString() }]);
      setQ('');
    }

    try {
      const detectedLanguage = chatLanguageMode === 'auto' ? detectMessageLanguage(trimmed, language) : chatLanguageMode;
      if (chatLanguageMode === 'auto' && detectedLanguage !== language) setDetectedLanguage(detectedLanguage);
      const r = await platformApi.ask(
        trimmed,
        projectContext(project, profile, detectedLanguage, chatLanguageMode),
        conversationId || undefined,
        answers,
        modeOverride,
        allowModeMismatch,
        resumeRoute,
      );
      const nextId = r.conversation_id as string;
      setConversationId(nextId);
      setResult(r);
      if (chatLanguageMode === 'auto' && ['English', 'Sinhala', 'Tamil'].includes(String(r?.response_language || ''))) {
        setDetectedLanguage(r.response_language as AppLanguage);
      }
      if (r?.report) setReport(r.report);
      setClarificationAnswers({});
      await reloadMessages(nextId);
      await refreshConversations();
    } catch (e: any) {
      setNotice(e.message);
      setMessages(current => [...current.filter(m => !String(m.id || '').startsWith('optimistic-')), { id: `error-${Date.now()}`, role: 'assistant', content: language === 'Sinhala' ? `එම ඉල්ලීම සම්පූර්ණ කළ නොහැකි විය: ${e.message}` : language === 'Tamil' ? `அந்த கோரிக்கையை முடிக்க முடியவில்லை: ${e.message}` : `I could not complete that request: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const submitClarification = async () => {
    const fields = result?.clarification_fields || [];
    const missingRequired = fields.filter((f: any) => f.required && clarificationAnswers[f.key] === undefined && !activeMemory?.known_facts?.[f.key]);
    if (missingRequired.length) {
      setNotice(`Please complete: ${missingRequired.map((x: any) => x.label).join(', ')}`);
      return;
    }
    await askQuestion('', clarificationAnswers);
  };

  const newChat = () => {
    setConversationId('');
    setMessages([]);
    setResult(null);
    setReport(null);
    setClarificationAnswers({});
    setNotice('');
    setQ('');
    setMode('auto');
  };

  const archiveCurrent = async (id: string, event: MouseEvent) => {
    event.stopPropagation();
    try {
      await platformApi.archiveConversation(id);
      const list = (await refreshConversations()).filter((x: any) => x.status !== 'archived');
      if (conversationId === id) {
        if (list[0]) await loadConversation(list[0].id);
        else newChat();
      }
    } catch (e: any) { setNotice(e.message); }
  };

  const generateReport = async () => {
    if (!conversationId || reportLoading) return;
    setReportLoading(true);
    setNotice('');
    try {
      const generated = await platformApi.generateConversationReport(conversationId);
      setReport(generated);
      setNotice('Cultivation report generated and stored in your private Supabase report bucket.');
      await reloadMessages(conversationId);
      await refreshConversations();
    } catch (e: any) { setNotice(e.message); }
    finally { setReportLoading(false); }
  };

  const speak = () => {
    if (!result?.summary || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(result.summary);
    u.lang = language === 'Sinhala' ? 'si-LK' : language === 'Tamil' ? 'ta-LK' : 'en-LK';
    window.speechSynthesis.speak(u);
  };
  const stopAudio = () => { if ('speechSynthesis' in window) window.speechSynthesis.cancel(); };
  const saveAnswer = () => {
    if (!result) return;
    const key = 'mihimura_saved_ai_answers';
    const items = JSON.parse(localStorage.getItem(key) || '[]');
    items.unshift({ saved_at: new Date().toISOString(), conversation_id: conversationId || null, project_id: project?.id || null, language, result });
    localStorage.setItem(key, JSON.stringify(items.slice(0, 50)));
    setNotice('Answer saved locally for quick reference. The conversation itself is already persisted in Supabase.');
  };
  const createTask = async () => {
    if (!result || !project) { setNotice('Create or select a cultivation project before converting this recommendation into a task.'); return; }
    await platformApi.addTask({ project_id: project.id, title: result.recommended_action, task_type: 'AI recommendation', due_at: new Date(Date.now() + 24 * 3600e3).toISOString(), priority: ['action', 'emergency'].includes(result.risk_level) ? 'high' : 'medium', weather_dependency: 'Re-check current weather before execution', instructions: result.why, schedule_reason: 'Created after explicit farmer confirmation from MihiMura recommendation' });
    setNotice('Task created. The confirmation and recommendation remain visible in the audit trail.');
    nav('/app/tasks');
  };

  const renderModeSwitch = () => {
    if (result?.response_type !== 'mode_switch' || !result?.suggested_mode || !isAgentMode(result.suggested_mode)) return null;
    const suggested = result.suggested_mode as AgentMode;
    const originalQuestion = String(result.original_question || '').trim();
    return <div className="ai-mode-switch-card">
      <div className="ai-mode-switch-icon"></div>
      <div className="ai-mode-switch-copy">
        <small>{language === 'Sinhala' ? 'වඩා සුදුසු workflow එකක් හඳුනාගත්තා' : language === 'Tamil' ? 'சிறந்த workflow கண்டறியப்பட்டது' : 'Better workflow detected'}</small>
        <h3>{language === 'Sinhala' ? `${modeLabel(suggested)} වෙත මාරු වෙන්නද?` : language === 'Tamil' ? `${modeLabel(suggested)} முறைக்கு மாறவா?` : `Switch to ${modeLabel(suggested)}?`}</h3>
        <p>{result.why || result.mode_reason}</p>
        <span>{language === 'Sinhala' ? 'ඔබගේ සංවාදය සහ farm context එලෙසම පවතී; වෙනස් වන්නේ workflow/tool permissions පමණයි.' : language === 'Tamil' ? 'உங்கள் உரையாடலும் farm context-உம் அதேபடி இருக்கும்; workflow/tool permissions மட்டும் மாறும்.' : 'Your conversation and farm context stay the same; only the workflow/tool permissions change.'}</span>
      </div>
      <div className="ai-mode-switch-actions">
        <Button disabled={loading || !originalQuestion} onClick={() => { setMode(suggested); void askQuestion(originalQuestion, {}, suggested, false, true); }}>{language === 'Sinhala' ? 'මාරු වී ඉදිරියට' : language === 'Tamil' ? 'மாற்றி தொடரவும்' : 'Switch & continue'} <ArrowRight/></Button>
        <Button variant="secondary" disabled={loading || !originalQuestion} onClick={() => void askQuestion(originalQuestion, {}, mode, true, true)}>{language === 'Sinhala' ? `${modeLabel(mode)} තුළ සිටින්න` : language === 'Tamil' ? `${modeLabel(mode)} முறையில் தொடரவும்` : `Stay in ${modeLabel(mode)}`}</Button>
      </div>
    </div>;
  };

  const renderClarification = () => {
    const fields = result?.clarification_fields || [];
    if (result?.response_type !== 'clarification' || !fields.length) return null;
    return <div className="ai-clarification-card">
      <div className="ai-clarification-head"><span><b>{language === 'Sinhala' ? 'අත්‍යවශ්‍ය වාර්තා තොරතුරු පමණයි' : language === 'Tamil' ? 'கட்டாய அறிக்கை விவரங்கள் மட்டும்' : 'Only the required report details'}</b><small>{language === 'Sinhala' ? 'කන්නය, වාරි මූලාශ්‍රය, ප්‍රභේදය සහ වගා දිනය වාර්තාව නවත්වන්නේ නැහැ; ඒවා පැහැදිලි උපකල්පන ලෙස තැබිය හැක.' : language === 'Tamil' ? 'பருவம், பாசனம், வகை மற்றும் நடவு தேதி அறிக்கையைத் தடுக்காது; அவற்றை தெளிவான கருதுகோள்களாக வைத்துக்கொள்ளலாம்.' : 'Optional season, irrigation, variety and planting date will not block the report; they can remain visible assumptions.'}</small></span></div>
      <div className="ai-clarification-grid">{fields.map((field: any) => <label key={field.key}>{field.label}{field.required && <em>required</em>}
        {field.type === 'select' ? <select value={clarificationAnswers[field.key] ?? ''} onChange={e => setClarificationAnswers(x => ({ ...x, [field.key]: e.target.value }))}><option value="">{language === 'Sinhala' ? 'තෝරන්න…' : language === 'Tamil' ? 'தேர்வு செய்யவும்…' : 'Choose…'}</option>{(field.options || []).map((option: any) => { const value = typeof option === 'string' ? option : option.value; const label = typeof option === 'string' ? option : (option.label || option.value); return <option key={value} value={value}>{label}</option>; })}</select>
          : <input type={field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'} step={field.type === 'number' ? '0.01' : undefined} placeholder={field.placeholder || ''} value={clarificationAnswers[field.key] ?? ''} onChange={e => setClarificationAnswers(x => ({ ...x, [field.key]: field.type === 'number' ? (e.target.value === '' ? '' : Number(e.target.value)) : e.target.value }))}/>}</label>)}</div>
      <div className="ai-clarification-actions"><Button disabled={loading} onClick={() => void submitClarification()}>{loading ? (language === 'Sinhala' ? 'පසුබිම යාවත්කාලීන කරමින්…' : language === 'Tamil' ? 'சூழலை புதுப்பிக்கிறது…' : 'Updating context…') : (language === 'Sinhala' ? 'මෙම තොරතුරු සමඟ ඉදිරියට යන්න' : language === 'Tamil' ? 'இந்த விவரங்களுடன் தொடரவும்' : 'Continue with these details')} <ArrowRight/></Button></div>
    </div>;
  };

  const currentReport = report || result?.report || latestAssistant?.metadata?.report;
  const effectiveMode: AgentMode = isAgentMode(result?.effective_mode) ? result.effective_mode : mode;
  const modeDescription = AGENT_MODES.find(x => x.id === mode)?.description || AGENT_MODES[0].description;

  return <div className="ai-shell">
    <aside className="ai-history-panel">
      <div className="ai-history-head"><div><Bot/><span><b>Conversations</b><small>Persistent farm memory</small></span></div><button onClick={newChat} title="New conversation"><Plus/></button></div>
      <button className="ai-new-chat" onClick={newChat}><Plus/> New farm conversation</button>
      <div className="ai-history-list">{conversations.length ? conversations.map(c => <button className={conversationId === c.id ? 'active' : ''} key={c.id} onClick={() => { void loadConversation(c.id); if (c.project_id) setProjectId(c.project_id); }}><span><b>{c.title || 'Farm conversation'}</b><small>{new Date(c.updated_at || c.created_at).toLocaleString()}</small></span><i onClick={e => void archiveCurrent(c.id, e)} title="Archive">×</i></button>) : <div className="ai-history-empty"><span>No saved conversations yet.</span><small>Your first message will create one.</small></div>}</div>
      <div className="ai-memory-note"><ShieldCheck/><span><b>Context precedence</b><small>Current message → conversation → selected project → profile default.</small></span></div>
    </aside>

    <div className="ai-main-column">
      <div className="ai-mode-bar" role="tablist" aria-label="MihiMura AI mode">
        <div className="ai-mode-options">{AGENT_MODES.map(option => <button type="button" role="tab" aria-selected={mode === option.id} className={mode === option.id ? 'active' : ''} key={option.id} onClick={() => setMode(option.id)}>{option.id === 'auto' ? <EyeIcon/> : option.id === 'simple_chat' ? <Bot/> : option.id === 'decision_support' ? <ShieldCheck/> : <FileText/>}<span><b>{option.label}</b></span></button>)}</div>
        <div className="ai-mode-description"><span><b>{modeLabel(mode)}</b>{modeDescription}</span>{result?.detected_mode && <i>Detected: {modeLabel(result.detected_mode)}</i>}</div>
      </div>

    <div className="ai-workbench"><Card className="ai-chat-card" title="MihiMura AI" subtitle={`${modeLabel(effectiveMode)} · persistent farm conversation`} action={<select className="compact-select" value={chatLanguageMode} onChange={e => { const next = e.target.value as ChatLanguageMode; setChatLanguageMode(next); if (next !== 'auto') void setLanguage(next); }}><option value="auto">Auto detect · {language}</option><option value="English">English</option><option value="Sinhala">සිංහල</option><option value="Tamil">தமிழ்</option></select>}>
      <div className="ai-context-selector"><div className="ai-context-strip"><span> Active context</span><b>{activeMemory?.known_facts?.location ? `${activeMemory.known_facts.location} · conversation scenario` : project ? `${project.farm_name} · ${project.crop} · ${project.stage}` : `${profile?.district || 'Sri Lanka'} · General location context`}</b><small>{activeMemory?.summary || (project ? 'Farm memory + weather + climate baseline + safety policy' : 'No project selected. Explicit conversation facts override profile defaults.')}</small></div><label>Project context<select value={projectId} onChange={e => setProjectId(e.target.value)}><option value="">General / no project</option>{projects.map(p => <option value={p.id} key={p.id}>{p.farm_name} · {p.crop} · {p.stage}</option>)}</select></label></div>

      <VoiceAgent language={language} project={project} profile={profile} conversationId={conversationId || undefined} mode={mode} onDecision={(voiceResult) => { const nextId = voiceResult?.conversation_id || conversationId; if (nextId) setConversationId(nextId); setResult(voiceResult); if (voiceResult?.report) setReport(voiceResult.report); if (nextId) { void reloadMessages(nextId); void refreshConversations(); } }} />
      {notice && <Notice tone="info" title="MihiMura">{notice}</Notice>}

      <div className={`ai-message-list ${!conversationLoading && !messages.length && !loading ? 'is-empty' : ''}`}>{conversationLoading ? <div className="ai-thinking"><i/><i/><i/><span>Loading conversation memory…</span></div> : messages.length ? messages.map((m, i) => <div className={`ai-msg ${m.role}`} key={m.id || i}>{m.role === 'assistant' && <Bot/>}<div><span className="ai-message-text">{messageText(m)}</span>{m?.metadata?.report?.download_url && <a className="ai-inline-report" href={currentReport?.id === m.metadata.report.id ? (currentReport.download_url || m.metadata.report.download_url) : m.metadata.report.download_url} target="_blank" rel="noreferrer"><FileText/> {m.metadata.report.title || 'Open report'} <Download/></a>}</div></div>) : <div className="ai-chat-welcome"><Bot/><h3>Ask MihiMura naturally.</h3><p>I can remember the current planning scenario across follow-up questions. For example: “I want to plant paddy on 1 acre in Polonnaruwa and need a full report.”</p></div>}{loading && <div className="ai-thinking"><i/><i/><i/><span>{thinkingCopy(mode)}</span></div>}</div>

      {renderModeSwitch()}
      {renderClarification()}
      {(result?.report_ready || currentReport) && <div className="ai-report-ready"><FileText/><span><b>{currentReport?.title || 'Cultivation report can now be generated'}</b><small>{currentReport ? 'Stored privately and linked to this conversation.' : 'The complete report covers agronomy, equipment/tools, inputs, cost/profit scenarios, harvest, logistics and marketing. Estimates and verification gaps remain visible.'}</small></span>{currentReport?.download_url ? <a href={currentReport.download_url} target="_blank" rel="noreferrer">Open PDF <Download/></a> : <Button disabled={reportLoading} onClick={() => void generateReport()}>{reportLoading ? 'Generating PDF…' : 'Generate full PDF'}</Button>}</div>}

      <div className="ai-suggestions">{(result?.suggested_actions?.length ? result.suggested_actions : language === 'Sinhala' ? ['අක්කර 1ක වී වගාවක් සැලසුම් කරන්න', 'අද වාරි ජලය දෙන්න ඕනද?', 'මගේ අවදානම් ලකුණු වැඩි වුණේ ඇයි?', 'මෙම පත්‍ර ගැටලුවට තවත් මොන evidence ඕනද?'] : language === 'Tamil' ? ['1 ஏக்கர் நெல் சாகுபடியை திட்டமிடவும்', 'இன்று நீர்ப்பாசனம் செய்ய வேண்டுமா?', 'என் risk score ஏன் அதிகரித்தது?', 'இந்த இலை பிரச்சினைக்கு இன்னும் என்ன evidence தேவை?'] : ['Plan paddy cultivation for 1 acre', 'Should I irrigate today?', 'Why did my risk score increase?', 'What evidence do you need for this leaf problem?']).slice(0, 5).map((x: string) => <button onClick={() => setQ(x)} key={x}>{x}</button>)}</div>
      <div className="ai-composer"><button onClick={() => nav('/app/scan')} title="Open guided image evidence"><Paperclip/></button><textarea value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void askQuestion(q); } }} placeholder={language === 'Sinhala' ? `${modeLabel(mode)} mode එකෙන් අහන්න… MihiMura මේ සංවාදය මතක තබා ගනී.` : language === 'Tamil' ? `${modeLabel(mode)} முறையில் கேளுங்கள்… MihiMura இந்த உரையாடலை நினைவில் வைத்திருக்கும்.` : `Ask in ${modeLabel(mode)} mode… MihiMura remembers this conversation.`}/><Button onClick={() => void askQuestion(q)} disabled={loading || !q.trim()}><Send/></Button></div>
    </Card>

      <div className="ai-evidence-column"><Card title={effectiveMode === 'simple_chat' ? 'Conversation response' : effectiveMode === 'full_report' ? 'Report overview' : 'Decision contract'} subtitle={effectiveMode === 'simple_chat' ? 'Natural answer first. The router will suggest a stronger workflow when needed.' : effectiveMode === 'full_report' ? 'Comprehensive planning with assumptions, financial scenarios and verification gates.' : 'Simple answer first. Evidence and limitations remain visible.'}>{result ? <div className="decision-result"><div className="decision-risk"><Status tone={result.risk_level === 'emergency' ? 'red' : result.risk_level === 'action' ? 'orange' : result.risk_level === 'low' ? 'green' : 'amber'}>{result.risk_level || 'watch'}</Status><span>Confidence <b>{Math.round((result.confidence || 0) * 100)}%</b></span>{result?.evidence_quality?.level && <span>Evidence <b>{String(result.evidence_quality.level)}</b></span>}<span>Provider <b>{result.provider || 'policy engine'}</b></span></div><section><small>Recommended action</small><h3>{result.recommended_action || result.summary}</h3></section><section><small>Why</small><p>{result.why || 'Continue the conversation to build a grounded decision.'}</p></section><details open><summary>Evidence / source freshness</summary><div className="source-evidence-list">{(result.sources || []).length ? (result.sources || []).map((x: any, i: number) => <div key={i}><ShieldCheck/><span><b>{typeof x === 'string' ? x : (x.name || x.source || 'Source')}</b>{typeof x !== 'string' && <small>{[x.freshness || x.retrieved_at || '', x.citation || ''].filter(Boolean).join(' · ')}</small>}</span></div>) : <span className="inline-warning">No external source was needed yet. Clarification and memory-management steps are workflow evidence, not agronomic evidence.</span>}</div></details><details><summary>Alternatives & “do not do”</summary><div className="decision-lists"><div><b>Alternatives</b>{(result.alternatives || []).map((x: string) => <span key={x}><CheckCircle2/>{x}</span>)}</div><div><b>Do not do</b>{(result.do_not_do || []).map((x: string) => <span key={x}><AlertTriangle/>{x}</span>)}</div></div></details><div className="counterfactual"><div><b>What would change this recommendation?</b><p>{result.counterfactual || 'Re-check the evidence if conditions materially change.'}</p></div></div><section><small>Follow-up</small><p>{result.follow_up || 'Continue in this same conversation.'}</p></section>{result.confirmation_required && <Notice tone="warning" title="Farmer confirmation required">This recommendation does not execute automatically. Review the evidence before creating or changing a field task.</Notice>}<div className="decision-actions"><Button variant="secondary" onClick={speak}><Volume2/> Read aloud</Button><Button variant="secondary" onClick={stopAudio}><VolumeX/> Stop audio</Button><Button variant="secondary" onClick={saveAnswer}><Save/> Save answer</Button>{result.report_ready && !currentReport && <Button variant="secondary" disabled={reportLoading} onClick={() => void generateReport()}><FileText/> Generate report</Button>}{effectiveMode === 'decision_support' && <Button disabled={!project || result.response_type === 'clarification' || result.response_type === 'mode_switch'} onClick={() => void createTask()}><Plus/> Confirm & create task</Button>}</div>{effectiveMode === 'decision_support' && !project && <small className="inline-warning">Select a saved project only when you want to create a consequential field task. General planning conversations do not require one.</small>}</div> : <Empty title="Ask a farm question" detail="The response will show action, why, confidence, alternatives, sources, confirmation and follow-up."/>}</Card>
        <Card title="Agent trace" subtitle="Visible coordination makes the workflow testable and auditable">{result ? <div className="agent-trace-list">{(result.agent_trace || []).map((x: any, i: number) => <div key={i}><i>{i + 1}</i><span><b>{typeof x === 'string' ? 'Agent' : x.agent}</b><p>{typeof x === 'string' ? x : x.action}</p></span><Status tone="green">{typeof x === 'string' ? 'done' : x.status}</Status></div>)}</div> : <div className="agent-placeholder"><Bot/><span>High-level tool and agent coordination appears after the first request.</span></div>}</Card>
      </div>
    </div>
    </div>
  </div>;
}

export function ScanPage() {
  const nav = useNavigate(); const { profile } = useAuth();
  const [files, setFiles] = useState<File[]>([]), [previews, setPreviews] = useState<string[]>([]), [crop, setCrop] = useState('Auto-detect'), [symptoms, setSymptoms] = useState(''), [affected, setAffected] = useState(10), [firstObserved, setFirstObserved] = useState(''), [irrigation, setIrrigation] = useState('Normal'), [recentInputs, setRecentInputs] = useState(''), [projects, setProjects] = useState<any[]>([]), [projectId, setProjectId] = useState(''), [result, setResult] = useState<any>(null), [loading, setLoading] = useState(false), [notice, setNotice] = useState('');
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => { platformApi.projects().then((x: any[]) => { setProjects(x); if (x[0]) { setProjectId(x[0].id); setCrop(x[0].crop || 'Auto-detect') } }).catch(() => setProjects([])); return () => previews.forEach(URL.revokeObjectURL) }, []);
  const choose = (e: any) => { const selected = Array.from(e.target.files || []) as File[]; const valid = selected.filter(x => ['image/jpeg', 'image/png', 'image/webp'].includes(x.type)); if (valid.length !== selected.length) setNotice('Only JPEG, PNG and WebP images are accepted.'); const next = [...files, ...valid].slice(0, 4); previews.forEach(URL.revokeObjectURL); setFiles(next); setPreviews(next.map(URL.createObjectURL)); e.target.value = '' };
  const remove = (i: number) => { const next = files.filter((_, j) => j !== i); previews.forEach(URL.revokeObjectURL); setFiles(next); setPreviews(next.map(URL.createObjectURL)) };
  const contextText = `${symptoms || 'No symptom text provided'}; affected about ${affected}%; first observed ${firstObserved || 'unknown'}; irrigation ${irrigation}; recent inputs ${recentInputs || 'none reported'}; region ${profile?.district || 'unknown'}`;
  const run = async () => { if (!files.length) return; setLoading(true); setNotice(''); try { setResult(await platformApi.diagnose(files, crop, contextText, projectId)) } catch (e: any) { setNotice(e.message) } finally { setLoading(false) } };
  const expert = async () => { if (!result) return; if (!projectId) { setNotice('Select a project before creating an expert evidence case.'); return } await platformApi.addExpertCase({ project_id: projectId, urgency: result.expert_review ? 'high' : 'medium', reason: `Crop scan review: ${result?.differential?.[0]?.condition || 'uncertain condition'}`, evidence: `${result.image_count || files.length} images · crop ${result.crop} · confidence ${Math.round((result.crop_confidence || 0) * 100)}% · symptoms ${(result.observed_symptoms || []).join(', ')}`, preferred_language: profile?.language || 'English' }); nav('/app/expert') };
  return <><section className="page-intro"><div><span className="eyebrow"><Camera /> Guided multimodal evidence</span><h2>Crop health scan</h2><p>A safer assessment combines up to four viewpoints with symptoms, timing, irrigation, recent treatments and project context.</p></div></section>{notice && <Notice tone="info" title="Crop Health Scan">{notice}</Notice>}<div className="scan-layout"><Card title="1. Capture the evidence" subtitle="Leaf front, leaf back, whole plant and field-wide views"><div className="image-slot-grid">{['Leaf front', 'Leaf back', 'Whole plant', 'Field-wide'].map((label, i) => <button key={label} className={`image-slot ${previews[i] ? 'filled' : ''}`} onClick={() => previews[i] ? remove(i) : input.current?.click()}>{previews[i] ? <><img src={previews[i]} alt={label} /><span className="image-remove">Remove</span></> : <><FileImage /><b>{label}</b><span>{i === 0 ? 'Required' : 'Recommended'}</span></>}</button>)}</div><input ref={input} hidden multiple type="file" accept="image/jpeg,image/png,image/webp" onChange={choose} /><div className="field-grid"><label>Crop<select value={crop} onChange={e => setCrop(e.target.value)}><option>Auto-detect</option><option>Chilli</option><option>Paddy</option><option>Tomato</option><option>Brinjal</option><option>Maize</option></select></label><label>Affected area <b>{affected}%</b><input type="range" min="1" max="100" value={affected} onChange={e => setAffected(Number(e.target.value))} /></label><label className="full">Symptoms<textarea value={symptoms} onChange={e => setSymptoms(e.target.value)} placeholder="Describe discoloration, lesions, wilting, insects, field pattern…" /></label><label>First observed<input type="date" value={firstObserved} onChange={e => setFirstObserved(e.target.value)} /></label><label>Irrigation status<select value={irrigation} onChange={e => setIrrigation(e.target.value)}><option>Normal</option><option>Dry</option><option>Waterlogged</option><option>Unknown</option></select></label><label>Recent fertilizer / pesticide<input value={recentInputs} onChange={e => setRecentInputs(e.target.value)} placeholder="None / describe without guessing rates" /></label><label>Project<select value={projectId} onChange={e => setProjectId(e.target.value)}><option value="">No project / general scan</option>{projects.map(p => <option value={p.id} key={p.id}>{p.farm_name} · {p.crop} · {p.stage}</option>)}</select></label></div><Button disabled={!files.length || loading} onClick={() => void run()}>{loading ? 'Vision agent is comparing evidence…' : <> Analyse {files.length || ''} guided image{files.length === 1 ? '' : 's'}</>}</Button></Card><Card title="2. Differential assessment" subtitle="Ranked possibilities with uncertainty and next evidence">{result ? <div className="diagnosis"><div className="diagnosis-top"><div><small>Likely crop</small><h3>{result.crop}</h3><span>{Math.round((result.crop_confidence || 0) * 100)}% crop confidence · {result.image_count || files.length} image(s)</span></div><Status tone={result.expert_review ? 'orange' : 'amber'}>{result.urgency}</Status></div><div className="quality-line"><ShieldCheck /><span>Evidence quality</span><b>{result.quality}</b></div><section><h4>Observed symptoms</h4><div className="tag-row">{(result.observed_symptoms || []).map((x: string) => <span key={x}>{x}</span>)}</div></section><section><h4>Possible conditions</h4><div className="differential-list">{(result.differential || []).map((x: any, i: number) => <div key={`${x.condition}-${i}`}><i>0{i + 1}</i><span><b>{x.condition}</b><p>{x.evidence}</p></span><strong>{Math.round((x.confidence || 0) * 100)}%</strong></div>)}</div></section><section><h4>Immediate low-risk steps</h4><ul>{(result.safe_steps || []).map((x: string) => <li key={x}>{x}</li>)}</ul></section>{result.additional_evidence_needed?.length > 0 && <section><h4>Evidence still needed</h4><div className="tag-row">{result.additional_evidence_needed.map((x: string) => <span key={x}>{x}</span>)}</div></section>}<Notice tone="warning" title="Diagnosis safeguard">{result.disclaimer}</Notice><div className="decision-actions"><Button variant="secondary" disabled={!projectId} onClick={async () => { if (!projectId) return; await platformApi.addTask({ project_id: projectId, title: 'Collect crop-scan follow-up evidence', task_type: 'Crop observation', due_at: new Date(Date.now() + 24 * 3600e3).toISOString(), priority: 'medium', instructions: (result.safe_steps || []).join('; '), weather_dependency: 'Field observation when safe' }); nav('/app/tasks') }}>Create observation task</Button><Button disabled={!projectId} onClick={() => void expert()}><Stethoscope /> Request expert review</Button></div></div> : <Empty title="No analysis yet" detail="Add at least one clear image and symptom context. Multiple guided images improve the evidence package." />}</Card></div></>;
}

export function RecommendationHistoryPage() { const [audit, setAudit] = useState<any[]>([]); useEffect(() => { platformApi.audit().then(setAudit).catch(() => setAudit([])) }, []); const items = audit.filter(x => x.action === 'ai_recommendation' || x.action === 'crop_image_analysis' || x.action === 'create_task' || x.action === 'confirmed_order'); return <><section className="page-intro"><div><span className="eyebrow"><FileText /> Explainable history</span><h2>Recommendation history & action receipts</h2><p>Consequential decisions preserve provider, confidence, user confirmation and outcome instead of disappearing into chat history.</p></div></section><Card title="Verified action receipts" subtitle="Audit trail for recommendations, scans, task creation and confirmed orders">{items.length ? <div className="receipt-list">{items.map((x: any) => <div key={x.id}><span className="receipt-icon"><ShieldCheck /></span><div><small>{new Date(x.created_at).toLocaleString()}</small><b>{String(x.action).replaceAll('_', ' ')}</b><p>{x.details?.question || x.details?.filename || x.details?.filenames?.join(', ') || x.entity}</p></div><Status tone="green">Recorded</Status><button aria-label="Open receipt details"><ArrowRight /></button></div>)}</div> : <Empty title="No action receipts yet" detail="Ask MihiMura a question, run a crop scan, create a task or confirm an order to create the first auditable record." />}</Card></> }

export function ExpertEscalationPage() { const { profile } = useAuth(); const [cases, setCases] = useState<any[]>([]), [projects, setProjects] = useState<any[]>([]), [projectId, setProjectId] = useState(''), [reason, setReason] = useState('Low-confidence crop symptom assessment'), [urgency, setUrgency] = useState('medium'), [notice, setNotice] = useState(''); const load = async () => { const r = await Promise.allSettled([platformApi.expertCases(), platformApi.projects()]); if (r[0].status === 'fulfilled') setCases(r[0].value); if (r[1].status === 'fulfilled') { setProjects(r[1].value); if (!projectId && r[1].value[0]) setProjectId(r[1].value[0].id) } }; useEffect(() => { void load() }, []); const submit = async () => { if (!projectId) { setNotice('Create or select a project before sending an expert case.'); return } await platformApi.addExpertCase({ project_id: projectId, urgency, reason, evidence: 'Digital twin history + recent weather + current AI recommendation + available crop scans', preferred_language: profile?.language || 'English', availability: 'Weekdays 09:00–17:00' }); setNotice('Expert case created with a structured evidence packet.'); await load() }; return <><section className="page-intro"><div><span className="eyebrow"><Stethoscope /> Human-in-the-loop safety</span><h2>Expert escalation</h2><p>Use a qualified agricultural instructor or agronomist when uncertainty, hazard, conflict or repeated deterioration crosses the escalation threshold.</p></div></section>{notice && <Notice tone="info" title="Expert network">{notice}</Notice>}<div className="two-col"><Card title="Create an evidence-backed case" subtitle="MihiMura packages context so the expert does not start from zero"><label>Project<select value={projectId} onChange={e => setProjectId(e.target.value)}><option value="">Select a project</option>{projects.map(p => <option value={p.id} key={p.id}>{p.farm_name} · {p.crop}</option>)}</select></label><label>Reason<textarea value={reason} onChange={e => setReason(e.target.value)} /></label><label>Urgency<select value={urgency} onChange={e => setUrgency(e.target.value)}><option>low</option><option>medium</option><option>high</option><option>emergency</option></select></label><div className="evidence-package"><b>Evidence package includes</b><span>Project crop + stage</span><span>Recent tasks and inputs</span><span>Weather context</span><span>AI differential / confidence</span><span>Farmer observations</span></div><Button disabled={!projectId} onClick={() => void submit()}><Stethoscope /> Submit expert case</Button></Card><Card title="Your cases" subtitle="Expert decisions are stored separately from AI output">{cases.length ? <div className="case-list">{cases.map(c => <div key={c.id}><div><Status tone={c.urgency === 'emergency' ? 'red' : c.urgency === 'high' ? 'orange' : 'amber'}>{c.urgency}</Status><b>{c.reason}</b><p>{c.evidence}</p><small>{new Date(c.created_at).toLocaleString()}</small></div><Status tone={c.status === 'closed' ? 'green' : 'blue'}>{c.status}</Status></div>)}</div> : <Empty title="No open expert case" />}</Card></div><Card title="Automatic escalation thresholds"><div className="threshold-grid">{['Low diagnosis confidence or multiple serious possibilities', 'Restricted / hazardous treatment question', 'Potential regional outbreak or quarantine concern', 'Official emergency alert', 'Conflicting authoritative sources', 'Repeated deterioration despite completed interventions', 'Large-value or unusual order quantity', 'Farmer requests certified opinion or visit'].map(x => <div key={x}><ShieldCheck /><span>{x}</span></div>)}</div></Card></> }