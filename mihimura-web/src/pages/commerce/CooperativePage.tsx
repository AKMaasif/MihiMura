import { useState } from 'react';
import { CircleDollarSign, Handshake, PackageCheck, ShieldCheck, ShoppingCart, Truck } from 'lucide-react';
import { Button, Card } from '../../components/common/UI';

export function CooperativePage() {
  const [active, setActive] = useState<string | null>(null);
  const pools = [
    ['Certified paddy seed', '420 kg', '8 farms', 'Ampara'],
    ['Sticky traps', '320 units', '11 farms', 'Ampara / Batticaloa'],
    ['Soil moisture meters', '14 units', '14 farms', 'Eastern Province'],
  ];
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Handshake /> Aggregated demand planning
          </span>
          <h2>Cooperative / supplier portal</h2>
          <p>
            Opt-in demand can be grouped to reduce cost and delivery distance without exposing private
            agronomic rankings.
          </p>
        </div>
      </section>
      <div className="dashboard-metrics">
        <div className="ui-metric">
          <span className="ui-metric-icon">
            <ShoppingCart />
          </span>
          <div>
            <small>Open demand pool</small>
            <strong>118 units</strong>
            <em>Across 23 opt-in farms</em>
          </div>
        </div>
        <div className="ui-metric tone-green">
          <span className="ui-metric-icon">
            <Truck />
          </span>
          <div>
            <small>Grouped deliveries</small>
            <strong>4</strong>
            <em>Planned this week</em>
          </div>
        </div>
        <div className="ui-metric tone-purple">
          <span className="ui-metric-icon">
            <CircleDollarSign />
          </span>
          <div>
            <small>Estimated logistics saving</small>
            <strong>14%</strong>
            <em>Demo cooperative model</em>
          </div>
        </div>
      </div>
      <div className="two-col">
        <Card title="Collective procurement pool">
          <div className="pool-list">
            {pools.map((x) => (
              <div className={active === x[0] ? 'active' : ''} key={x[0]}>
                <PackageCheck />
                <span>
                  <b>{x[0]}</b>
                  <small>
                    {x[2]} · {x[3]}
                  </small>
                </span>
                <strong>{x[1]}</strong>
                <Button variant="secondary" onClick={() => setActive(active === x[0] ? null : x[0])}>
                  {active === x[0] ? 'Close' : 'Open pool'}
                </Button>
                {active === x[0] && (
                  <p className="pool-detail">
                    Only aggregate demand is visible. Exact field boundaries, diagnoses and individual farmer
                    recommendations are not shared with suppliers.
                  </p>
                )}
              </div>
            ))}
          </div>
        </Card>
        <Card title="Partner safeguards">
          <div className="threshold-grid">
            {[
              'Supplier payment does not affect recommendation rank',
              'Only verified catalog items can enter a pool',
              'Farmer must opt in to aggregated demand',
              'Exact farm boundaries are not shared with suppliers',
              'Substitutions require explicit permission',
              'Order confirmations remain auditable',
            ].map((x) => (
              <div key={x}>
                <ShieldCheck />
                <span>{x}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}
