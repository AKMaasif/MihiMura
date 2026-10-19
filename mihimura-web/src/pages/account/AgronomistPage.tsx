import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, FileText, Stethoscope } from 'lucide-react';
import { Button, Card, Empty, Metric, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';

export function AgronomistPage() {
  const [cases, setCases] = useState<any[]>([]),
    [notice, setNotice] = useState('');
  const load = () =>
    platformApi
      .expertCases()
      .then(setCases)
      .catch((e) => setNotice(e.message));
  useEffect(() => {
    void load();
  }, []);
  const update = async (id: string, data: any) => {
    if (String(id).startsWith('case_demo')) {
      setNotice('Create a real expert case from the farmer portal to test expert actions.');
      return;
    }
    await platformApi.patchExpertCase(id, data);
    setNotice('Expert decision recorded separately from the original AI output.');
    await load();
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Stethoscope /> Expert triage & accountable correction
          </span>
          <h2>Agronomist Copilot</h2>
          <p>
            Experts receive structured evidence and can accept, correct, request more evidence or close cases.
            Expert decisions remain distinct from AI output.
          </p>
        </div>
      </section>
      {notice && (
        <Notice tone="info" title="Agronomist Copilot">
          {notice}
        </Notice>
      )}
      <div className="dashboard-metrics">
        <Metric
          label="Open cases"
          value={cases.filter((x) => x.status !== 'closed').length}
          icon={Stethoscope}
          tone="orange"
        />
        <Metric
          label="High urgency"
          value={cases.filter((x) => ['high', 'emergency'].includes(x.urgency)).length}
          icon={AlertTriangle}
          tone="orange"
        />
        <Metric
          label="Awaiting evidence"
          value={cases.filter((x) => x.status === 'needs-evidence').length}
          icon={FileText}
          tone="blue"
        />
        <Metric
          label="Expert corrections"
          value={cases.filter((x) => Boolean(x.expert_decision)).length}
          icon={Activity}
        />
      </div>
      <Card title="Expert triage queue" subtitle="Sorted by urgency, potential harm and evidence quality">
        {cases.length ? (
          <div className="expert-queue-list">
            {cases.map((c) => (
              <div key={c.id}>
                <div className="case-main">
                  <Status
                    tone={c.urgency === 'emergency' ? 'red' : c.urgency === 'high' ? 'orange' : 'amber'}
                  >
                    {c.urgency}
                  </Status>
                  <span>
                    <b>{c.reason}</b>
                    <p>{c.evidence}</p>
                    <small>
                      {c.farmer_name ? `${c.farmer_name} · ${c.farmer_district || ''} · ` : ''}
                      {c.project_id} · {new Date(c.created_at).toLocaleString()}
                    </small>
                  </span>
                </div>
                <div className="case-evidence">
                  <small>Evidence packet</small>
                  <span>Crop + stage</span>
                  <span>Images</span>
                  <span>Weather</span>
                  <span>Recent inputs</span>
                  <span>AI differential</span>
                </div>
                {c.expert_decision && (
                  <Notice tone="success" title="Expert decision">
                    {c.expert_decision}
                  </Notice>
                )}
                <div className="case-actions">
                  <Button onClick={() => void update(c.id, { status: 'accepted' })}>Accept case</Button>
                  <Button
                    variant="secondary"
                    onClick={() =>
                      void update(c.id, {
                        status: 'needs-evidence',
                        expert_decision:
                          'Please provide clearer guided images and the latest field observation.',
                      })
                    }
                  >
                    Request evidence
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      const text = window.prompt(
                        'Record the expert correction or modified plan. It will remain separate from AI output.',
                      );
                      if (text) void update(c.id, { status: 'expert-reviewed', expert_decision: text });
                    }}
                  >
                    Correct / modify plan
                  </Button>
                  <Button variant="secondary" onClick={() => void update(c.id, { status: 'closed' })}>
                    Close
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty
            title="No expert case in the queue"
            detail="Farmer escalations will appear here with their evidence packages."
          />
        )}
      </Card>
    </>
  );
}
