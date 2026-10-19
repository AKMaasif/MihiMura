import { useEffect, useState } from 'react';
import { AlertTriangle, Droplets, Globe2, ShieldCheck, Sprout, Stethoscope, Users } from 'lucide-react';
import { Card, Empty, Metric, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';

export function GovernmentPage() {
  const [dashboard, setDashboard] = useState<any>(null),
    [community, setCommunity] = useState<any[]>([]);
  useEffect(() => {
    Promise.allSettled([platformApi.dashboard(), platformApi.community()]).then((r) => {
      if (r[0].status === 'fulfilled') setDashboard(r[0].value);
      if (r[1].status === 'fulfilled') setCommunity(r[1].value);
    });
  }, []);
  const provinces = Object.values(dashboard?.provinces || {}) as any[];
  const action = provinces.filter((p: any) => p.healthScore < 60).length;
  const monitored = provinces.reduce((sum: number, p: any) => sum + Number(p.atRiskArea || 0), 0);
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Globe2 /> Privacy-preserving regional intelligence
          </span>
          <h2>Government / NGO analytics</h2>
          <p>
            Regional planning uses aggregated trends and suppresses exact farmer identity, individual
            boundaries and small cell counts.
          </p>
        </div>
      </section>
      <div className="dashboard-metrics">
        <Metric
          label="At-risk area proxy"
          value={`${monitored.toLocaleString()} ac`}
          note="9-province demonstration layer"
          icon={Sprout}
        />
        <Metric
          label="Provinces at action level"
          value={action}
          note="health score below 60"
          icon={AlertTriangle}
          tone="orange"
        />
        <Metric
          label="Community clusters"
          value={community.length}
          note="only threshold-qualified clusters"
          icon={Users}
        />
        <Metric
          label="Critical threats"
          value={dashboard?.summary?.criticalThreats ?? '—'}
          note="national risk queue"
          icon={Droplets}
          tone="blue"
        />
        <Metric
          label="Provinces needing action"
          value={dashboard?.summary ? `${dashboard.summary.provincesNeedingAction ?? 0} / 9` : '—'}
          note={dashboard?.live ? 'live crop condition index below 60' : 'baseline values'}
          icon={Stethoscope}
          tone="purple"
        />
      </div>
      <div className="two-col">
        <Card
          title="Regional program signals"
          subtitle="Operational layer — not a substitute for official statistics"
        >
          <div className="gov-table">
            {provinces
              .sort((a: any, b: any) => a.healthScore - b.healthScore)
              .slice(0, 5)
              .map((p: any) => (
                <div key={p.name}>
                  <b>{p.name}</b>
                  <span>{p.nextAction}</span>
                  <Status tone={p.healthScore < 45 ? 'red' : p.healthScore < 60 ? 'orange' : 'amber'}>
                    {p.healthScore < 45 ? 'High' : p.healthScore < 60 ? 'Action' : 'Watch'}
                  </Status>
                  <strong>{p.atRiskArea} ac</strong>
                </div>
              ))}
          </div>
        </Card>
        <Card title="Community Sentinel evidence">
          <div className="source-status-list">
            {community.length ? (
              community.map((c: any) => (
                <div key={`${c.district}-${c.crop}-${c.report_type}`}>
                  <i className="live" />
                  <span>
                    <b>
                      {c.district} · {c.crop}
                    </b>
                    <small>
                      {c.report_type} · latest {new Date(c.created_at).toLocaleString()}
                    </small>
                  </span>
                  <em>{c.report_count} reports</em>
                </div>
              ))
            ) : (
              <Empty
                title="No publishable community cluster"
                detail="Individual reports remain private until the minimum threshold is reached."
              />
            )}
          </div>
        </Card>
      </div>
      <Card title="Privacy controls">
        <div className="threshold-grid">
          {[
            'Suppress small regional counts',
            'Remove personal identifiers',
            'Never expose exact farm boundaries',
            'Separate farmer consent from program analytics',
            'Audit exports and analyst access',
            'Show source freshness and reporting period',
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
