import {
  ArrowRight,
  Bot,
  CheckCircle2,
  CloudSun,
  Globe2,
  Leaf,
  MapPin,
  Radar,
  Satellite,
  ShieldCheck,
  Sprout,
  Users,
  Waves,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button, Status } from '../../components/common/UI';
import { SriLankaProvinceMap } from '../../components/dashboard/SriLankaProvinceMap';
import { situationLabel, useProvinceSituation } from '../../hooks/useProvinceSituation';

export function WelcomePage() {
  const situation = useProvinceSituation();
  const provinces = Object.values(situation.provinces);
  // Highlight the province with the lowest crop condition and the wettest outlook.
  const focus = provinces.length
    ? provinces.reduce((a, b) => (b.healthScore < a.healthScore ? b : a), provinces[0])
    : undefined;
  const wettest = provinces.length
    ? provinces.reduce(
        (a, b) => ((b.rainProbabilityNext3d ?? 0) > (a.rainProbabilityNext3d ?? 0) ? b : a),
        provinces[0],
      )
    : undefined;
  const needsAction = focus && focus.healthScore < 60;
  return (
    <main className="welcome-page">
      <section className="welcome-hero">
        <div className="welcome-copy">
          <span className="hero-tag"> A living farm intelligence system for Sri Lanka</span>
          <h1>
            Climate threats become <em>clear actions</em> before they become crop loss.
          </h1>
          <p>
            MihiMura connects a persistent farm digital twin with weather, crop evidence, satellite signals,
            trusted knowledge and safety-aware AI agents.
          </p>
          <div className="welcome-actions">
            <Link to="/auth?mode=register">
              <Button>
                Build my field companion <ArrowRight />
              </Button>
            </Link>
            <Link to="/auth">
              <Button variant="secondary">Open existing profile</Button>
            </Link>
          </div>
          <div className="hero-proof">
            <div>
              <b>14-day</b>
              <span>risk horizon</span>
            </div>
            <div>
              <b>3</b>
              <span>languages</span>
            </div>
            <div>
              <b>9</b>
              <span>Sri Lankan provinces</span>
            </div>
            <div>
              <b>1 loop</b>
              <span>observe → act → learn</span>
            </div>
          </div>
        </div>
        <div className="welcome-visual">
          <div className="hero-glass map">
            <div className="glass-head">
              <span>
                <Globe2 /> Live national pulse
              </span>
              <Status tone={situation.offline || !situation.live ? 'amber' : needsAction ? 'orange' : 'green'}>
                {situation.offline ? 'Offline' : !situation.live ? 'Baseline' : needsAction ? 'Action' : 'Stable'}
              </Status>
            </div>
            <SriLankaProvinceMap
              selectedProvince={focus?.name || 'Eastern'}
              activeLayer="cropHealth"
              provinces={situation.provinces}
              onSelectProvince={() => {}}
              sourceNote={situationLabel(situation)}
            />
          </div>
          <div className="hero-float agent">
            <Bot />
            <div>
              <small>Safety agent · {focus?.name}</small>
              <b>{focus?.nextAction || 'Routine monitoring'}</b>
              <p>Crop condition index {focus?.healthScore ?? '—'}/100.</p>
            </div>
          </div>
          <div className="hero-float weather">
            <CloudSun />
            <div>
              <b>{situation.live ? `${wettest?.rainProbabilityNext3d ?? 0}%` : '—'}</b>
              <span>rain chance · {wettest?.name}</span>
            </div>
          </div>
        </div>
      </section>
      <section className="journey-ribbon">
        {[
          ['01', MapPin, 'Locate', 'GPS or manual region'],
          ['02', Sprout, 'Remember', 'Create a crop digital twin'],
          ['03', Satellite, 'Observe', 'Weather, images, satellite'],
          ['04', Radar, 'Predict', 'Risk with uncertainty'],
          ['05', ShieldCheck, 'Validate', 'Safety and expert gates'],
          ['06', CheckCircle2, 'Act & learn', 'Tasks, receipts, outcomes'],
        ].map(([n, I, t, d]: any) => (
          <div key={n}>
            <i>{n}</i>
            <I />
            <b>{t}</b>
            <span>{d}</span>
          </div>
        ))}
      </section>
      <section className="welcome-cards">
        <div className="section-heading">
          <span>Beyond a chatbot</span>
          <h2>A coordinated operational system around each real field.</h2>
        </div>
        <div className="feature-cards">
          {[
            [
              Bot,
              'Agentic coordination',
              'Specialist agents retrieve evidence, reason in parallel and pass the final action through policy checks.',
            ],
            [
              Waves,
              'Water Budget Wallet',
              'See crop-stage demand, rainfall contribution and estimated days of water remaining.',
            ],
            [
              Users,
              'Community Sentinel',
              'Anonymized local reports can reveal emerging clusters only after privacy and quality thresholds.',
            ],
            [
              ShieldCheck,
              'Verified Action Receipts',
              'Consequential recommendations retain source, confidence, confirmation and outcome for auditability.',
            ],
          ].map(([I, t, d]: any) => (
            <article key={t}>
              <I />
              <b>{t}</b>
              <p>{d}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="welcome-cta">
        <Leaf />
        <span>Built for the farmer’s next decision, not another dashboard to interpret.</span>
        <Link to="/auth?mode=register">
          <Button>
            Start the journey <ArrowRight />
          </Button>
        </Link>
      </section>
    </main>
  );
}
