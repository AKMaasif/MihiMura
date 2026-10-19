import { useEffect, useState } from 'react';
import { ArrowRight, Plus, Sprout, Wheat } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Empty, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { defaultProjectForm, projectProgress, stageOrder } from './farmShared';

export function ProjectsPage() {
  const nav = useNavigate();
  const [projects, setProjects] = useState<any[]>([]),
    [farms, setFarms] = useState<any[]>([]),
    [create, setCreate] = useState(false),
    [form, setForm] = useState<any>(defaultProjectForm),
    [notice, setNotice] = useState('');
  const load = async () => {
    const [projectsResult, farmsResult] = await Promise.allSettled([
      platformApi.projects(),
      platformApi.farms(),
    ]);

    if (projectsResult.status === 'fulfilled') {
      setProjects(projectsResult.value);
    }

    if (farmsResult.status === 'fulfilled') {
      const farmList = farmsResult.value as any[];

      setFarms(farmList);

      setForm((x: any) => ({
        ...x,
        farm_id: x.farm_id || farmList[0]?.id || '',
      }));
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const add = async () => {
    if (!form.farm_id || !form.crop) {
      setNotice('Select a farm and crop first.');
      return;
    }
    await platformApi.addProject(form);
    setCreate(false);
    setForm({ ...defaultProjectForm, farm_id: farms[0]?.id || '' });
    await load();
    setNotice('Digital twin created. Add tasks and field evidence as cultivation progresses.');
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Wheat /> Crop-specific digital twins
          </span>
          <h2>Cultivation projects</h2>
          <p>
            Projects carry crop variety, season, timeline, water context, costs, tasks, images, interventions
            and outcomes from planning through season review.
          </p>
        </div>
        <Button disabled={!farms.length} onClick={() => setCreate(true)}>
          <Plus /> Create project
        </Button>
      </section>
      {notice && (
        <Notice tone="info" title="Cultivation projects">
          {notice}
        </Notice>
      )}
      {!farms.length && (
        <Notice tone="warning" title="A farm is required first">
          Create a farm before starting a crop-specific digital twin.
        </Notice>
      )}
      {projects.length ? (
        <div className="project-grid">
          {projects.map((p) => (
            <article key={p.id} className="project-card">
              <div className="project-visual">
                <Sprout />
                <span>{p.crop}</span>
              </div>
              <div className="project-body">
                <div>
                  <Status
                    tone={(p.risk_score || 0) > 70 ? 'red' : (p.risk_score || 0) > 50 ? 'orange' : 'green'}
                  >
                    {p.risk_score ?? 0} risk
                  </Status>
                  <small>
                    {p.season || 'Season not set'} · {p.status}
                  </small>
                </div>
                <h3>
                  {p.crop} · {p.variety || 'Variety not set'}
                </h3>
                <p>{p.farm_name || p.farm_id}</p>
                <div className="project-scores">
                  <span>
                    <small>Health</small>
                    <b>{p.health_score ?? '—'}/100</b>
                  </span>
                  <span>
                    <small>Stage</small>
                    <b>{p.stage}</b>
                  </span>
                  <span>
                    <small>Target harvest</small>
                    <b>{p.target_harvest || 'Not set'}</b>
                  </span>
                </div>
                <div className="project-progress">
                  <i style={{ width: `${projectProgress(p)}%` }} />
                  <small>Estimated crop-cycle progress</small>
                </div>
                <Button onClick={() => nav(`/app/projects/${p.id}`)}>
                  Open digital twin <ArrowRight />
                </Button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        farms.length && (
          <Card>
            <Empty
              title="No cultivation project yet"
              detail="Create a crop project to start the digital twin lifecycle."
            />
          </Card>
        )
      )}
      {create && (
        <div className="modal-backdrop">
          <div className="modal-card wide">
            <header>
              <div>
                <span className="eyebrow">New digital twin</span>
                <h2>Create cultivation project</h2>
              </div>
              <button onClick={() => setCreate(false)}>×</button>
            </header>
            <div className="field-grid three">
              <label>
                Farm / field
                <select value={form.farm_id} onChange={(e) => setForm({ ...form, farm_id: e.target.value })}>
                  {farms.map((f) => (
                    <option value={f.id} key={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Crop
                <input value={form.crop} onChange={(e) => setForm({ ...form, crop: e.target.value })} />
              </label>
              <label>
                Variety
                <input value={form.variety} onChange={(e) => setForm({ ...form, variety: e.target.value })} />
              </label>
              <label>
                Purpose
                <input value={form.purpose} onChange={(e) => setForm({ ...form, purpose: e.target.value })} />
              </label>
              <label>
                Season
                <select value={form.season} onChange={(e) => setForm({ ...form, season: e.target.value })}>
                  <option>Yala</option>
                  <option>Maha</option>
                  <option>Perennial</option>
                </select>
              </label>
              <label>
                Current stage
                <select value={form.stage} onChange={(e) => setForm({ ...form, stage: e.target.value })}>
                  {stageOrder.map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
              </label>
              <label>
                Planned start
                <input
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                />
              </label>
              <label>
                Actual sowing / transplanting <em>optional</em>
                <input
                  type="date"
                  value={form.actual_start_date}
                  onChange={(e) => setForm({ ...form, actual_start_date: e.target.value })}
                />
              </label>
              <label>
                Target harvest
                <input
                  type="date"
                  value={form.target_harvest}
                  onChange={(e) => setForm({ ...form, target_harvest: e.target.value })}
                />
              </label>
              <label>
                Irrigation mode
                <input
                  value={form.irrigation_mode}
                  onChange={(e) => setForm({ ...form, irrigation_mode: e.target.value })}
                />
              </label>
              <label>
                Seed source
                <input
                  value={form.seed_source}
                  onChange={(e) => setForm({ ...form, seed_source: e.target.value })}
                />
              </label>
              <label>
                Budget (LKR)
                <input
                  type="number"
                  min="0"
                  value={form.budget}
                  onChange={(e) => setForm({ ...form, budget: Number(e.target.value) })}
                />
              </label>
              <label className="full">
                Notes
                <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
              </label>
            </div>
            <Notice tone="info" title="Suitability before prescription">
              The live build can validate regional weather and field context. Consequential
              fertilizer/treatment rates must come from approved agronomic knowledge rather than free-form AI
              generation.
            </Notice>
            <div className="modal-actions">
              <Button variant="ghost" onClick={() => setCreate(false)}>
                Cancel
              </Button>
              <Button onClick={() => void add()}>
                <Sprout /> Generate digital twin plan
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
