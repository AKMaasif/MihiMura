import { useEffect, useState } from 'react';
import { FileText, Mic, Save, Sprout } from 'lucide-react';
import { Button, Card, Empty, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';

export function DiaryPage() {
  const [items, setItems] = useState<any[]>([]),
    [projects, setProjects] = useState<any[]>([]),
    [offline, setOffline] = useState(false),
    [notice, setNotice] = useState(''),
    [form, setForm] = useState<any>({
      project_id: '',
      type: 'field-note',
      note: '',
      growth_stage: '',
      rainfall: '',
      irrigation: '',
      pest_count: 0,
      symptoms: '',
      action_taken: '',
    });
  const load = async () => {
    const [observationsResult, projectsResult] = await Promise.allSettled([
      platformApi.observations(),
      platformApi.projects(),
    ]);

    if (observationsResult.status === 'fulfilled') {
      setItems(observationsResult.value);
    }

    if (projectsResult.status === 'fulfilled') {
      const projectList = projectsResult.value as any[];

      setProjects(projectList);

      setForm((x: any) => ({
        ...x,

        project_id: x.project_id || projectList[0]?.id || '',

        growth_stage: x.growth_stage || projectList[0]?.stage || '',
      }));
    }
  };
  const flushOffline = async () => {
    if (!navigator.onLine) return;
    const q = JSON.parse(localStorage.getItem('mihimura_offline_diary') || '[]');
    if (!q.length) return;
    const failed = [];
    for (const item of q) {
      try {
        const { id, created_at, ...payload } = item;
        await platformApi.addObservation(payload);
      } catch {
        failed.push(item);
      }
    }
    localStorage.setItem('mihimura_offline_diary', JSON.stringify(failed));
    if (q.length !== failed.length)
      setNotice(`${q.length - failed.length} offline observation(s) synchronized.`);
    await load();
  };
  useEffect(() => {
    void load();
    setOffline(!navigator.onLine);
    const h = () => {
      setOffline(!navigator.onLine);
      if (navigator.onLine) void flushOffline();
    };
    window.addEventListener('online', h);
    window.addEventListener('offline', h);
    return () => {
      window.removeEventListener('online', h);
      window.removeEventListener('offline', h);
    };
  }, []);
  const save = async () => {
    if (!form.project_id || !form.note) {
      setNotice('Select a project and add an observation note.');
      return;
    }
    if (offline) {
      const q = JSON.parse(localStorage.getItem('mihimura_offline_diary') || '[]');
      const item = { ...form, created_at: new Date().toISOString(), id: `offline_${Date.now()}` };
      q.push(item);
      localStorage.setItem('mihimura_offline_diary', JSON.stringify(q));
      setItems((x) => [item, ...x]);
      setNotice('Saved offline. It will synchronize when connectivity returns.');
    } else {
      await platformApi.addObservation(form);
      await load();
    }
    setForm((x: any) => ({ ...x, note: '', symptoms: '', action_taken: '' }));
  };
  const voice = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      setNotice('Speech recognition is unavailable in this browser.');
      return;
    }
    const rec = new SR();
    rec.lang = 'en-LK';
    rec.onresult = (e: any) => setForm((x: any) => ({ ...x, note: e.results[0][0].transcript }));
    rec.start();
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <FileText /> Local evidence the models cannot see
          </span>
          <h2>Field diary</h2>
          <p>
            Text/voice notes, crop stage, rain, irrigation, pest counts and actions become persistent
            digital-twin evidence.
          </p>
        </div>
        <Status tone={offline ? 'amber' : 'green'}>
          {offline ? 'Offline · queue enabled' : 'Online · syncing'}
        </Status>
      </section>
      {notice && (
        <Notice tone="info" title="Field diary">
          {notice}
        </Notice>
      )}
      <div className="two-col">
        <Card title="Record an observation" subtitle="Designed to save even when connectivity is poor">
          <div className="field-grid">
            <label>
              Project
              <select
                value={form.project_id}
                onChange={(e) => {
                  const p = projects.find((x) => x.id === e.target.value);
                  setForm({
                    ...form,
                    project_id: e.target.value,
                    growth_stage: p?.stage || form.growth_stage,
                  });
                }}
              >
                <option value="">Select project</option>
                {projects.map((p) => (
                  <option value={p.id} key={p.id}>
                    {p.farm_name} · {p.crop}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Observation type
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                <option>field-note</option>
                <option>pest count</option>
                <option>plant symptom</option>
                <option>rain / irrigation</option>
                <option>task outcome</option>
              </select>
            </label>
            <label>
              Growth stage
              <input
                value={form.growth_stage}
                onChange={(e) => setForm({ ...form, growth_stage: e.target.value })}
              />
            </label>
            <label>
              Pest count
              <input
                type="number"
                min="0"
                value={form.pest_count}
                onChange={(e) => setForm({ ...form, pest_count: Number(e.target.value) })}
              />
            </label>
            <label className="full">
              Voice/text note
              <div className="input-with-action">
                <textarea
                  value={form.note}
                  onChange={(e) => setForm({ ...form, note: e.target.value })}
                  placeholder="What changed in the field today?"
                />
                <button onClick={voice} aria-label="Dictate note">
                  <Mic />
                </button>
              </div>
            </label>
            <label>
              Rain / weather
              <input value={form.rainfall} onChange={(e) => setForm({ ...form, rainfall: e.target.value })} />
            </label>
            <label>
              Irrigation
              <input
                value={form.irrigation}
                onChange={(e) => setForm({ ...form, irrigation: e.target.value })}
              />
            </label>
            <label>
              Plant symptoms
              <input value={form.symptoms} onChange={(e) => setForm({ ...form, symptoms: e.target.value })} />
            </label>
            <label>
              Action taken
              <input
                value={form.action_taken}
                onChange={(e) => setForm({ ...form, action_taken: e.target.value })}
              />
            </label>
          </div>
          <Button disabled={!projects.length} onClick={() => void save()}>
            <Save /> {offline ? 'Save offline' : 'Save & sync'}
          </Button>
        </Card>
        <Card title="Recent observations">
          {items.length ? (
            <div className="diary-list">
              {items.map((x) => (
                <div key={x.id}>
                  <i>
                    <Sprout />
                  </i>
                  <div>
                    <small>
                      {new Date(x.created_at).toLocaleString()} · {x.type}
                    </small>
                    <b>{x.note}</b>
                    <p>
                      {x.growth_stage || 'stage not recorded'} · pests {x.pest_count || 0} ·{' '}
                      {x.rainfall || 'weather not recorded'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Empty title="No field note recorded yet" />
          )}
        </Card>
      </div>
    </>
  );
}
