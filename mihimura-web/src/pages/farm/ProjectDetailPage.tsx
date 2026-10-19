import { useEffect, useState } from 'react';
import { CalendarDays, CheckCircle2, CircleDollarSign, Droplets, Sprout } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Card, Empty, Metric, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { stageOrder } from './farmShared';

export function ProjectDetailPage() {
  const nav = useNavigate();
  const { projectId } = useParams();
  const [project, setProject] = useState<any>(null),
    [tasks, setTasks] = useState<any[]>([]),
    [observations, setObservations] = useState<any[]>([]),
    [expenses, setExpenses] = useState<any[]>([]),
    [weather, setWeather] = useState<any>(null);
  useEffect(() => {
    Promise.allSettled([
      platformApi.projects(),
      platformApi.tasks(),
      platformApi.observations(),
      platformApi.expenses(),
    ]).then((r) => {
      if (r[0].status === 'fulfilled') {
        const p = r[0].value.find((x: any) => x.id === projectId);
        setProject(p || null);
        if (p)
          platformApi
            .weather(p.lat || 7.291, p.lon || 81.674, 14)
            .then(setWeather)
            .catch(() => {});
      }
      if (r[1].status === 'fulfilled') setTasks(r[1].value.filter((x: any) => x.project_id === projectId));
      if (r[2].status === 'fulfilled')
        setObservations(r[2].value.filter((x: any) => x.project_id === projectId));
      if (r[3].status === 'fulfilled') setExpenses(r[3].value.filter((x: any) => x.project_id === projectId));
    });
  }, [projectId]);
  if (!project)
    return (
      <Card>
        <Empty
          title="Project not found"
          detail="Return to Cultivation Projects and open an available digital twin."
        />
        <div className="empty-actions">
          <Button onClick={() => nav('/app/projects')}>Back to projects</Button>
        </div>
      </Card>
    );
  const planted = project.actual_start_date || project.start_date;
  const days = planted ? Math.max(0, Math.floor((Date.now() - Date.parse(planted)) / 86400000)) : 0;
  const rain = weather?.daily?.precipitation_probability_max?.[1];
  const spent = expenses.reduce((s, x) => s + Number(x.amount || 0), 0);
  return (
    <>
      <section className="twin-header">
        <div>
          <span className="eyebrow">
            {project.farm_name} · {project.season || 'Season'}
          </span>
          <h2>
            {project.crop} · {project.variety || 'Variety not set'}
          </h2>
          <p>
            Day {days} · {project.stage} stage
          </p>
        </div>
        <div>
          <Status
            tone={
              Number(project.risk_score) > 70 ? 'red' : Number(project.risk_score) > 50 ? 'orange' : 'green'
            }
          >
            Risk {project.risk_score ?? '—'}
          </Status>
          <Status tone="amber">Health {project.health_score ?? '—'}</Status>
          <Button onClick={() => nav('/app/ai')}>Ask AI about this project</Button>
        </div>
      </section>
      <div className="dashboard-metrics">
        <Metric label="Current stage" value={project.stage} note="Digital twin lifecycle" icon={Sprout} />
        <Metric
          label="Days after planting"
          value={days}
          note="From recorded start date"
          icon={CalendarDays}
        />
        <Metric
          label="Tomorrow rain"
          value={rain === undefined ? '—' : `${rain}%`}
          note="Open-Meteo live/fallback"
          icon={Droplets}
          tone="blue"
        />
        <Metric
          label="Recorded spend"
          value={`LKR ${spent.toLocaleString()}`}
          note={`Budget LKR ${Number(project.budget || 0).toLocaleString()}`}
          icon={CircleDollarSign}
          tone="purple"
        />
      </div>
      <Card
        title="Cultivation lifecycle"
        subtitle="Weather and observations can propose safer task windows; the farmer confirms changes"
      >
        <div className="lifecycle-track">
          {stageOrder.map((s, i) => {
            const current = Math.max(0, stageOrder.indexOf(project.stage));
            return (
              <div className={i < current ? 'done' : i === current ? 'active' : ''} key={s}>
                <i>{i < current ? <CheckCircle2 /> : i + 1}</i>
                <b>{s}</b>
              </div>
            );
          })}
        </div>
      </Card>
      <div className="three-col">
        <Card title="Today / upcoming tasks">
          <div className="compact-task-list">
            {tasks.slice(0, 5).map((t) => (
              <div key={t.id}>
                <i className={t.priority} />
                <span>
                  <b>{t.title}</b>
                  <small>
                    {new Date(t.due_at).toLocaleString()} · {t.weather_dependency}
                  </small>
                </span>
                <Status tone={t.status === 'completed' ? 'green' : 'amber'}>{t.status}</Status>
              </div>
            ))}
          </div>
          {!tasks.length && <Empty title="No task yet" />}
          <Button variant="secondary" onClick={() => nav('/app/tasks')}>
            Open task centre
          </Button>
        </Card>
        <Card title="Field evidence timeline">
          <div className="evidence-timeline">
            {observations.slice(0, 5).map((o) => (
              <div key={o.id}>
                <i />
                <time>{new Date(o.created_at).toLocaleDateString()}</time>
                <span>
                  <b>{o.type}</b>
                  <small>{o.note}</small>
                </span>
              </div>
            ))}
          </div>
          {!observations.length && <Empty title="No field observation yet" />}
          <Button variant="secondary" onClick={() => nav('/app/diary')}>
            Record evidence
          </Button>
        </Card>
        <Card title="Next safe action">
          <div className="next-stage">
            <Sprout />
            <b>
              {rain !== undefined && rain > 70
                ? 'Review exposed operations before rain'
                : 'Continue stage-aware monitoring'}
            </b>
            <span>
              {rain !== undefined ? `Tomorrow rain probability ${rain}%` : 'Weather context unavailable'}
            </span>
            <p>Ask MihiMura for an explainable recommendation grounded in this project.</p>
          </div>
          <Button onClick={() => nav('/app/ai')}>Ask MihiMura</Button>
        </Card>
      </div>
    </>
  );
}
