import { useEffect, useState } from 'react';
import { Handshake, MapPin, Store } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Empty, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';

export function SuppliersPage() {
  const nav = useNavigate();
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    platformApi
      .suppliers()
      .then(setItems)
      .catch(() => {});
  }, []);
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Handshake /> Partner transparency
          </span>
          <h2>Verified suppliers</h2>
          <p>
            Verification status, location and delivery are visible separately from agronomic recommendation
            logic.
          </p>
        </div>
      </section>
      {items.length ? (
        <div className="supplier-grid">
          {items.map((s) => (
            <Card key={s.id}>
              <div className="supplier-card">
                <span>
                  <Store />
                </span>
                <div>
                  <Status tone="green">Verified supplier</Status>
                  <h3>{s.name}</h3>
                  <p>
                    <MapPin /> {s.district}
                  </p>
                  <dl>
                    <div>
                      <dt>Service rating</dt>
                      <dd>{s.rating}/5</dd>
                    </div>
                    <div>
                      <dt>Delivery</dt>
                      <dd>{s.delivery}</dd>
                    </div>
                  </dl>
                  <Button variant="secondary" onClick={() => nav('/app/marketplace')}>
                    View catalog
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <Empty title="Supplier directory unavailable" />
        </Card>
      )}
    </>
  );
}
