import {
  Bot,
  CheckCircle2,
  CloudSun,
  Database,
  MapPin,
  MessageSquareText,
  Satellite,
  ShieldCheck,
} from 'lucide-react';

export function HowItWorksPage() {
  return (
    <main className="public-content">
      <section className="public-hero-small">
        <span>One continuous workflow</span>
        <h1>Observe → Predict → Reason → Validate → Explain → Confirm → Execute → Measure.</h1>
      </section>
      <div className="process-timeline">
        {[
          [MapPin, 'Context', 'Farm, crop, stage, field history and consent'],
          [CloudSun, 'Live conditions', 'Forecast, climate baseline and optional IoT'],
          [Satellite, 'Perception', 'Satellite proxies and guided crop images'],
          [Bot, 'Agent reasoning', 'Specialists run tools and compare evidence'],
          [ShieldCheck, 'Safety validation', 'Unsupported or harmful actions are blocked'],
          [MessageSquareText, 'Farmer explanation', 'Simple answer first; evidence opens on demand'],
          [CheckCircle2, 'Execution', 'Create task, expert case or confirmed order'],
          [Database, 'Learning record', 'Outcome and action receipt update the digital twin'],
        ].map(([I, t, d]: any, i) => (
          <div key={t}>
            <i>{String(i + 1).padStart(2, '0')}</i>
            <span>
              <I />
            </span>
            <b>{t}</b>
            <p>{d}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
