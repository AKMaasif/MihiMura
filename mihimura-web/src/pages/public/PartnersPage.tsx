import { HeartHandshake } from 'lucide-react';

export function PartnersPage() {
  return (
    <main className="public-content">
      <section className="public-hero-small">
        <span>Partnership architecture</span>
        <h1>MihiMura integrates authorities and field actors; it does not replace them.</h1>
      </section>
      <div className="partner-grid">
        {[
          ['Department of Agriculture', 'Protocols, crop guidance and expert review'],
          ['Department of Meteorology', 'Authoritative weather advisories'],
          ['Disaster Management Centre', 'Warnings and emergency context'],
          ['Department of Census & Statistics', 'Crop extent, production and reporting'],
          ['Universities', 'Agronomy, remote sensing, HCI and evaluation'],
          ['Farmer cooperatives', 'Co-design, trust and collective procurement'],
          ['Verified suppliers', 'Stock, delivery and safety metadata'],
          ['Telecommunications partners', 'Low-cost push, SMS and voice fallback'],
        ].map((x) => (
          <article key={x[0]}>
            <HeartHandshake />
            <b>{x[0]}</b>
            <p>{x[1]}</p>
          </article>
        ))}
      </div>
    </main>
  );
}
