import { useEffect, useState } from 'react';
import { Activity, Bot, Database, Gauge, Globe2, Lock, RefreshCcw, ShieldCheck, Trash2 } from 'lucide-react';
import { Button, Card, Empty, Metric, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';

export function AdminPage() {
  const [health, setHealth] = useState<any>(null),
    [audit, setAudit] = useState<any[]>([]),
    [users, setUsers] = useState<any[]>([]),
    [runs, setRuns] = useState<any[]>([]),
    [knowledge, setKnowledge] = useState<any[]>([]),
    [ingestionJobs, setIngestionJobs] = useState<any[]>([]),
    [evalStatus, setEvalStatus] = useState<any>(null),
    [evalRuns, setEvalRuns] = useState<any[]>([]),
    [evalBusy, setEvalBusy] = useState<'policy' | 'live' | ''>(''),
    [notice, setNotice] = useState('');
  const [knowledgeFile, setKnowledgeFile] = useState<File | null>(null),
    [knowledgeMeta, setKnowledgeMeta] = useState<any>({
      title: '',
      authority: 'Sri Lanka Department of Agriculture',
      authority_tier: 1,
      document_type: 'guidance',
      crop: 'Paddy',
      language: 'English',
      source_url: '',
    }),
    [knowledgeBusy, setKnowledgeBusy] = useState(false);
  const load = () =>
    Promise.allSettled([
      platformApi.health(),
      platformApi.audit(),
      platformApi.adminUsers(),
      platformApi.agentRuns(),
      platformApi.knowledgeDocuments(),
      platformApi.knowledgeIngestionJobs(),
      platformApi.evaluationStatus(),
      platformApi.evaluationRuns(),
    ]).then((r) => {
      if (r[0].status === 'fulfilled') setHealth(r[0].value);
      if (r[1].status === 'fulfilled') setAudit(r[1].value);
      if (r[2].status === 'fulfilled') setUsers(r[2].value);
      if (r[3].status === 'fulfilled') setRuns(r[3].value);
      if (r[4].status === 'fulfilled') setKnowledge(r[4].value);
      if (r[5].status === 'fulfilled') setIngestionJobs(r[5].value);
      if (r[6].status === 'fulfilled') setEvalStatus(r[6].value);
      if (r[7].status === 'fulfilled') setEvalRuns(r[7].value);
    });
  useEffect(() => {
    void load();
  }, []);
  const active = ingestionJobs.some((j: any) =>
    ['queued', 'processing', 'cancel_requested'].includes(j.status),
  );
  useEffect(() => {
    if (!active) return;
    const t = window.setInterval(
      () =>
        platformApi
          .knowledgeIngestionJobs()
          .then(setIngestionJobs)
          .catch(() => {}),
      2000,
    );
    return () => window.clearInterval(t);
  }, [active]);
  const verify = async (uid: string, value: boolean) => {
    try {
      await platformApi.adminVerify(uid, value);
      setNotice(value ? 'Professional identity verified.' : 'Professional access revoked.');
      await load();
    } catch (e: any) {
      setNotice(e.message);
    }
  };
  const setStatus = async (uid: string, status: 'active' | 'suspended') => {
    try {
      await platformApi.adminSetStatus(uid, status);
      setNotice(
        status === 'suspended'
          ? 'User access suspended at the MihiMura API boundary.'
          : 'User access restored.',
      );
      await load();
    } catch (e: any) {
      setNotice(e.message);
    }
  };
  const ingestKnowledge = async () => {
    if (!knowledgeFile || !knowledgeMeta.title.trim() || !knowledgeMeta.authority.trim()) {
      setNotice('Choose a document and provide title + authority first.');
      return;
    }
    setKnowledgeBusy(true);
    try {
      const r: any = await platformApi.uploadKnowledgeDocument(knowledgeFile, knowledgeMeta);
      if (r?.duplicate)
        setNotice(`This exact document is already fully indexed (${r?.chunk_count || 0} chunks).`);
      else {
        setNotice(
          r?.already_running
            ? 'This document already has an active ingestion job.'
            : `Upload accepted. Background job ${r?.job?.id || ''} is now running.`,
        );
        setKnowledgeFile(null);
        setKnowledgeMeta({ ...knowledgeMeta, title: '' });
      }
      await load();
    } catch (e: any) {
      setNotice(e.message);
    } finally {
      setKnowledgeBusy(false);
    }
  };
  const retryIngestion = async (id: string) => {
    try {
      await platformApi.retryKnowledgeIngestion(id);
      setNotice('Retry queued.');
      await load();
    } catch (e: any) {
      setNotice(e.message);
    }
  };
  const cancelIngestion = async (id: string) => {
    try {
      await platformApi.cancelKnowledgeIngestion(id);
      setNotice('Cancellation requested.');
      await load();
    } catch (e: any) {
      setNotice(e.message);
    }
  };
  const removeKnowledge = async (id: string) => {
    if (!window.confirm('Remove this knowledge document and all indexed chunks?')) return;
    try {
      await platformApi.deleteKnowledgeDocument(id);
      setNotice('Knowledge document removed.');
      await load();
    } catch (e: any) {
      setNotice(e.message);
    }
  };
  const runEvaluation = async (mode: 'policy' | 'live') => {
    setEvalBusy(mode);
    try {
      const result: any = await platformApi.runEvaluation(mode, [], true);
      const pct = Math.round(Number(result?.summary?.pass_rate || 0) * 100);
      setNotice(
        `${mode === 'policy' ? 'Policy' : 'Live'} evaluation completed: ${result?.summary?.passed || 0}/${result?.summary?.cases || 0} passed (${pct}%).${result?.persisted ? ' Results saved.' : result?.persistence_error ? ` ${result.persistence_error}` : ''}`,
      );
      await load();
    } catch (e: any) {
      setNotice(e.message);
    } finally {
      setEvalBusy('');
    }
  };
  const controls = [
    ['Hazardous-treatment gate', 'Enabled'],
    ['Commerce confirmation gate', 'Enabled'],
    ['Community privacy threshold', 'Enabled'],
    ['Official-warning precedence', 'Enabled'],
    ['Action receipts', 'Enabled'],
    ['Low-confidence escalation', 'Enabled'],
  ];
  const professional = users.filter((u) => ['agronomist', 'supplier', 'analyst', 'admin'].includes(u.role));
  const stage = (x: any) => String(x || 'queued').replaceAll('_', ' ');
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Database /> Source, agent & governance operations
          </span>
          <h2>Administration and data operations</h2>
          <p>
            Operational visibility includes source health, Supabase identities, access status, policy gates,
            professional verification, agent runs and audit logs.
          </p>
        </div>
        <Button variant="secondary" onClick={() => void load()}>
          <RefreshCcw /> Refresh status
        </Button>
      </section>
      {notice && (
        <Notice tone="info" title="Administration">
          {notice}
        </Notice>
      )}
      <div className="dashboard-metrics">
        <Metric
          label="API"
          value={health?.status || 'Checking'}
          note={`v${health?.version || '7.1.0'}`}
          icon={Activity}
        />
        <Metric
          label="AI providers"
          value={health?.ai_providers?.join(', ') || 'Rules-based fallback'}
          note="Configured generation providers"
          icon={Bot}
          tone={health?.ai_configured ? 'green' : 'orange'}
        />
        <Metric
          label="Supabase"
          value={health?.supabase_configured ? 'Configured' : 'Needs setup'}
          note="Auth + PostgreSQL + Storage"
          icon={Lock}
          tone={health?.supabase_configured ? 'green' : 'orange'}
        />
        <Metric
          label="Knowledge RAG"
          value={
            health?.rag_database_ready && health?.rag_configured
              ? 'Ready'
              : health?.rag_configured
                ? 'Run migration'
                : 'Needs setup'
          }
          note={
            health?.rag_database_ready && health?.rag_configured
              ? `${health?.embedding_model || 'embedding'} · ${health?.embedding_dimension || 768}d`
              : 'pgvector + hybrid search'
          }
          icon={Database}
          tone={health?.rag_configured ? 'green' : 'orange'}
        />
        <Metric
          label="Sentinel Hub"
          value={health?.sentinel_configured ? 'Configured' : 'Demo snapshot'}
          note="satellite catalogue"
          icon={Globe2}
          tone={health?.sentinel_configured ? 'green' : 'orange'}
        />
        <Metric
          label="AI evaluation"
          value={
            health?.evaluation?.benchmark_cases ? `${health.evaluation.benchmark_cases} cases` : 'Checking'
          }
          note={
            health?.evaluation?.database_ready ? 'Phase 4A results storage ready' : 'Run Phase 4A migration'
          }
          icon={Gauge}
          tone={health?.evaluation?.database_ready ? 'green' : 'orange'}
        />
      </div>
      <div className="two-col">
        <Card title="Governance controls">
          <div className="governance-list">
            {controls.map((x) => (
              <div key={x[0]}>
                <ShieldCheck />
                <span>{x[0]}</span>
                <Status tone="green">{x[1]}</Status>
              </div>
            ))}
          </div>
        </Card>
        <Card title="Data source status">
          <div className="source-status-list">
            {[
              ['Open-Meteo', 'Forecast', 'No key', 'live'],
              ['NASA POWER', 'Climate baseline', 'No key', 'live'],
              ['xAI / Meta', 'Text and configured vision models', 'API key + model ID', 'optional'],
              ['Gemini', 'Optional generation, vector indexing and server speech', 'API key', 'optional'],
              ['Supabase', 'Auth + PostgreSQL + Storage', 'URL + publishable/secret keys', 'core'],
              ['Copernicus Sentinel Hub', 'Satellite catalogue', 'OAuth client', 'optional'],
              [
                'Sri Lanka official sources',
                'Agronomy RAG corpus',
                'pgvector + FTS ingestion',
                'core knowledge',
              ],
            ].map((x) => (
              <div key={x[0]}>
                <i className={x[3]} />
                <span>
                  <b>{x[0]}</b>
                  <small>{x[1]}</small>
                </span>
                <em>{x[2]}</em>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <Card
        title="Phase 4A · AI evaluation & validation"
        subtitle="Repeatable benchmarks test routing, multilingual behavior, tool selection, safety gates, confidence integrity and response completeness."
      >
        <div className="evaluation-toolbar">
          <div>
            <b>{evalStatus?.benchmark_cases || health?.evaluation?.benchmark_cases || 0} benchmark cases</b>
            <small>English · Sinhala · Tamil · policy + live production-path modes</small>
          </div>
          <div>
            <Button
              variant="secondary"
              disabled={Boolean(evalBusy)}
              onClick={() => void runEvaluation('policy')}
            >
              <ShieldCheck /> {evalBusy === 'policy' ? 'Running policy checks…' : 'Run policy benchmark'}
            </Button>
            <Button disabled={Boolean(evalBusy)} onClick={() => void runEvaluation('live')}>
              <Bot /> {evalBusy === 'live' ? 'Running live AI checks…' : 'Run live benchmark'}
            </Button>
          </div>
        </div>
        {!evalStatus?.database_ready && (
          <Notice tone="warning" title="Evaluation persistence is not initialized">
            Run <code>supabase/migrations/20260813_0004_phase4a_evaluation.sql</code>. Policy/live runs can
            still execute, but they cannot be stored until the migration is applied.
          </Notice>
        )}
        <div className="evaluation-run-list">
          {evalRuns.length ? (
            evalRuns.slice(0, 8).map((r: any) => (
              <div key={r.id}>
                <span>
                  <b>
                    {String(r.mode || 'policy').toUpperCase()} · {Math.round(Number(r.pass_rate || 0) * 100)}%
                    pass
                  </b>
                  <small>
                    {new Date(r.created_at).toLocaleString()} · {r.passed_count}/{r.case_count} passed · avg{' '}
                    {Math.round(Number(r.average_score || 0) * 100)}% · {Number(r.duration_ms || 0)} ms
                  </small>
                </span>
                <Status tone={r.status === 'passed' ? 'green' : 'orange'}>
                  {String(r.status || 'needs_review').replaceAll('_', ' ')}
                </Status>
              </div>
            ))
          ) : (
            <Empty
              title="No stored evaluation run yet"
              detail="Run the policy benchmark first. It is deterministic and does not require live AI/tool calls."
            />
          )}
        </div>
      </Card>
      <div className="two-col">
        <Card
          title="Agricultural RAG ingestion"
          subtitle="Upload returns quickly; extraction, embedding and indexing continue in a tracked background job."
        >
          <label>
            Document title
            <input
              value={knowledgeMeta.title}
              onChange={(e) => setKnowledgeMeta({ ...knowledgeMeta, title: e.target.value })}
              placeholder="Rice cultivation guidance"
            />
          </label>
          <label>
            Authority
            <input
              value={knowledgeMeta.authority}
              onChange={(e) => setKnowledgeMeta({ ...knowledgeMeta, authority: e.target.value })}
            />
          </label>
          <div className="two-col">
            <label>
              Authority tier
              <select
                value={knowledgeMeta.authority_tier}
                onChange={(e) =>
                  setKnowledgeMeta({ ...knowledgeMeta, authority_tier: Number(e.target.value) })
                }
              >
                <option value={1}>Tier 1 · Official</option>
                <option value={2}>Tier 2 · University / research</option>
                <option value={3}>Tier 3 · Verified industry</option>
                <option value={4}>Tier 4 · General curated</option>
              </select>
            </label>
            <label>
              Crop
              <input
                value={knowledgeMeta.crop}
                onChange={(e) => setKnowledgeMeta({ ...knowledgeMeta, crop: e.target.value })}
                placeholder="Paddy or General"
              />
            </label>
          </div>
          <label>
            Document language
            <select
              value={knowledgeMeta.language}
              onChange={(e) => setKnowledgeMeta({ ...knowledgeMeta, language: e.target.value })}
            >
              <option>English</option>
              <option>Sinhala</option>
              <option>Tamil</option>
            </select>
          </label>
          <label>
            Official / source URL
            <input
              value={knowledgeMeta.source_url}
              onChange={(e) => setKnowledgeMeta({ ...knowledgeMeta, source_url: e.target.value })}
              placeholder="https://..."
            />
          </label>
          <label>
            Knowledge file
            <input
              type="file"
              accept=".pdf,.txt,.md,.markdown,.csv,.tsv,.json"
              onChange={(e) => setKnowledgeFile(e.target.files?.[0] || null)}
            />
          </label>
          <Button disabled={!knowledgeFile || knowledgeBusy} onClick={() => void ingestKnowledge()}>
            <Database /> {knowledgeBusy ? 'Uploading…' : 'Ingest into RAG'}
          </Button>
        </Card>
        <Card
          title="Indexed knowledge"
          subtitle="Only published material participates in normal hybrid retrieval"
        >
          <div className="admin-user-list">
            {knowledge.length ? (
              knowledge.slice(0, 12).map((d: any) => (
                <div key={d.id}>
                  <span>
                    <b>{d.title}</b>
                    <small>
                      {d.authority} · Tier {d.authority_tier} · {d.crop || 'General'} · {d.language}
                      {d?.metadata?.total_chunks ? ` · ${d.metadata.total_chunks} chunks` : ''}
                    </small>
                  </span>
                  <Status tone={d.status === 'published' ? 'green' : 'amber'}>{d.status}</Status>
                  <Button variant="danger" onClick={() => void removeKnowledge(d.id)}>
                    <Trash2 /> Remove
                  </Button>
                </div>
              ))
            ) : (
              <Empty
                title="No RAG documents indexed"
                detail="Run the RAG migrations, then ingest a trusted agriculture document."
              />
            )}
          </div>
        </Card>
      </div>
      <Card
        title="RAG ingestion jobs"
        subtitle="Live progress refreshes every 2 seconds while a job is active"
      >
        <div className="rag-job-list">
          {ingestionJobs.length ? (
            ingestionJobs.slice(0, 12).map((j: any) => {
              const d = j.knowledge_documents || {};
              const stale =
                j.status === 'processing' &&
                j.heartbeat_at &&
                Date.now() - new Date(j.heartbeat_at).getTime() > 90000;
              return (
                <div className="rag-job" key={j.id}>
                  <div className="rag-job-head">
                    <span>
                      <b>{d.title || j.document_id}</b>
                      <small>
                        {j.id} · {stage(j.stage)}
                        {j.total_chunks ? ` · ${j.processed_chunks}/${j.total_chunks} chunks` : ''}
                        {j.total_batches ? ` · batch ${j.current_batch}/${j.total_batches}` : ''}
                      </small>
                    </span>
                    <Status
                      tone={
                        j.status === 'completed'
                          ? 'green'
                          : j.status === 'failed'
                            ? 'red'
                            : stale
                              ? 'orange'
                              : 'amber'
                      }
                    >
                      {stale ? 'stalled?' : j.status}
                    </Status>
                  </div>
                  <div className="rag-progress">
                    <i style={{ width: `${Math.max(0, Math.min(100, Number(j.progress_percent || 0)))}%` }} />
                  </div>
                  <div className="rag-job-meta">
                    <span>{Number(j.progress_percent || 0)}%</span>
                    {j.heartbeat_at && (
                      <span>Last activity {new Date(j.heartbeat_at).toLocaleTimeString()}</span>
                    )}
                    {j.error_message && <span className="rag-job-error">{j.error_message}</span>}
                  </div>
                  <div className="rag-job-actions">
                    {j.status === 'failed' && (
                      <Button variant="secondary" onClick={() => void retryIngestion(j.id)}>
                        <RefreshCcw /> Retry
                      </Button>
                    )}
                    {['queued', 'processing'].includes(j.status) && (
                      <Button variant="secondary" onClick={() => void cancelIngestion(j.id)}>
                        Cancel
                      </Button>
                    )}
                  </div>
                </div>
              );
            })
          ) : (
            <Empty
              title="No ingestion jobs yet"
              detail="Upload a trusted knowledge file to create a tracked ingestion job."
            />
          )}
        </div>
      </Card>
      <Card
        title="User access management"
        subtitle="Authentication identities live in Supabase Auth; MihiMura authorization and account status are enforced server-side"
      >
        <div className="admin-user-list">
          {users.length ? (
            users.map((u) => (
              <div key={u.uid}>
                <span>
                  <b>{u.name || u.email || u.uid}</b>
                  <small>
                    {u.email || 'no email'} · {u.role} · {u.district || 'region not set'} · {u.provider}
                  </small>
                </span>
                <Status tone={u.status === 'active' ? 'green' : u.status === 'suspended' ? 'red' : 'amber'}>
                  {u.status || 'active'}
                </Status>
                {u.provider === 'demo' ? (
                  <Button variant="secondary" disabled>
                    Demo identity
                  </Button>
                ) : u.status === 'suspended' ? (
                  <Button variant="secondary" onClick={() => void setStatus(u.uid, 'active')}>
                    Restore
                  </Button>
                ) : (
                  <Button variant="danger" onClick={() => void setStatus(u.uid, 'suspended')}>
                    Suspend
                  </Button>
                )}
              </div>
            ))
          ) : (
            <Empty
              title="No application profiles found"
              detail="Create or sign in with a Supabase user first."
            />
          )}
        </div>
      </Card>
      <Card
        title="Professional identity verification"
        subtitle="Professional workspaces are not unlocked by a self-declared role alone"
      >
        {professional.length ? (
          <div className="admin-user-list">
            {professional.map((u) => (
              <div key={u.uid}>
                <span>
                  <b>{u.name || u.email || u.uid}</b>
                  <small>
                    {u.role} · {u.district || 'region not set'} · {u.provider}
                  </small>
                </span>
                <Status tone={u.professional_verified ? 'green' : 'amber'}>
                  {u.professional_verified ? 'Verified' : 'Pending'}
                </Status>
                <Button variant="secondary" onClick={() => void verify(u.uid, !u.professional_verified)}>
                  {u.professional_verified ? 'Revoke' : 'Verify'}
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <Empty
            title="No professional verification requests"
            detail="New agronomist, supplier and analyst identities will appear here after onboarding."
          />
        )}
      </Card>
      <Card
        title="Recent multi-agent runs"
        subtitle="Provider, policy outcome, tool trace, latency and evidence are stored for explainability"
      >
        {runs.length ? (
          <div className="agent-run-admin-list">
            {runs.slice(0, 12).map((r: any) => (
              <div key={r.id}>
                <span>
                  <b>{r.request}</b>
                  <small>
                    {new Date(r.created_at).toLocaleString()} · {r.provider}
                    {r.model ? ` / ${r.model}` : ''}
                  </small>
                </span>
                <Status tone={r.policy_decision === 'confirmation-required' ? 'amber' : 'green'}>
                  {r.policy_decision || 'advisory'}
                </Status>
                <em>{Number(r.latency_ms || 0)} ms</em>
              </div>
            ))}
          </div>
        ) : (
          <Empty
            title="No agent run has been recorded yet"
            detail="Ask MihiMura a farm question to create a traceable agent-run receipt."
          />
        )}
      </Card>
      <Card
        title="Recent audit events"
        subtitle="Tool calls, confirmations, agent decisions and expert corrections should be immutable in production"
      >
        {audit.length ? (
          <div className="audit-table">
            {audit.slice(0, 20).map((a) => (
              <div key={a.id}>
                <time>{new Date(a.created_at).toLocaleString()}</time>
                <b>{a.action}</b>
                <span>{a.entity}</span>
                <code>{JSON.stringify(a.details).slice(0, 100)}</code>
              </div>
            ))}
          </div>
        ) : (
          <Empty title="No audit events yet" />
        )}
      </Card>
    </>
  );
}
