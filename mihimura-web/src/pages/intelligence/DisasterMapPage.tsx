import { useEffect, useState } from 'react';
import { AlertTriangle, CloudRain, Globe2, ThermometerSun, Waves } from 'lucide-react';
import { Card, Notice, Status, Button } from '../../components/common/UI';
import { useNavigate } from 'react-router-dom';
import { platformApi } from '../../services/platformApi';
import { SriLankaProvinceMap } from '../../components/dashboard/SriLankaProvinceMap';
import { provinceData } from '../../data/mockApi';

export function DisasterMapPage() {
  const nav = useNavigate();
  const [selected, setSelected] = useState('Eastern'),
    [projects, setProjects] = useState<any[]>([]),
    [notice, setNotice] = useState('');
  useEffect(() => {
    platformApi
      .projects()
      .then(setProjects)
      .catch(() => {});
  }, []);
  const create = async () => {
    const p = projects.find((x) => x.province === selected) || projects[0];
    if (!p) {
      setNotice('Create a cultivation project before creating a mitigation checklist.');
      return;
    }
    await platformApi.addTask({
      project_id: p.id,
      title: `Review ${selected} rainfall/runoff exposure`,
      task_type: 'Disaster preparation',
      due_at: new Date(Date.now() + 12 * 3600e3).toISOString(),
      priority: provinceData[selected].rainfallRisk > 70 ? 'high' : 'medium',
      weather_dependency: 'Verify current official warning and live forecast',
      instructions:
        'Inspect drainage, access routes and vulnerable crop-stage operations. Escalate emergency warnings to official guidance.',
      schedule_reason: 'Created from national disaster exposure map',
    });
    nav('/app/tasks');
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Globe2 /> Hazard spatial context
          </span>
          <h2>National disaster exposure map</h2>
          <p>
            Province-level exposure is separated from exact farm boundaries for privacy. Official warnings
            take precedence over predictive layers.
          </p>
        </div>
      </section>
      {notice && (
        <Notice tone="info" title="Disaster map">
          {notice}
        </Notice>
      )}
      <Card title="Sri Lanka hazard overview" subtitle="Select a province to inspect current demo exposure">
        <div className="national-map-grid">
          <SriLankaProvinceMap
            selectedProvince={selected}
            activeLayer="rainfallRisk"
            provinces={provinceData}
            onSelectProvince={setSelected}
          />
          <div className="province-side">
            <Status tone="orange">{selected} Province</Status>
            <h2>{provinceData[selected].rainfallRisk}/100</h2>
            <p>Rainfall / runoff exposure proxy</p>
            <div className="risk-mini-list">
              <div>
                <CloudRain />
                <span>
                  <small>Flood / runoff</small>
                  <b>{provinceData[selected].rainfallRisk}/100</b>
                </span>
              </div>
              <div>
                <ThermometerSun />
                <span>
                  <small>Heat</small>
                  <b>52/100</b>
                </span>
              </div>
              <div>
                <Waves />
                <span>
                  <small>Drought proxy</small>
                  <b>{Math.max(18, 100 - provinceData[selected].rainfallRisk)}/100</b>
                </span>
              </div>
              <div>
                <AlertTriangle />
                <span>
                  <small>Landslide / slope</small>
                  <b>{['Central', 'Sabaragamuwa', 'Uva'].includes(selected) ? 'Watch' : 'Low'}</b>
                </span>
              </div>
            </div>
            <Button onClick={() => void create()}>Create local mitigation checklist</Button>
          </div>
        </div>
      </Card>
    </>
  );
}
