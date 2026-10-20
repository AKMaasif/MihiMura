import { useEffect, useState } from 'react';
import { AlertTriangle, CloudRain, Globe2, ThermometerSun, Waves } from 'lucide-react';
import { Card, Notice, Status, Button } from '../../components/common/UI';
import { useNavigate } from 'react-router-dom';
import { platformApi } from '../../services/platformApi';
import { SriLankaProvinceMap } from '../../components/dashboard/SriLankaProvinceMap';
import { situationLabel, useProvinceSituation } from '../../hooks/useProvinceSituation';

export function DisasterMapPage() {
  const nav = useNavigate();
  const situation = useProvinceSituation();
  const provinceData = situation.provinces;
  const [selected, setSelected] = useState('Eastern'),
    [projects, setProjects] = useState<any[]>([]),
    [notice, setNotice] = useState('');
  useEffect(() => {
    platformApi
      .projects()
      .then(setProjects)
      .catch(() => {});
  }, []);
  const current = provinceData[selected];
  const score = (value?: number | null) => (value === null || value === undefined ? '—' : `${value}/100`);
  // Hill-country provinces are landslide-prone; heavy forecast rain raises the level.
  const hilly = ['Central', 'Sabaragamuwa', 'Uva'].includes(selected);
  const landslide = !hilly
    ? 'Low'
    : current.rainfallRisk >= 70
      ? 'High'
      : current.rainfallRisk >= 45
        ? 'Watch'
        : 'Low';
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
      priority: current.rainfallRisk > 70 ? 'high' : 'medium',
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
      <Card
        title="Sri Lanka hazard overview"
        subtitle={
          situation.live
            ? 'Select a province to inspect current exposure from live forecast data'
            : 'Live data unavailable — showing baseline reference values'
        }
      >
        <div className="national-map-grid">
          <SriLankaProvinceMap
            selectedProvince={selected}
            activeLayer="rainfallRisk"
            provinces={provinceData}
            onSelectProvince={setSelected}
            sourceNote={situationLabel(situation)}
          />
          <div className="province-side">
            <Status tone="orange">{selected} Province</Status>
            <h2>{current.rainfallRisk}/100</h2>
            <p>Rainfall / runoff exposure proxy</p>
            <div className="risk-mini-list">
              <div>
                <CloudRain />
                <span>
                  <small>Flood / runoff</small>
                  <b>{current.rainfallRisk}/100</b>
                </span>
              </div>
              <div>
                <ThermometerSun />
                <span>
                  <small>Heat</small>
                  <b>{score(current.heatStress)}</b>
                </span>
              </div>
              <div>
                <Waves />
                <span>
                  <small>Drought / water stress</small>
                  <b>{score(current.waterStress)}</b>
                </span>
              </div>
              <div>
                <AlertTriangle />
                <span>
                  <small>Landslide / slope</small>
                  <b>{landslide}</b>
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
