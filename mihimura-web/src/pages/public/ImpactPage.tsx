export function ImpactPage() {
  return (
    <main className="public-content">
      <section className="public-hero-small">
        <span>Measurable resilience</span>
        <h1>Designed around SDG 2, SDG 13 and SDG 15.</h1>
        <p>The system tracks practical outcomes instead of presenting sustainability as a vague score.</p>
      </section>
      <div className="sdg-big-grid">
        <article>
          <i>2</i>
          <h2>Zero Hunger</h2>
          <p>Resilient production, earlier intervention and reduced avoidable crop loss.</p>
          <b>KPIs</b>
          <span>Yield retained · crop-loss events avoided · task adherence · smallholder reach</span>
        </article>
        <article>
          <i>13</i>
          <h2>Climate Action</h2>
          <p>Local risk awareness and adaptation before weather becomes operational damage.</p>
          <b>KPIs</b>
          <span>Early-warning lead time · water saved · climate actions completed</span>
        </article>
        <article>
          <i>15</i>
          <h2>Life on Land</h2>
          <p>Soil protection, responsible inputs and lower-risk interventions.</p>
          <b>KPIs</b>
          <span>Input reduction · soil-health actions · erosion prevention · biodiversity checks</span>
        </article>
      </div>
    </main>
  );
}
