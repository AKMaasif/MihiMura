import { Card } from '../../components/common/UI';

export function HelpPage() {
  return (
    <main className="public-content">
      <section className="public-hero-small">
        <span>Help & transparency</span>
        <h1>Know what the system knows & what it does not.</h1>
      </section>
      <div className="public-grid3">
        <Card title="Using the demo">
          <p>
            Create a demo identity, finish onboarding, open the active paddy digital twin, ask about
            fertilizer timing, upload a crop image, create a task and complete a mock verified order.
          </p>
        </Card>
        <Card title="AI limitations">
          <p>
            Forecasts carry uncertainty, satellite vegetation values are proxies, and a phone image cannot
            confirm many diseases without field symptoms or lab testing.
          </p>
        </Card>
        <Card title="Data control">
          <p>
            Location, sharing, expert referral and purchasing require contextual consent. Exact farm
            boundaries should not appear in public regional analytics.
          </p>
        </Card>
      </div>
    </main>
  );
}
