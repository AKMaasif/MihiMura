import { useEffect, useState } from 'react';
import { Database, Satellite } from 'lucide-react';
import { Card, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { useAuth } from '../../context/AuthContext';

export function SatellitePage() {
  const { profile } = useAuth();
  const [data, setData] = useState<any>(null),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    platformApi
      .satellite(profile?.lat || 7.291, profile?.lon || 81.674)
      .then(setData)
      .finally(() => setLoading(false));
  }, []);
  const trend = data?.ndviTrend || [0.62, 0.61, 0.6, 0.58, 0.55, 0.53, 0.51];
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Satellite /> Remote-sensing evidence
          </span>
          <h2>Satellite intelligence</h2>
          <p>
            Optical vegetation indicators are proxies, not diagnoses. Cloud cover, revisit date and processing
            version remain visible.
          </p>
        </div>
        <Status tone={data?.configured ? 'green' : 'amber'}>
          {data?.configured ? 'Copernicus connected' : 'Demo Sentinel snapshot'}
        </Status>
      </section>
      <div className="two-col">
        <Card title="Vegetation condition trend" subtitle="Sentinel-2 example · selected field">
          <div className="ndvi-chart">
            <div className="chart-axis">
              <span>0.8</span>
              <span>0.6</span>
              <span>0.4</span>
              <span>0.2</span>
            </div>
            <div className="chart-bars">
              {trend.map((v: number, i: number) => (
                <div key={i}>
                  <i style={{ height: `${v * 100}%` }} />
                  <small>{['-30d', '-25d', '-20d', '-15d', '-10d', '-5d', 'Now'][i] || i}</small>
                </div>
              ))}
            </div>
          </div>
          <Notice tone="warning" title="Interpretation">
            A declining NDVI-like proxy can reflect crop stage, soil background, management or stress. It
            should trigger field verification—not automatic treatment.
          </Notice>
        </Card>
        <Card
          title="Available scenes"
          subtitle="Cloud cover determines whether optical interpretation is useful"
        >
          {loading ? (
            <div className="page-loading">Checking Sentinel catalogue…</div>
          ) : (
            <div className="scene-list">
              {(data?.scenes || []).map((s: any, i: number) => (
                <div key={s.id || i}>
                  <Satellite />
                  <span>
                    <b>{s.date?.slice?.(0, 10) || s.date}</b>
                    <small>Sentinel-2 L2A</small>
                  </span>
                  <Status tone={(s.cloudCover ?? 20) < 15 ? 'green' : 'amber'}>
                    {s.cloudCover ?? '—'}% cloud
                  </Status>
                </div>
              ))}
            </div>
          )}
          <div className="source-card">
            <Database />
            <div>
              <b>{data?.source || 'Sentinel-2 demo snapshot'}</b>
              <p>
                {data?.configured
                  ? 'Authenticated using backend OAuth client credentials.'
                  : 'Add Sentinel Hub client credentials to enable live catalogue queries.'}
              </p>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}
