import { ArrowRight, ShieldCheck } from 'lucide-react';
import { Card } from '../../components/common/UI';

export function AboutPage() {
  return (
    <main className="public-content">
      <section className="public-hero-small">
        <span>Why MihiMura exists</span>
        <h1>A farmer-experience layer over fragmented climate and agricultural intelligence.</h1>
        <p>
          Climate losses emerge from interacting conditions. MihiMura’s goal is to catch those interactions
          early and turn them into understandable, accountable action.
        </p>
      </section>
      <div className="public-grid3">
        {[
          [
            'Late detection',
            'Stress is often noticed only after visible damage.',
            'Combine photos, field observations, weather anomalies and satellite proxies.',
          ],
          [
            'Generic advice',
            'The same instruction can be wrong across crop stages and locations.',
            'Condition guidance on field location, stage, water, history and forecast.',
          ],
          [
            'No execution loop',
            'Advice often ends as a message.',
            'Turn accepted recommendations into tasks, reminders, expert cases and verified action records.',
          ],
        ].map((x) => (
          <Card key={x[0]} title={x[0]}>
            <p>{x[1]}</p>
            <div className="solution-line">
              <ArrowRight /> {x[2]}
            </div>
          </Card>
        ))}
      </div>
      <Card title="Operating principle" className="public-wide-card">
        <div className="principle-row">
          <ShieldCheck />
          <div>
            <b>Decision support, not false authority</b>
            <p>
              High-risk recommendations expose uncertainty and evidence, require confirmation and escalate
              when confidence is low or harm could be significant.
            </p>
          </div>
        </div>
      </Card>
    </main>
  );
}
