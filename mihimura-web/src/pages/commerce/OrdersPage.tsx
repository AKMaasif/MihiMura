import { useEffect, useState } from 'react';
import { CheckCircle2, MapPin, PackageCheck, Truck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Empty, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';

export function OrdersPage() {
  const nav = useNavigate();
  const [orders, setOrders] = useState<any[]>([]),
    [notice, setNotice] = useState('');
  useEffect(() => {
    platformApi
      .orders()
      .then(setOrders)
      .catch(() => {});
  }, []);
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Truck /> Traceable fulfillment
          </span>
          <h2>Orders, delivery & purchase history</h2>
          <p>
            Every confirmed order links back to a project and preserves user confirmation in the audit trail.
          </p>
        </div>
      </section>
      {notice && (
        <Notice tone="info" title="Order support">
          {notice}
        </Notice>
      )}
      {orders.length ? (
        <div className="orders-list">
          {orders.map((o) => (
            <Card key={o.id}>
              <div className="order-head">
                <div>
                  <Status tone="green">{o.status}</Status>
                  <h3>{o.id}</h3>
                  <p>{new Date(o.created_at).toLocaleString()}</p>
                </div>
                <strong>LKR {Number(o.total).toLocaleString()}</strong>
              </div>
              <div className="tracking">
                <div className="done">
                  <i>
                    <CheckCircle2 />
                  </i>
                  <span>
                    <b>Confirmed</b>
                    <small>Order receipt stored</small>
                  </span>
                </div>
                <div className="active">
                  <i>
                    <PackageCheck />
                  </i>
                  <span>
                    <b>Preparing</b>
                    <small>Demo supplier processing</small>
                  </span>
                </div>
                <div>
                  <i>
                    <Truck />
                  </i>
                  <span>
                    <b>In transit</b>
                    <small>Pending</small>
                  </span>
                </div>
                <div>
                  <i>
                    <MapPin />
                  </i>
                  <span>
                    <b>Delivered</b>
                    <small>Pending</small>
                  </span>
                </div>
              </div>
              <div className="order-items">
                {o.items?.map((x: any) => (
                  <span key={x.id}>
                    {x.quantity}× {x.name}
                  </span>
                ))}
              </div>
              <div className="order-actions">
                <Button
                  variant="secondary"
                  onClick={() =>
                    setNotice(
                      `Issue report opened for ${o.id}. In production this would create a supplier support case with the immutable receipt attached.`,
                    )
                  }
                >
                  Report issue
                </Button>
                <Button variant="secondary" onClick={() => nav('/app/diary')}>
                  Record field application
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Empty
          title="No order has been confirmed"
          detail="The demo marketplace is intentionally confirmation-gated."
        />
      )}
    </>
  );
}
