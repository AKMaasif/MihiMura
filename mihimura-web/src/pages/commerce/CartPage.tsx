import { useEffect, useMemo, useState } from 'react';
import { PackageCheck, ShieldCheck, ShoppingCart, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Empty, Notice } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { type CartItem, getCart, saveCart } from './cart';

export function CartPage() {
  const nav = useNavigate();
  const [cart, setCartState] = useState<CartItem[]>(getCart()),
    [projects, setProjects] = useState<any[]>([]),
    [projectId, setProjectId] = useState(''),
    [confirmed, setConfirmed] = useState(false),
    [substitution, setSubstitution] = useState(false),
    [address, setAddress] = useState(''),
    [payment, setPayment] = useState('Cash on delivery'),
    [delivery, setDelivery] = useState('Standard cooperative delivery'),
    [notice, setNotice] = useState('');
  useEffect(() => {
    platformApi
      .projects()
      .then((x) => {
        setProjects(x);
        if (x[0]) {
          setProjectId(x[0].id);
          setAddress(`${x[0].farm_name}, ${x[0].district}`);
        }
      })
      .catch(() => {});
  }, []);
  const update = (id: string, q: number) => {
    const next =
      q <= 0 ? cart.filter((x) => x.id !== id) : cart.map((x) => (x.id === id ? { ...x, quantity: q } : x));
    setCartState(next);
    saveCart(next);
  };
  const total = useMemo(() => cart.reduce((s, x) => s + Number(x.price) * x.quantity, 0), [cart]);
  const order = async () => {
    if (!confirmed || !projectId) return;
    try {
      await platformApi.addOrder({
        project_id: projectId,
        items: cart,
        confirmed: true,
        substitution_permission: substitution,
        delivery_address: address,
        payment_method: payment,
        delivery_method: delivery,
      });
      saveCart([]);
      setCartState([]);
      nav('/app/orders');
    } catch (e: any) {
      setNotice(e.message);
    }
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <ShoppingCart /> Confirmation-gated checkout
          </span>
          <h2>Cart & final confirmation</h2>
          <p>
            No silent substitutions. Final item, quantity, price, project, delivery and consent remain visible
            before the order is created.
          </p>
        </div>
      </section>
      {notice && (
        <Notice tone="warning" title="Checkout">
          {notice}
        </Notice>
      )}
      <div className="cart-layout">
        <Card title="Selected items" subtitle={`${cart.length} verified catalog option(s)`}>
          {cart.length ? (
            <div className="cart-list">
              {cart.map((x) => (
                <div key={x.id}>
                  <PackageCheck />
                  <span>
                    <b>{x.name}</b>
                    <small>
                      {x.supplier} · {x.pack}
                    </small>
                  </span>
                  <div className="qty">
                    <button onClick={() => update(x.id, x.quantity - 1)}>−</button>
                    <b>{x.quantity}</b>
                    <button onClick={() => update(x.id, x.quantity + 1)}>+</button>
                  </div>
                  <strong>LKR {(Number(x.price) * x.quantity).toLocaleString()}</strong>
                  <button className="remove" onClick={() => update(x.id, 0)}>
                    <X />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <Empty
              title="Your cart is empty"
              detail="Open the verified marketplace after an agronomic action is justified."
            />
          )}
        </Card>
        <Card title="Delivery & confirmation">
          <label>
            Farm / project
            <select
              value={projectId}
              onChange={(e) => {
                setProjectId(e.target.value);
                const p = projects.find((x) => x.id === e.target.value);
                if (p) setAddress(`${p.farm_name}, ${p.district}`);
              }}
            >
              <option value="">Select project</option>
              {projects.map((p) => (
                <option value={p.id} key={p.id}>
                  {p.farm_name} · {p.crop}
                </option>
              ))}
            </select>
          </label>
          <label>
            Delivery address / instructions
            <input value={address} onChange={(e) => setAddress(e.target.value)} />
          </label>
          <label>
            Payment method
            <select value={payment} onChange={(e) => setPayment(e.target.value)}>
              <option>Cash on delivery</option>
              <option>Demo card payment</option>
              <option>Cooperative account</option>
            </select>
          </label>
          <label>
            Delivery method
            <select value={delivery} onChange={(e) => setDelivery(e.target.value)}>
              <option>Standard cooperative delivery</option>
              <option>Pickup</option>
              <option>Grouped farmer delivery</option>
            </select>
          </label>
          <div className="price-summary">
            <span>
              Items total <b>LKR {total.toLocaleString()}</b>
            </span>
            <span>
              Demo delivery <b>LKR {cart.length ? 450 : 0}</b>
            </span>
            <strong>
              Total <b>LKR {(total + (cart.length ? 450 : 0)).toLocaleString()}</b>
            </strong>
          </div>
          <Notice tone="warning" title="Final safety gate">
            Confirm compatibility, product label, quantity, weather and farm/project context before real-world
            use.
          </Notice>
          <label className="consent-check">
            <input
              type="checkbox"
              checked={substitution}
              onChange={(e) => setSubstitution(e.target.checked)}
            />
            Allow supplier substitution only after showing me an equivalent verified option for separate
            confirmation.
          </label>
          <label className="consent-check">
            <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />I
            confirm the selected project, items, quantities, prices and delivery details.
          </label>
          <Button disabled={!cart.length || !confirmed || !projectId} onClick={() => void order()}>
            <ShieldCheck /> Confirm demo order
          </Button>
        </Card>
      </div>
    </>
  );
}
