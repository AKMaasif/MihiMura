import { useEffect, useMemo, useState, type MouseEvent } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle2,
  Download,
  EyeIcon,
  FileText,
  Paperclip,
  Plus,
  Save,
  Send,
  ShieldCheck,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Empty, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { useAuth } from '../../context/AuthContext';
import { useLanguage, type AppLanguage } from '../../context/LanguageContext';
import { VoiceAgent } from '../../components/ai/VoiceAgent';
import {
  AGENT_MODES,
  type AgentMode,
  type ChatLanguageMode,
  decisionFromMessage,
  detectMessageLanguage,
  isAgentMode,
  messageText,
  modeLabel,
  projectContext,
  thinkingCopy,
} from './chatHelpers';

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

  const project = useMemo(() => projects.find((x) => x.id === projectId) || null, [projects, projectId]);
  const latestAssistant = useMemo(
    () => [...messages].reverse().find((m) => m.role === 'assistant'),
    [messages],
  );
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
      if (
        chatLanguageMode === 'auto' &&
        ['English', 'Sinhala', 'Tamil'].includes(String(memoryLanguage || ''))
      ) {
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
    Promise.allSettled([platformApi.projects(), platformApi.conversations()]).then(async (r) => {
      if (!alive) return;
      if (r[0].status === 'fulfilled') {
        const projectList = r[0].value as any[];
        setProjects(projectList);
      }
      if (r[1].status === 'fulfilled') {
        const list = (r[1].value as any[]).filter((x) => x.status !== 'archived');
        setConversations(list);
        if (list[0]) {
          await loadConversation(list[0].id);
          if (list[0].project_id) setProjectId(list[0].project_id);
        } else {
          setConversationLoading(false);
        }
      } else setConversationLoading(false);
    });
    return () => {
      alive = false;
    };
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
      setMessages((current) => [
        ...current,
        {
          id: `optimistic-${Date.now()}`,
          role: 'user',
          content: trimmed,
          created_at: new Date().toISOString(),
        },
      ]);
      setQ('');
    }

    try {
      const detectedLanguage =
        chatLanguageMode === 'auto' ? detectMessageLanguage(trimmed, language) : chatLanguageMode;
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
      if (
        chatLanguageMode === 'auto' &&
        ['English', 'Sinhala', 'Tamil'].includes(String(r?.response_language || ''))
      ) {
        setDetectedLanguage(r.response_language as AppLanguage);
      }
      if (r?.report) setReport(r.report);
      setClarificationAnswers({});
      await reloadMessages(nextId);
      await refreshConversations();
    } catch (e: any) {
      setNotice(e.message);
      setMessages((current) => [
        ...current.filter((m) => !String(m.id || '').startsWith('optimistic-')),
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content:
            language === 'Sinhala'
              ? `එම ඉල්ලීම සම්පූර්ණ කළ නොහැකි විය: ${e.message}`
              : language === 'Tamil'
                ? `அந்த கோரிக்கையை முடிக்க முடியவில்லை: ${e.message}`
                : `I could not complete that request: ${e.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const submitClarification = async () => {
    const fields = result?.clarification_fields || [];
    const missingRequired = fields.filter(
      (f: any) =>
        f.required && clarificationAnswers[f.key] === undefined && !activeMemory?.known_facts?.[f.key],
    );
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
    } catch (e: any) {
      setNotice(e.message);
    }
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
    } catch (e: any) {
      setNotice(e.message);
    } finally {
      setReportLoading(false);
    }
  };

  const speak = () => {
    if (!result?.summary || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(result.summary);
    u.lang = language === 'Sinhala' ? 'si-LK' : language === 'Tamil' ? 'ta-LK' : 'en-LK';
    window.speechSynthesis.speak(u);
  };
  const stopAudio = () => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  };
  const saveAnswer = () => {
    if (!result) return;
    const key = 'mihimura_saved_ai_answers';
    const items = JSON.parse(localStorage.getItem(key) || '[]');
    items.unshift({
      saved_at: new Date().toISOString(),
      conversation_id: conversationId || null,
      project_id: project?.id || null,
      language,
      result,
    });
    localStorage.setItem(key, JSON.stringify(items.slice(0, 50)));
    setNotice(
      'Answer saved locally for quick reference. The conversation itself is already persisted in Supabase.',
    );
  };
  const createTask = async () => {
    if (!result || !project) {
      setNotice('Create or select a cultivation project before converting this recommendation into a task.');
      return;
    }
    await platformApi.addTask({
      project_id: project.id,
      title: result.recommended_action,
      task_type: 'AI recommendation',
      due_at: new Date(Date.now() + 24 * 3600e3).toISOString(),
      priority: ['action', 'emergency'].includes(result.risk_level) ? 'high' : 'medium',
      weather_dependency: 'Re-check current weather before execution',
      instructions: result.why,
      schedule_reason: 'Created after explicit farmer confirmation from MihiMura recommendation',
    });
    setNotice('Task created. The confirmation and recommendation remain visible in the audit trail.');
    nav('/app/tasks');
  };

  const renderModeSwitch = () => {
    if (
      result?.response_type !== 'mode_switch' ||
      !result?.suggested_mode ||
      !isAgentMode(result.suggested_mode)
    )
      return null;
    const suggested = result.suggested_mode as AgentMode;
    const originalQuestion = String(result.original_question || '').trim();
    return (
      <div className="ai-mode-switch-card">
        <div className="ai-mode-switch-icon"></div>
        <div className="ai-mode-switch-copy">
          <small>
            {language === 'Sinhala'
              ? 'වඩා සුදුසු workflow එකක් හඳුනාගත්තා'
              : language === 'Tamil'
                ? 'சிறந்த workflow கண்டறியப்பட்டது'
                : 'Better workflow detected'}
          </small>
          <h3>
            {language === 'Sinhala'
              ? `${modeLabel(suggested)} වෙත මාරු වෙන්නද?`
              : language === 'Tamil'
                ? `${modeLabel(suggested)} முறைக்கு மாறவா?`
                : `Switch to ${modeLabel(suggested)}?`}
          </h3>
          <p>{result.why || result.mode_reason}</p>
          <span>
            {language === 'Sinhala'
              ? 'ඔබගේ සංවාදය සහ farm context එලෙසම පවතී; වෙනස් වන්නේ workflow/tool permissions පමණයි.'
              : language === 'Tamil'
                ? 'உங்கள் உரையாடலும் farm context-உம் அதேபடி இருக்கும்; workflow/tool permissions மட்டும் மாறும்.'
                : 'Your conversation and farm context stay the same; only the workflow/tool permissions change.'}
          </span>
        </div>
        <div className="ai-mode-switch-actions">
          <Button
            disabled={loading || !originalQuestion}
            onClick={() => {
              setMode(suggested);
              void askQuestion(originalQuestion, {}, suggested, false, true);
            }}
          >
            {language === 'Sinhala'
              ? 'මාරු වී ඉදිරියට'
              : language === 'Tamil'
                ? 'மாற்றி தொடரவும்'
                : 'Switch & continue'}{' '}
            <ArrowRight />
          </Button>
          <Button
            variant="secondary"
            disabled={loading || !originalQuestion}
            onClick={() => void askQuestion(originalQuestion, {}, mode, true, true)}
          >
            {language === 'Sinhala'
              ? `${modeLabel(mode)} තුළ සිටින්න`
              : language === 'Tamil'
                ? `${modeLabel(mode)} முறையில் தொடரவும்`
                : `Stay in ${modeLabel(mode)}`}
          </Button>
        </div>
      </div>
    );
  };

  const renderClarification = () => {
    const fields = result?.clarification_fields || [];
    if (result?.response_type !== 'clarification' || !fields.length) return null;
    return (
      <div className="ai-clarification-card">
        <div className="ai-clarification-head">
          <span>
            <b>
              {language === 'Sinhala'
                ? 'අත්‍යවශ්‍ය වාර්තා තොරතුරු පමණයි'
                : language === 'Tamil'
                  ? 'கட்டாய அறிக்கை விவரங்கள் மட்டும்'
                  : 'Only the required report details'}
            </b>
            <small>
              {language === 'Sinhala'
                ? 'කන්නය, වාරි මූලාශ්‍රය, ප්‍රභේදය සහ වගා දිනය වාර්තාව නවත්වන්නේ නැහැ; ඒවා පැහැදිලි උපකල්පන ලෙස තැබිය හැක.'
                : language === 'Tamil'
                  ? 'பருவம், பாசனம், வகை மற்றும் நடவு தேதி அறிக்கையைத் தடுக்காது; அவற்றை தெளிவான கருதுகோள்களாக வைத்துக்கொள்ளலாம்.'
                  : 'Optional season, irrigation, variety and planting date will not block the report; they can remain visible assumptions.'}
            </small>
          </span>
        </div>
        <div className="ai-clarification-grid">
          {fields.map((field: any) => (
            <label key={field.key}>
              {field.label}
              {field.required && <em>required</em>}
              {field.type === 'select' ? (
                <select
                  value={clarificationAnswers[field.key] ?? ''}
                  onChange={(e) => setClarificationAnswers((x) => ({ ...x, [field.key]: e.target.value }))}
                >
                  <option value="">
                    {language === 'Sinhala'
                      ? 'තෝරන්න…'
                      : language === 'Tamil'
                        ? 'தேர்வு செய்யவும்…'
                        : 'Choose…'}
                  </option>
                  {(field.options || []).map((option: any) => {
                    const value = typeof option === 'string' ? option : option.value;
                    const label = typeof option === 'string' ? option : option.label || option.value;
                    return (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    );
                  })}
                </select>
              ) : (
                <input
                  type={field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'}
                  step={field.type === 'number' ? '0.01' : undefined}
                  placeholder={field.placeholder || ''}
                  value={clarificationAnswers[field.key] ?? ''}
                  onChange={(e) =>
                    setClarificationAnswers((x) => ({
                      ...x,
                      [field.key]:
                        field.type === 'number'
                          ? e.target.value === ''
                            ? ''
                            : Number(e.target.value)
                          : e.target.value,
                    }))
                  }
                />
              )}
            </label>
          ))}
        </div>
        <div className="ai-clarification-actions">
          <Button disabled={loading} onClick={() => void submitClarification()}>
            {loading
              ? language === 'Sinhala'
                ? 'පසුබිම යාවත්කාලීන කරමින්…'
                : language === 'Tamil'
                  ? 'சூழலை புதுப்பிக்கிறது…'
                  : 'Updating context…'
              : language === 'Sinhala'
                ? 'මෙම තොරතුරු සමඟ ඉදිරියට යන්න'
                : language === 'Tamil'
                  ? 'இந்த விவரங்களுடன் தொடரவும்'
                  : 'Continue with these details'}{' '}
            <ArrowRight />
          </Button>
        </div>
      </div>
    );
  };

  const currentReport = report || result?.report || latestAssistant?.metadata?.report;
  const effectiveMode: AgentMode = isAgentMode(result?.effective_mode) ? result.effective_mode : mode;
  const modeDescription = AGENT_MODES.find((x) => x.id === mode)?.description || AGENT_MODES[0].description;

  return (
    <div className="ai-shell">
      <aside className="ai-history-panel">
        <div className="ai-history-head">
          <div>
            <Bot />
            <span>
              <b>Conversations</b>
              <small>Persistent farm memory</small>
            </span>
          </div>
          <button onClick={newChat} title="New conversation">
            <Plus />
          </button>
        </div>
        <button className="ai-new-chat" onClick={newChat}>
          <Plus /> New farm conversation
        </button>
        <div className="ai-history-list">
          {conversations.length ? (
            conversations.map((c) => (
              <button
                className={conversationId === c.id ? 'active' : ''}
                key={c.id}
                onClick={() => {
                  void loadConversation(c.id);
                  if (c.project_id) setProjectId(c.project_id);
                }}
              >
                <span>
                  <b>{c.title || 'Farm conversation'}</b>
                  <small>{new Date(c.updated_at || c.created_at).toLocaleString()}</small>
                </span>
                <i onClick={(e) => void archiveCurrent(c.id, e)} title="Archive">
                  ×
                </i>
              </button>
            ))
          ) : (
            <div className="ai-history-empty">
              <span>No saved conversations yet.</span>
              <small>Your first message will create one.</small>
            </div>
          )}
        </div>
        <div className="ai-memory-note">
          <ShieldCheck />
          <span>
            <b>Context precedence</b>
            <small>Current message → conversation → selected project → profile default.</small>
          </span>
        </div>
      </aside>

      <div className="ai-main-column">
        <div className="ai-mode-bar" role="tablist" aria-label="MihiMura AI mode">
          <div className="ai-mode-options">
            {AGENT_MODES.map((option) => (
              <button
                type="button"
                role="tab"
                aria-selected={mode === option.id}
                className={mode === option.id ? 'active' : ''}
                key={option.id}
                onClick={() => setMode(option.id)}
              >
                {option.id === 'auto' ? (
                  <EyeIcon />
                ) : option.id === 'simple_chat' ? (
                  <Bot />
                ) : option.id === 'decision_support' ? (
                  <ShieldCheck />
                ) : (
                  <FileText />
                )}
                <span>
                  <b>{option.label}</b>
                </span>
              </button>
            ))}
          </div>
          <div className="ai-mode-description">
            <span>
              <b>{modeLabel(mode)}</b>
              {modeDescription}
            </span>
            {result?.detected_mode && <i>Detected: {modeLabel(result.detected_mode)}</i>}
          </div>
        </div>

        <div className="ai-workbench">
          <Card
            className="ai-chat-card"
            title="MihiMura AI"
            subtitle={`${modeLabel(effectiveMode)} · persistent farm conversation`}
            action={
              <select
                className="compact-select"
                value={chatLanguageMode}
                onChange={(e) => {
                  const next = e.target.value as ChatLanguageMode;
                  setChatLanguageMode(next);
                  if (next !== 'auto') void setLanguage(next);
                }}
              >
                <option value="auto">Auto detect · {language}</option>
                <option value="English">English</option>
                <option value="Sinhala">සිංහල</option>
                <option value="Tamil">தமிழ்</option>
              </select>
            }
          >
            <div className="ai-context-selector">
              <div className="ai-context-strip">
                <span> Active context</span>
                <b>
                  {activeMemory?.known_facts?.location
                    ? `${activeMemory.known_facts.location} · conversation scenario`
                    : project
                      ? `${project.farm_name} · ${project.crop} · ${project.stage}`
                      : `${profile?.district || 'Sri Lanka'} · General location context`}
                </b>
                <small>
                  {activeMemory?.summary ||
                    (project
                      ? 'Farm memory + weather + climate baseline + safety policy'
                      : 'No project selected. Explicit conversation facts override profile defaults.')}
                </small>
              </div>
              <label>
                Project context
                <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                  <option value="">General / no project</option>
                  {projects.map((p) => (
                    <option value={p.id} key={p.id}>
                      {p.farm_name} · {p.crop} · {p.stage}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <VoiceAgent
              language={language}
              project={project}
              profile={profile}
              conversationId={conversationId || undefined}
              mode={mode}
              onDecision={(voiceResult) => {
                const nextId = voiceResult?.conversation_id || conversationId;
                if (nextId) setConversationId(nextId);
                setResult(voiceResult);
                if (voiceResult?.report) setReport(voiceResult.report);
                if (nextId) {
                  void reloadMessages(nextId);
                  void refreshConversations();
                }
              }}
            />
            {notice && (
              <Notice tone="info" title="MihiMura">
                {notice}
              </Notice>
            )}

            <div
              className={`ai-message-list ${!conversationLoading && !messages.length && !loading ? 'is-empty' : ''}`}
            >
              {conversationLoading ? (
                <div className="ai-thinking">
                  <i />
                  <i />
                  <i />
                  <span>Loading conversation memory…</span>
                </div>
              ) : messages.length ? (
                messages.map((m, i) => (
                  <div className={`ai-msg ${m.role}`} key={m.id || i}>
                    {m.role === 'assistant' && <Bot />}
                    <div>
                      <span className="ai-message-text">{messageText(m)}</span>
                      {m?.metadata?.report?.download_url && (
                        <a
                          className="ai-inline-report"
                          href={
                            currentReport?.id === m.metadata.report.id
                              ? currentReport.download_url || m.metadata.report.download_url
                              : m.metadata.report.download_url
                          }
                          target="_blank"
                          rel="noreferrer"
                        >
                          <FileText /> {m.metadata.report.title || 'Open report'} <Download />
                        </a>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="ai-chat-welcome">
                  <Bot />
                  <h3>Ask MihiMura naturally.</h3>
                  <p>
                    I can remember the current planning scenario across follow-up questions. For example: “I
                    want to plant paddy on 1 acre in Polonnaruwa and need a full report.”
                  </p>
                </div>
              )}
              {loading && (
                <div className="ai-thinking">
                  <i />
                  <i />
                  <i />
                  <span>{thinkingCopy(mode)}</span>
                </div>
              )}
            </div>

            {renderModeSwitch()}
            {renderClarification()}
            {(result?.report_ready || currentReport) && (
              <div className="ai-report-ready">
                <FileText />
                <span>
                  <b>{currentReport?.title || 'Cultivation report can now be generated'}</b>
                  <small>
                    {currentReport
                      ? 'Stored privately and linked to this conversation.'
                      : 'The complete report covers agronomy, equipment/tools, inputs, cost/profit scenarios, harvest, logistics and marketing. Estimates and verification gaps remain visible.'}
                  </small>
                </span>
                {currentReport?.download_url ? (
                  <a href={currentReport.download_url} target="_blank" rel="noreferrer">
                    Open PDF <Download />
                  </a>
                ) : (
                  <Button disabled={reportLoading} onClick={() => void generateReport()}>
                    {reportLoading ? 'Generating PDF…' : 'Generate full PDF'}
                  </Button>
                )}
              </div>
            )}

            <div className="ai-suggestions">
              {(result?.suggested_actions?.length
                ? result.suggested_actions
                : language === 'Sinhala'
                  ? [
                      'අක්කර 1ක වී වගාවක් සැලසුම් කරන්න',
                      'අද වාරි ජලය දෙන්න ඕනද?',
                      'මගේ අවදානම් ලකුණු වැඩි වුණේ ඇයි?',
                      'මෙම පත්‍ර ගැටලුවට තවත් මොන evidence ඕනද?',
                    ]
                  : language === 'Tamil'
                    ? [
                        '1 ஏக்கர் நெல் சாகுபடியை திட்டமிடவும்',
                        'இன்று நீர்ப்பாசனம் செய்ய வேண்டுமா?',
                        'என் risk score ஏன் அதிகரித்தது?',
                        'இந்த இலை பிரச்சினைக்கு இன்னும் என்ன evidence தேவை?',
                      ]
                    : [
                        'Plan paddy cultivation for 1 acre',
                        'Should I irrigate today?',
                        'Why did my risk score increase?',
                        'What evidence do you need for this leaf problem?',
                      ]
              )
                .slice(0, 5)
                .map((x: string) => (
                  <button onClick={() => setQ(x)} key={x}>
                    {x}
                  </button>
                ))}
            </div>
            <div className="ai-composer">
              <button onClick={() => nav('/app/scan')} title="Open guided image evidence">
                <Paperclip />
              </button>
              <textarea
                value={q}
                maxLength={4000}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    void askQuestion(q);
                  }
                }}
                placeholder={
                  language === 'Sinhala'
                    ? `${modeLabel(mode)} mode එකෙන් අහන්න… MihiMura මේ සංවාදය මතක තබා ගනී.`
                    : language === 'Tamil'
                      ? `${modeLabel(mode)} முறையில் கேளுங்கள்… MihiMura இந்த உரையாடலை நினைவில் வைத்திருக்கும்.`
                      : `Ask in ${modeLabel(mode)} mode… MihiMura remembers this conversation.`
                }
              />
              <Button onClick={() => void askQuestion(q)} disabled={loading || !q.trim()}>
                <Send />
              </Button>
            </div>
          </Card>

          <div className="ai-evidence-column">
            <Card
              title={
                effectiveMode === 'simple_chat'
                  ? 'Conversation response'
                  : effectiveMode === 'full_report'
                    ? 'Report overview'
                    : 'Decision contract'
              }
              subtitle={
                effectiveMode === 'simple_chat'
                  ? 'Natural answer first. The router will suggest a stronger workflow when needed.'
                  : effectiveMode === 'full_report'
                    ? 'Comprehensive planning with assumptions, financial scenarios and verification gates.'
                    : 'Simple answer first. Evidence and limitations remain visible.'
              }
            >
              {result ? (
                <div className="decision-result">
                  <div className="decision-risk">
                    <Status
                      tone={
                        result.risk_level === 'emergency'
                          ? 'red'
                          : result.risk_level === 'action'
                            ? 'orange'
                            : result.risk_level === 'low'
                              ? 'green'
                              : 'amber'
                      }
                    >
                      {result.risk_level || 'watch'}
                    </Status>
                    <span>
                      Confidence <b>{Math.round((result.confidence || 0) * 100)}%</b>
                    </span>
                    {result?.evidence_quality?.level && (
                      <span>
                        Evidence <b>{String(result.evidence_quality.level)}</b>
                      </span>
                    )}
                    <span>
                      Provider <b>{result.provider || 'policy engine'}</b>
                    </span>
                  </div>
                  <section>
                    <small>Recommended action</small>
                    <h3>{result.recommended_action || result.summary}</h3>
                  </section>
                  <section>
                    <small>Why</small>
                    <p>{result.why || 'Continue the conversation to build a grounded decision.'}</p>
                  </section>
                  <details open>
                    <summary>Evidence / source freshness</summary>
                    <div className="source-evidence-list">
                      {(result.sources || []).length ? (
                        (result.sources || []).map((x: any, i: number) => (
                          <div key={i}>
                            <ShieldCheck />
                            <span>
                              <b>{typeof x === 'string' ? x : x.name || x.source || 'Source'}</b>
                              {typeof x !== 'string' && (
                                <small>
                                  {[x.freshness || x.retrieved_at || '', x.citation || '']
                                    .filter(Boolean)
                                    .join(' · ')}
                                </small>
                              )}
                            </span>
                          </div>
                        ))
                      ) : (
                        <span className="inline-warning">
                          No external source was needed yet. Clarification and memory-management steps are
                          workflow evidence, not agronomic evidence.
                        </span>
                      )}
                    </div>
                  </details>
                  <details>
                    <summary>Alternatives & “do not do”</summary>
                    <div className="decision-lists">
                      <div>
                        <b>Alternatives</b>
                        {(result.alternatives || []).map((x: string) => (
                          <span key={x}>
                            <CheckCircle2 />
                            {x}
                          </span>
                        ))}
                      </div>
                      <div>
                        <b>Do not do</b>
                        {(result.do_not_do || []).map((x: string) => (
                          <span key={x}>
                            <AlertTriangle />
                            {x}
                          </span>
                        ))}
                      </div>
                    </div>
                  </details>
                  <div className="counterfactual">
                    <div>
                      <b>What would change this recommendation?</b>
                      <p>
                        {result.counterfactual || 'Re-check the evidence if conditions materially change.'}
                      </p>
                    </div>
                  </div>
                  <section>
                    <small>Follow-up</small>
                    <p>{result.follow_up || 'Continue in this same conversation.'}</p>
                  </section>
                  {result.confirmation_required && (
                    <Notice tone="warning" title="Farmer confirmation required">
                      This recommendation does not execute automatically. Review the evidence before creating
                      or changing a field task.
                    </Notice>
                  )}
                  <div className="decision-actions">
                    <Button variant="secondary" onClick={speak}>
                      <Volume2 /> Read aloud
                    </Button>
                    <Button variant="secondary" onClick={stopAudio}>
                      <VolumeX /> Stop audio
                    </Button>
                    <Button variant="secondary" onClick={saveAnswer}>
                      <Save /> Save answer
                    </Button>
                    {result.report_ready && !currentReport && (
                      <Button
                        variant="secondary"
                        disabled={reportLoading}
                        onClick={() => void generateReport()}
                      >
                        <FileText /> Generate report
                      </Button>
                    )}
                    {effectiveMode === 'decision_support' && (
                      <Button
                        disabled={
                          !project ||
                          result.response_type === 'clarification' ||
                          result.response_type === 'mode_switch'
                        }
                        onClick={() => void createTask()}
                      >
                        <Plus /> Confirm & create task
                      </Button>
                    )}
                  </div>
                  {effectiveMode === 'decision_support' && !project && (
                    <small className="inline-warning">
                      Select a saved project only when you want to create a consequential field task. General
                      planning conversations do not require one.
                    </small>
                  )}
                </div>
              ) : (
                <Empty
                  title="Ask a farm question"
                  detail="The response will show action, why, confidence, alternatives, sources, confirmation and follow-up."
                />
              )}
            </Card>
            <Card
              title="Agent trace"
              subtitle="Visible coordination makes the workflow testable and auditable"
            >
              {result ? (
                <div className="agent-trace-list">
                  {(result.agent_trace || []).map((x: any, i: number) => (
                    <div key={i}>
                      <i>{i + 1}</i>
                      <span>
                        <b>{typeof x === 'string' ? 'Agent' : x.agent}</b>
                        <p>{typeof x === 'string' ? x : x.action}</p>
                      </span>
                      <Status tone="green">{typeof x === 'string' ? 'done' : x.status}</Status>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="agent-placeholder">
                  <Bot />
                  <span>High-level tool and agent coordination appears after the first request.</span>
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
