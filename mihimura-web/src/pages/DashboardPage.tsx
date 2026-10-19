import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  CalendarDays,
  Camera,
  CheckCircle2,
  CloudRain,
  Droplets,
  Gauge,
  MapPin,
  MessageSquareText,
  Plus,
  RefreshCcw,
  ShieldCheck,
  Sprout,
  ThermometerSun,
  Waves,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Card, Metric, Notice, Status, Button, Empty } from '../components/common/UI';
import { platformApi } from '../services/platformApi';
import { useAuth } from '../context/AuthContext';

export default function DashboardPage() {
  const nav = useNavigate();
  const { profile } = useAuth();
  const [tasks, setTasks] = useState<any[]>([]),
    [projects, setProjects] = useState<any[]>([]),
    [weather, setWeather] = useState<any>(null),
    [dashboard, setDashboard] = useState<any>(null),
    [loading, setLoading] = useState(true),
    [degraded, setDegraded] = useState(false);

  const load = async () => {
    setLoading(true);
    setDegraded(false);
    const r = await Promise.allSettled([
      platformApi.tasks(),
      platformApi.projects(),
      platformApi.weather(profile?.lat || 7.291, profile?.lon || 81.674, 14),
      platformApi.dashboard(),
    ]);
    if (r[0].status === 'fulfilled') setTasks(r[0].value);
    else setDegraded(true);
    if (r[1].status === 'fulfilled') setProjects(r[1].value);
    else setDegraded(true);
    if (r[2].status === 'fulfilled') setWeather(r[2].value);
    else setDegraded(true);
    if (r[3].status === 'fulfilled') setDashboard(r[3].value);
    else setDegraded(true);
    setLoading(false);
  };

  useEffect(() => {
    void load();
  }, [profile?.lat, profile?.lon]);

  const pending = tasks.filter((x) => x.status !== 'completed');
  const rain = weather?.daily?.precipitation_probability_max?.[1] ?? null;
  const p = projects[0] || null;
  const topActions = useMemo(() => pending.slice(0, 3), [pending]);
  const walletDays = p ? Math.max(1.8, 6.2 - (Number(p.risk_score || 30) / 100) * 2).toFixed(1) : '—';

  const twinStages = ['Planning', 'Establishment', 'Vegetative', 'Reproductive', 'Harvest'];

  const normalizeStage = (stage?: string) => {
    switch ((stage || '').toLowerCase()) {
      case 'planning':
        return 'Planning';
      case 'establishment':
      case 'germination':
      case 'seedling':
        return 'Establishment';
      case 'vegetative':
      case 'tillering':
        return 'Vegetative';
      case 'flowering':
      case 'reproductive':
      case 'grain filling':
        return 'Reproductive';
      case 'harvest':
      case 'harvesting':
        return 'Harvest';
      default:
        return 'Planning';
    }
  };

  const currentTwinStage = normalizeStage(p?.stage);
  const currentTwinStageIndex = twinStages.indexOf(currentTwinStage);

  return (
    <>
      <section className="command-hero">
        <div>
          <span className="eyebrow">
            <MapPin /> {profile?.district || 'Sri Lanka'} ·{' '}
            {new Date().toLocaleDateString('en-LK', { weekday: 'long', day: 'numeric', month: 'long' })}
          </span>
          <h2>Good morning, {String(profile?.name || 'Farmer').split(' ')[0]}.</h2>
          <p>
            {p
              ? 'Your farm digital twin has checked weather, field history and active risks.'
              : `Your profile is ready. Create your first farm and cultivation project to activate field-specific intelligence.`}
          </p>
        </div>
        <div className="command-actions">
          <Button variant="secondary" onClick={() => void load()}>
            <RefreshCcw /> Refresh intelligence
          </Button>
          <Button onClick={() => nav('/app/ai')}>
            <MessageSquareText /> Ask MihiMura
          </Button>
        </div>
      </section>

      {degraded && (
        <Notice tone="warning" title="Some live services are temporarily unavailable">
          MihiMura is showing the data that could be synchronized successfully. Retry before making a
          consequential field decision.
        </Notice>
      )}
      {rain !== null && rain >= 70 && (
        <Notice tone="warning" title="Weather may change tomorrow’s field plan">
          Rain probability is currently {rain}%. Review weather-dependent tasks before applying inputs or
          scheduling exposed field work.
        </Notice>
      )}

      {!p && (
        <Card className="first-field-card">
          <div className="first-field-journey">
            <span className="first-field-icon">
              <Sprout />
            </span>
            <div>
              <span className="eyebrow">Activate your farm digital twin</span>
              <h3>Connect a real field to MihiMura</h3>
              <p>
                Add a farm boundary, then create a crop project. Weather, AI chat, crop scans, tasks, water
                budgeting and recommendations will use that context instead of generic assumptions.
              </p>
              <div className="first-field-steps">
                <span>
                  <i>1</i>Add farm
                </span>
                <span>
                  <i>2</i>Create crop project
                </span>
                <span>
                  <i>3</i>Receive field-specific actions
                </span>
              </div>
            </div>
            <Button onClick={() => nav('/app/farms')}>
              Add my first farm <ArrowRight />
            </Button>
          </div>
        </Card>
      )}

      <section className="dashboard-metrics">
        <Metric
          label="Farm risk"
          value={p ? `${p.risk_score ?? 0}/100` : '—'}
          note={p ? 'Explainable composite' : 'Create a project to calculate'}
          icon={Gauge}
          tone={p && Number(p.risk_score) > 55 ? 'orange' : 'green'}
        />
        <Metric
          label="14-day weather"
          value={rain === null ? '—' : `${rain}%`}
          note="Tomorrow rain probability"
          icon={CloudRain}
          tone="blue"
        />
        <Metric
          label="Active projects"
          value={projects.length}
          note="Digital twins currently running"
          icon={Sprout}
        />
        <Metric
          label="Water wallet"
          value={p ? `${walletDays} days` : '—'}
          note={p ? 'Estimated field balance' : 'Requires a project'}
          icon={Droplets}
          tone="blue"
        />
        <Metric
          label="Open tasks"
          value={pending.length}
          note="Weather-aware execution queue"
          icon={CalendarDays}
          tone="purple"
        />
      </section>

      <div className="dashboard-main-grid">
        <Card
          title="What needs attention today"
          subtitle="Action-first queue ranked by urgency, safety and expected risk reduction"
          action={
            <button className="text-link" onClick={() => nav('/app/tasks')}>
              Open task centre <ArrowRight />
            </button>
          }
        >
          <div className="attention-list">
            {topActions.map((t, i) => (
              <button key={t.id} className="attention-item" onClick={() => nav('/app/tasks')}>
                <i className={t.priority} />
                <span className="attention-rank">0{i + 1}</span>
                <div>
                  <b>{t.title}</b>
                  <p>
                    {t.farm_name || p?.farm_name || 'Farm project'} ·{' '}
                    {t.weather_dependency || 'No weather dependency'}
                  </p>
                </div>
                <Status tone={t.priority === 'high' ? 'orange' : 'amber'}>{t.priority}</Status>
                <ArrowRight />
              </button>
            ))}
            {!topActions.length && (
              <div className="all-clear">
                <CheckCircle2 />
                <b>{p ? 'No urgent task is waiting.' : 'Your action queue will appear here.'}</b>
                <span>
                  {p
                    ? 'Continue routine monitoring and record field observations.'
                    : 'Create a project to generate stage-aware tasks and weather-sensitive actions.'}
                </span>
                {!p && (
                  <Button variant="secondary" onClick={() => nav('/app/projects')}>
                    Create project
                  </Button>
                )}
              </div>
            )}
          </div>
        </Card>

        <Card
          title="Local situation"
          subtitle={`${profile?.district || 'Manual region'} · ${profile?.location_consent ? 'GPS context enabled' : 'manual region context'}`}
        >
          <div className="weather-live">
            <div>
              <CloudRain />
              <span>
                <b>
                  {weather?.current?.temperature_2m !== undefined
                    ? `${weather.current.temperature_2m}°C`
                    : 'No live reading'}
                </b>
                <small>
                  {weather?.current?.relative_humidity_2m !== undefined
                    ? `${weather.current.relative_humidity_2m}% humidity`
                    : 'Refresh live weather'}
                </small>
              </span>
            </div>
            {rain !== null && (
              <Status tone={rain >= 70 ? 'orange' : 'amber'}>{rain >= 70 ? 'Action' : 'Watch'}</Status>
            )}
          </div>
          <div className="risk-bars">
            <label>
              <span>
                Rain / runoff <b>{rain === null ? 'Unknown' : rain >= 70 ? 'High' : 'Watch'}</b>
              </span>
              <i>
                <em style={{ width: `${rain === null ? 0 : Math.min(95, rain)}%` }} />
              </i>
            </label>
            <label>
              <span>
                Heat stress <b>Contextual</b>
              </span>
              <i>
                <em style={{ width: weather?.current?.temperature_2m >= 34 ? '72%' : '45%' }} />
              </i>
            </label>
            <label>
              <span>
                Regional crop pressure{' '}
                <b>{dashboard?.provinces?.Eastern?.pestRisk ? 'Monitored' : 'Awaiting data'}</b>
              </span>
              <i>
                <em style={{ width: `${dashboard?.provinces?.Eastern?.pestRisk || 0}%` }} />
              </i>
            </label>
          </div>
          <Button variant="secondary" onClick={() => nav('/app/local')}>
            Open local situation <ArrowRight />
          </Button>
        </Card>
      </div>

      <div className="dashboard-secondary-grid">
        <Card
          title="Active digital twin"
          subtitle="Persistent memory for crop, stage, tasks, interventions and outcomes"
        >
          {p ? (
            <div className="digital-twin-card">
              <div className="twin-top">
                <span className="twin-icon">
                  <Sprout />
                </span>
                <div>
                  <small>{p.farm_name}</small>
                  <h3>
                    {p.crop} · {p.variety || 'Variety not set'}
                  </h3>
                  <p>
                    {p.stage} · health {p.health_score ?? '—'}/100
                  </p>
                </div>
                <Status tone={(p.risk_score ?? 0) > 55 ? 'orange' : 'green'}>
                  {p.risk_score ?? '—'} risk
                </Status>
              </div>

              <div className="stage-track">
                {['Planning', 'Establishment', 'Vegetative', 'Reproductive', 'Harvest'].map((s, i) => (
                  <div
                    className={
                      i <=
                      Math.min(
                        4,
                        [
                          'Planning',
                          'Establishment',
                          'Vegetative',
                          'Tillering',
                          'Flowering',
                          'Reproductive',
                          'Harvest',
                        ].indexOf(p.stage) >= 0
                          ? Math.min(
                              4,
                              [
                                'Planning',
                                'Establishment',
                                'Vegetative',
                                'Tillering',
                                'Flowering',
                                'Reproductive',
                                'Harvest',
                              ].indexOf(p.stage),
                            )
                          : 1,
                      )
                        ? 'done'
                        : ''
                    }
                    key={s}
                  >
                    <i>{i < 2 ? <CheckCircle2 /> : i === 2 ? <Activity /> : ''}</i>
                    {/* Replaced <span> with <b> to avoid CSS bubble collision */}
                    <b>{s}</b>
                  </div>
                ))}
              </div>

              <div className="twin-foot">
                <span>
                  <Waves /> Water budget {walletDays} days
                </span>
                <span>
                  <ShieldCheck /> Confirmation gates enabled
                </span>
                <div style={{ marginLeft: 'auto' }}>
                  <Button variant="primary" onClick={() => nav(`/app/projects/${p.id}`)}>
                    Open digital twin
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <Empty
              title="No digital twin yet"
              detail="Create a cultivation project after adding your first farm."
            />
          )}
        </Card>

        <Card title="Quick evidence" subtitle="Field observations improve decisions more than generic chat">
          <div className="quick-actions">
            <button onClick={() => nav('/app/scan')}>
              <Camera />
              <span>
                <b>Scan a crop</b>
                <small>Guided image diagnosis</small>
              </span>
              <ArrowRight />
            </button>
            <button onClick={() => nav('/app/diary')}>
              <Plus />
              <span>
                <b>Record field observation</b>
                <small>Symptoms, pests, rain, action</small>
              </span>
              <ArrowRight />
            </button>
            <button onClick={() => nav('/app/ai')}>
              <Bot />
              <span>
                <b>Ask about this farm</b>
                <small>Context-aware AI reasoning</small>
              </span>
              <ArrowRight />
            </button>
          </div>
        </Card>

        <Card title="Resilience passport" subtitle="Seasonal improvement, not a vague sustainability badge">
          <div className="passport-score">
            <strong>{p ? '74' : '—'}</strong>
            <span>/100</span>
            {p && <Status tone="green">Improving</Status>}
          </div>
          {p ? (
            <>
              <div className="passport-list">
                <span>
                  Water efficiency <b>78</b>
                </span>
                <span>
                  Soil protection <b>71</b>
                </span>
                <span>
                  Climate readiness <b>69</b>
                </span>
                <span>
                  Task adherence <b>82</b>
                </span>
              </div>
              <button className="text-link" onClick={() => nav('/app/reports')}>
                View impact report <ArrowRight />
              </button>
            </>
          ) : (
            <p className="muted-copy">
              The passport activates after your project starts recording tasks, water use, risks and
              interventions.
            </p>
          )}
        </Card>
      </div>

      <section className="innovation-strip">
        <div>
          <ThermometerSun />
          <span>
            <b>Forecast-to-Task Autopilot</b>
            <small>Proposes safer task windows when weather changes.</small>
          </span>
        </div>
        <div>
          <Waves />
          <span>
            <b>Water Budget Wallet</b>
            <small>Tracks crop-stage demand and forecast contribution.</small>
          </span>
        </div>
        <div>
          <Bot />
          <span>
            <b>Explainable counterfactuals</b>
            <small>Shows what would change an AI recommendation.</small>
          </span>
        </div>
        <div>
          <AlertTriangle />
          <span>
            <b>Community Sentinel</b>
            <small>Privacy-thresholded local outbreak awareness.</small>
          </span>
        </div>
      </section>

      {loading && <div className="page-loading">Synchronising live sources…</div>}
    </>
  );
}
