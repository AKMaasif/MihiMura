import { useEffect, useState } from 'react';
import { Save, Wheat } from 'lucide-react';
import { Button, Card, Empty } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { ProjectSelector } from './ProjectSelector';

export function HarvestPage() {
  const [items, setItems] = useState<any[]>([]),
    [projects, setProjects] = useState<any[]>([]),
    [projectId, setProjectId] = useState(''),
    [yieldValue, setYield] = useState(0),
    [revenue, setRevenue] = useState(0),
    [quality, setQuality] = useState('Farmer recorded'),
    [date, setDate] = useState(new Date().toISOString().slice(0, 10)),
    [capsule, setCapsule] = useState('');
  const load = async () => {
    const r = await Promise.allSettled([platformApi.harvests(), platformApi.projects()]);
    if (r[0].status === 'fulfilled') setItems(r[0].value);
    if (r[1].status === 'fulfilled') {
      setProjects(r[1].value);
      if (!projectId && r[1].value[0]) setProjectId(r[1].value[0].id);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const add = async () => {
    if (!projectId) return;
    await platformApi.addHarvest({
      project_id: projectId,
      harvest_date: date,
      yield_value: yieldValue,
      yield_unit: 'kg',
      quality,
      revenue,
      note: 'Season review record',
    });
    await load();
  };
  const generateCapsule = () => {
    const p = projects.find((x) => x.id === projectId);
    const h = items.filter((x) => x.project_id === projectId);
    setCapsule(
      `${p?.crop || 'This crop'} on ${p?.farm_name || 'the selected farm'} has ${h.length} recorded harvest event(s). Preserve successful weather-aware timings, task outcomes, water records and expert corrections as the starting context for the next season.`,
    );
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Wheat /> Close the learning loop
          </span>
          <h2>Harvest & season review</h2>
          <p>
            Yield, revenue, task adherence, water use and risk events become next-season memory—not just a
            final number.
          </p>
        </div>
      </section>
      <div className="two-col">
        <Card title="Record harvest">
          <div className="field-grid">
            <ProjectSelector projects={projects} value={projectId} onChange={setProjectId} />
            <label>
              Yield (kg)
              <input
                type="number"
                min="0"
                value={yieldValue}
                onChange={(e) => setYield(Number(e.target.value))}
              />
            </label>
            <label>
              Revenue (LKR)
              <input
                type="number"
                min="0"
                value={revenue}
                onChange={(e) => setRevenue(Number(e.target.value))}
              />
            </label>
            <label>
              Quality
              <select value={quality} onChange={(e) => setQuality(e.target.value)}>
                <option>Farmer recorded</option>
                <option>Grade A</option>
                <option>Grade B</option>
                <option>Mixed</option>
              </select>
            </label>
            <label>
              Harvest date
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </label>
          </div>
          <Button disabled={!projectId || yieldValue <= 0} onClick={() => void add()}>
            <Save /> Record season outcome
          </Button>
        </Card>
        <Card title="Farm Knowledge Time Capsule">
          <div className="time-capsule">
            <Wheat />
            <h3>Season memory summary</h3>
            <p>
              {capsule ||
                'Generate a concise season memory from the selected digital twin. In production, MihiMura can translate and narrate this summary for the next season or next generation.'}
            </p>
            <Button variant="secondary" disabled={!projectId} onClick={generateCapsule}>
              Generate preview
            </Button>
          </div>
        </Card>
      </div>
      <Card title="Recorded harvests">
        {items.length ? (
          <div className="harvest-list">
            {items.map((x) => (
              <div key={x.id}>
                <Wheat />
                <span>
                  <b>
                    {x.yield_value} {x.yield_unit}
                  </b>
                  <small>
                    {x.harvest_date} · {x.quality}
                  </small>
                </span>
                <strong>LKR {Number(x.revenue).toLocaleString()}</strong>
              </div>
            ))}
          </div>
        ) : (
          <Empty title="No harvest record yet" detail="Use this page at maturity and season review." />
        )}
      </Card>
    </>
  );
}
