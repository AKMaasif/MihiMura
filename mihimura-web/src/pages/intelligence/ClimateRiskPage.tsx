import { useEffect, useState } from 'react';
import { CloudRain, Radar, ShieldAlert, ThermometerSun, Users, Wind } from 'lucide-react';
import { Card, Notice, Status, Button } from '../../components/common/UI';
import { useNavigate } from 'react-router-dom';
import { platformApi } from '../../services/platformApi';

export function ClimateRiskPage() {
  const nav = useNavigate();
  const [ack, setAck] = useState(false),
    [projects, setProjects] = useState<any[]>([]),
    [notice, setNotice] = useState('');
  useEffect(() => {
    platformApi
      .projects()
      .then(setProjects)
      .catch(() => {});
  }, []);
  const risks = [
    {
      icon: CloudRain,
      title: 'Flood / runoff',
      score: 76,
      level: 'Action',
      uncertainty: '72–88%',
      timing: 'Next 24–36h',
      why: 'Heavy rain + local drainage exposure',
      task: 'Prepare drainage and inspect runoff paths',
    },
    {
      icon: Users,
      title: 'Pest pressure',
      score: 69,
      level: 'Watch',
      uncertainty: '61–78%',
      timing: 'Next 3–5 days',
      why: 'Humidity + privacy-thresholded local reports',
      task: 'Inspect representative plants and monitoring traps',
    },
    {
      icon: ThermometerSun,
      title: 'Heat stress',
      score: 52,
      level: 'Watch',
      uncertainty: '45–64%',
      timing: 'Next 48h',
      why: 'Sensitive crop-stage periods',
      task: 'Review heat-sensitive field operations',
    },
    {
      icon: Wind,
      title: 'Wind exposure',
      score: 31,
      level: 'Low',
      uncertainty: '22–40%',
      timing: 'Next 24h',
      why: 'No material threshold crossed',
      task: 'Continue routine wind monitoring',
    },
  ];
  const makeTask = async (r: any) => {
    if (!projects[0]) {
      setNotice('Create a cultivation project before turning a risk into a mitigation task.');
      return;
    }
    await platformApi.addTask({
      project_id: projects[0].id,
      title: r.task,
      task_type: 'Climate mitigation',
      due_at: new Date(Date.now() + 24 * 3600e3).toISOString(),
      priority: r.level === 'Action' ? 'high' : 'medium',
      weather_dependency: `${r.title}: ${r.timing}; re-check current official/live sources`,
      instructions: `${r.why}. This task is a precaution, not a chemical prescription.`,
      schedule_reason: 'Created from Climate & Disaster Risk Centre after farmer action',
    });
    setNotice(`Mitigation task created for ${projects[0].farm_name}.`);
    nav('/app/tasks');
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Radar /> Predictive + authoritative risk
          </span>
          <h2>Climate & disaster risk centre</h2>
          <p>
            Material risks are translated into crop-specific preparations with probability, timing,
            uncertainty and source precedence.
          </p>
        </div>
      </section>
      {notice && (
        <Notice tone="info" title="Risk centre">
          {notice}
        </Notice>
      )}
      <div className={`official-alert ${ack ? 'ack' : ''}`}>
        <ShieldAlert />
        <div>
          <span>DEMO OFFICIAL-ADVISORY OVERLAY</span>
          <h3>Heavy rainfall conditions may affect Eastern Province field operations</h3>
          <p>
            Valid for the next 24–36 hours. Confirm with the current Sri Lanka Department of Meteorology / DMC
            publication before emergency action.
          </p>
        </div>
        <div>
          <Status tone="orange">Action</Status>
          <Button variant="secondary" onClick={() => setAck(true)}>
            {ack ? 'Acknowledged' : 'Acknowledge'}
          </Button>
        </div>
      </div>
      <div className="risk-cards">
        {risks.map((r) => {
          const I = r.icon;
          return (
            <Card key={r.title} className="risk-detail">
              <div className="risk-detail-top">
                <span>
                  <I />
                </span>
                <div>
                  <small>{r.title}</small>
                  <strong>{r.score}/100</strong>
                </div>
                <Status tone={r.level === 'Action' ? 'orange' : r.level === 'Watch' ? 'amber' : 'green'}>
                  {r.level}
                </Status>
              </div>
              <dl>
                <div>
                  <dt>Probability / uncertainty</dt>
                  <dd>{r.uncertainty}</dd>
                </div>
                <div>
                  <dt>Expected timing</dt>
                  <dd>{r.timing}</dd>
                </div>
                <div>
                  <dt>Why it matters</dt>
                  <dd>{r.why}</dd>
                </div>
              </dl>
              <Button variant="secondary" onClick={() => void makeTask(r)}>
                Create mitigation task
              </Button>
            </Card>
          );
        })}
      </div>
      <Card
        title="Risk communication rule"
        subtitle="The visual state changes with decision urgency—not just model score"
      >
        <div className="risk-level-grid">
          {[
            ['Green', 'Low', 'Routine monitoring', 'green'],
            ['Amber', 'Watch', 'Prepare and monitor', 'amber'],
            ['Orange', 'Action', 'Priority checklist + confirmation', 'orange'],
            ['Red', 'Emergency', 'Persistent warning + human escalation', 'red'],
          ].map(([a, b, c, d]: any) => (
            <div key={a} className={d}>
              <i />
              <b>
                {a} · {b}
              </b>
              <p>{c}</p>
            </div>
          ))}
        </div>
        <Notice tone="warning" title="Conflict resolution">
          Official emergency warnings override routine forecasts. Verified crop protocols override
          unconstrained model suggestions. Unresolved authoritative conflicts should be escalated.
        </Notice>
      </Card>
    </>
  );
}
