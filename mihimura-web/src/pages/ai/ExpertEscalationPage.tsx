import { useEffect, useState } from 'react';
import { ShieldCheck, Stethoscope } from 'lucide-react';
import { Button, Card, Empty, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { useAuth } from '../../context/AuthContext';

export function ExpertEscalationPage() {
  const { profile } = useAuth();
  const [cases, setCases] = useState<any[]>([]),
    [projects, setProjects] = useState<any[]>([]),
    [projectId, setProjectId] = useState(''),
    [reason, setReason] = useState('Low-confidence crop symptom assessment'),
    [urgency, setUrgency] = useState('medium'),
    [notice, setNotice] = useState('');
  const load = async () => {
    const r = await Promise.allSettled([platformApi.expertCases(), platformApi.projects()]);
    if (r[0].status === 'fulfilled') setCases(r[0].value);
    if (r[1].status === 'fulfilled') {
      setProjects(r[1].value);
      if (!projectId && r[1].value[0]) setProjectId(r[1].value[0].id);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const submit = async () => {
    if (!projectId) {
      setNotice('Create or select a project before sending an expert case.');
      return;
    }
    await platformApi.addExpertCase({
      project_id: projectId,
      urgency,
      reason,
      evidence: 'Digital twin history + recent weather + current AI recommendation + available crop scans',
      preferred_language: profile?.language || 'English',
      availability: 'Weekdays 09:00–17:00',
    });
    setNotice('Expert case created with a structured evidence packet.');
    await load();
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Stethoscope /> Human-in-the-loop safety
          </span>
          <h2>Expert escalation</h2>
          <p>
            Use a qualified agricultural instructor or agronomist when uncertainty, hazard, conflict or
            repeated deterioration crosses the escalation threshold.
          </p>
        </div>
      </section>
      {notice && (
        <Notice tone="info" title="Expert network">
          {notice}
        </Notice>
      )}
      <div className="two-col">
        <Card
          title="Create an evidence-backed case"
          subtitle="MihiMura packages context so the expert does not start from zero"
        >
          <label>
            Project
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">Select a project</option>
              {projects.map((p) => (
                <option value={p.id} key={p.id}>
                  {p.farm_name} · {p.crop}
                </option>
              ))}
            </select>
          </label>
          <label>
            Reason
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <label>
            Urgency
            <select value={urgency} onChange={(e) => setUrgency(e.target.value)}>
              <option>low</option>
              <option>medium</option>
              <option>high</option>
              <option>emergency</option>
            </select>
          </label>
          <div className="evidence-package">
            <b>Evidence package includes</b>
            <span>Project crop + stage</span>
            <span>Recent tasks and inputs</span>
            <span>Weather context</span>
            <span>AI differential / confidence</span>
            <span>Farmer observations</span>
          </div>
          <Button disabled={!projectId} onClick={() => void submit()}>
            <Stethoscope /> Submit expert case
          </Button>
        </Card>
        <Card title="Your cases" subtitle="Expert decisions are stored separately from AI output">
          {cases.length ? (
            <div className="case-list">
              {cases.map((c) => (
                <div key={c.id}>
                  <div>
                    <Status
                      tone={c.urgency === 'emergency' ? 'red' : c.urgency === 'high' ? 'orange' : 'amber'}
                    >
                      {c.urgency}
                    </Status>
                    <b>{c.reason}</b>
                    <p>{c.evidence}</p>
                    <small>{new Date(c.created_at).toLocaleString()}</small>
                  </div>
                  <Status tone={c.status === 'closed' ? 'green' : 'blue'}>{c.status}</Status>
                </div>
              ))}
            </div>
          ) : (
            <Empty title="No open expert case" />
          )}
        </Card>
      </div>
      <Card title="Automatic escalation thresholds">
        <div className="threshold-grid">
          {[
            'Low diagnosis confidence or multiple serious possibilities',
            'Restricted / hazardous treatment question',
            'Potential regional outbreak or quarantine concern',
            'Official emergency alert',
            'Conflicting authoritative sources',
            'Repeated deterioration despite completed interventions',
            'Large-value or unusual order quantity',
            'Farmer requests certified opinion or visit',
          ].map((x) => (
            <div key={x}>
              <ShieldCheck />
              <span>{x}</span>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}
