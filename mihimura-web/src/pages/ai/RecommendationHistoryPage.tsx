import { useEffect, useState } from 'react';
import { ArrowRight, FileText, ShieldCheck } from 'lucide-react';
import { Card, Empty, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';

export function RecommendationHistoryPage() {
  const [audit, setAudit] = useState<any[]>([]);
  useEffect(() => {
    platformApi
      .audit()
      .then(setAudit)
      .catch(() => setAudit([]));
  }, []);
  const items = audit.filter(
    (x) =>
      x.action === 'ai_recommendation' ||
      x.action === 'crop_image_analysis' ||
      x.action === 'create_task' ||
      x.action === 'confirmed_order',
  );
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <FileText /> Explainable history
          </span>
          <h2>Recommendation history & action receipts</h2>
          <p>
            Consequential decisions preserve provider, confidence, user confirmation and outcome instead of
            disappearing into chat history.
          </p>
        </div>
      </section>
      <Card
        title="Verified action receipts"
        subtitle="Audit trail for recommendations, scans, task creation and confirmed orders"
      >
        {items.length ? (
          <div className="receipt-list">
            {items.map((x: any) => (
              <div key={x.id}>
                <span className="receipt-icon">
                  <ShieldCheck />
                </span>
                <div>
                  <small>{new Date(x.created_at).toLocaleString()}</small>
                  <b>{String(x.action).replaceAll('_', ' ')}</b>
                  <p>
                    {x.details?.question ||
                      x.details?.filename ||
                      x.details?.filenames?.join(', ') ||
                      x.entity}
                  </p>
                </div>
                <Status tone="green">Recorded</Status>
                <button aria-label="Open receipt details">
                  <ArrowRight />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <Empty
            title="No action receipts yet"
            detail="Ask MihiMura a question, run a crop scan, create a task or confirm an order to create the first auditable record."
          />
        )}
      </Card>
    </>
  );
}
