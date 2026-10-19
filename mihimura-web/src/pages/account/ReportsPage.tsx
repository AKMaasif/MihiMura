import { useEffect, useState } from 'react';
import {
  Activity,
  BarChart3,
  CheckCircle2,
  Download,
  Droplets,
  FileDown,
  FileText,
  Waves,
  Wheat,
} from 'lucide-react';
import { Button, Card, Metric, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { download } from './download';

export function ReportsPage() {
  const [tasks, setTasks] = useState<any[]>([]),
    [expenses, setExpenses] = useState<any[]>([]),
    [harvests, setHarvests] = useState<any[]>([]),
    [aiReports, setAiReports] = useState<any[]>([]);
  useEffect(() => {
    Promise.allSettled([
      platformApi.tasks(),
      platformApi.expenses(),
      platformApi.harvests(),
      platformApi.reports(),
    ]).then((r) => {
      if (r[0].status === 'fulfilled') setTasks(r[0].value);
      if (r[1].status === 'fulfilled') setExpenses(r[1].value);
      if (r[2].status === 'fulfilled') setHarvests(r[2].value);
      if (r[3].status === 'fulfilled') setAiReports(r[3].value);
    });
  }, []);
  const completion = tasks.length
    ? Math.round((tasks.filter((x) => x.status === 'completed').length / tasks.length) * 100)
    : 76;
  const cost = expenses.reduce((s, x) => s + Number(x.amount || 0), 0);
  const exportCsv = () =>
    download(
      'mihimura-impact-report.csv',
      [
        ['Metric', 'Value'],
        ['Task adherence', `${completion}%`],
        ['Recorded costs', cost],
        ['Water saved estimate', '23400 L'],
        ['Early warning lead time', '18 hours'],
        ['Estimated loss avoided', '18500 LKR'],
      ]
        .map((x) => x.join(','))
        .join('\n'),
      'text/csv',
    );
  const openReport = (r: any) => {
    if (r?.download_url) window.open(r.download_url, '_blank', 'noopener,noreferrer');
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <BarChart3 /> Outcome & sustainability intelligence
          </span>
          <h2>Reports and impact</h2>
          <p>
            Track generated cultivation reports, yield, input use, water, costs, risk events, interventions
            and SDG-aligned outcomes without overstating causal impact.
          </p>
        </div>
        <Button onClick={exportCsv}>
          <FileDown /> Export CSV
        </Button>
      </section>
      {aiReports.length > 0 && (
        <Card
          title="AI cultivation reports"
          subtitle="Conversation-grounded PDF plans stored privately in Supabase Storage"
        >
          <div className="ai-report-history">
            {aiReports.map((r: any) => (
              <div key={r.id}>
                <FileText />
                <span>
                  <b>{r.title || 'MihiMura cultivation report'}</b>
                  <small>
                    {r.created_at ? new Date(r.created_at).toLocaleString() : 'Generated report'} ·{' '}
                    {String(r.report_type || 'cultivation plan').replaceAll('_', ' ')}
                  </small>
                  <p>{r.summary || 'Evidence-grounded cultivation planning report.'}</p>
                </span>
                <Status tone={r.status === 'ready' ? 'green' : 'amber'}>{r.status || 'ready'}</Status>
                <Button variant="secondary" disabled={!r.download_url} onClick={() => openReport(r)}>
                  <Download /> Open PDF
                </Button>
              </div>
            ))}
          </div>
        </Card>
      )}
      <div className="dashboard-metrics">
        <Metric
          label="Task adherence"
          value={`${completion}%`}
          note="Completed / recorded tasks"
          icon={CheckCircle2}
        />
        <Metric
          label="Water saved"
          value="23,400 L"
          note="Demo intervention estimate"
          icon={Droplets}
          tone="blue"
        />
        <Metric
          label="Input waste avoided"
          value="LKR 18,500"
          note="Demo fertilizer timing scenario"
          icon={Waves}
          tone="orange"
        />
        <Metric label="Early warning lead" value="18 h" note="Before exposed operation" icon={Activity} />
        <Metric
          label="Recorded costs"
          value={`LKR ${cost.toLocaleString()}`}
          note="Field diary + expense records"
          icon={FileText}
          tone="purple"
        />
      </div>
      <div className="two-col">
        <Card
          title="Intervention effectiveness"
          subtitle="Outcome tracking should compare recommendations with actual field results"
        >
          <div className="bar-chart">
            {[
              ['Weather-aware rescheduling', 94],
              ['Drainage preparation', 88],
              ['Field scouting', 79],
              ['Irrigation timing', 84],
            ].map((x) => (
              <label key={x[0] as string}>
                <span>{x[0]}</span>
                <b>{x[1]}%</b>
                <i>
                  <em style={{ width: `${x[1]}%` }} />
                </i>
              </label>
            ))}
          </div>
          <Notice tone="info" title="Evaluation discipline">
            Hackathon values are demonstrations, not causal evidence. A real pilot should track false alerts,
            expert corrections, task adherence, input use, water use, farmer comprehension and yield.
          </Notice>
        </Card>
        <Card title="MihiMura Resilience Passport">
          <div className="passport-large">
            <div>
              <strong>74</strong>
              <span>/100</span>
              <Status tone="green">Improving</Status>
            </div>
            <p>A seasonal improvement score grounded in field actions.</p>
          </div>
          <div className="passport-list">
            <span>
              Water efficiency <b>78</b>
            </span>
            <span>
              Soil protection <b>71</b>
            </span>
            <span>
              Climate exposure management <b>69</b>
            </span>
            <span>
              Task adherence <b>82</b>
            </span>
            <span>
              Recovery after risk event <b>70</b>
            </span>
          </div>
        </Card>
      </div>
      <Card title="SDG impact panel">
        <div className="sdg-report-grid">
          <div>
            <i>2</i>
            <span>
              <b>Zero Hunger</b>
              <p>Yield retained · early detection · smallholder reach</p>
            </span>
          </div>
          <div>
            <i>13</i>
            <span>
              <b>Climate Action</b>
              <p>Warning lead time · water saved · preparedness</p>
            </span>
          </div>
          <div>
            <i>15</i>
            <span>
              <b>Life on Land</b>
              <p>Input reduction · soil protection · biodiversity-safe checks</p>
            </span>
          </div>
        </div>
      </Card>
      {harvests.length > 0 && (
        <Card title="Season outcomes">
          <div className="harvest-list">
            {harvests.map((h) => (
              <div key={h.id}>
                <Wheat />
                <span>
                  <b>
                    {h.yield_value} {h.yield_unit}
                  </b>
                  <small>{h.harvest_date}</small>
                </span>
                <strong>LKR {Number(h.revenue).toLocaleString()}</strong>
              </div>
            ))}
          </div>
        </Card>
      )}
    </>
  );
}
