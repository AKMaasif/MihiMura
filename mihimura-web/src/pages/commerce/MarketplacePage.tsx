import { useEffect, useState } from 'react';
import { PackageCheck, ShieldCheck, ShoppingCart, Store } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Empty, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { type CartItem, getCart, saveCart } from './cart';

export function MarketplacePage() {
  const nav = useNavigate();
  const [products, setProducts] = useState<any[]>([]),
    [category, setCategory] = useState('All'),
    [cart, setCart] = useState<CartItem[]>(getCart()),
    [query, setQuery] = useState('');
  useEffect(() => {
    platformApi
      .products()
      .then(setProducts)
      .catch(() => setProducts([]));
  }, []);
  const add = (p: any) => {
    const ex = cart.find((x) => x.id === p.id);
    const next = ex
      ? cart.map((x) => (x.id === p.id ? { ...x, quantity: x.quantity + 1 } : x))
      : [...cart, { ...p, quantity: 1 }];
    setCart(next);
    saveCart(next);
  };
  const visible = products.filter(
    (x) =>
      (category === 'All' || x.category === category) &&
      `${x.name} ${x.specification} ${x.compatibility}`.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Store /> Agronomy-first commerce
          </span>
          <h2>Verified marketplace</h2>
          <p>
            Products are kept separate from agronomic ranking. Compatibility, safety and farmer confirmation
            come before an order.
          </p>
        </div>
        <Button onClick={() => nav('/app/cart')}>
          <ShoppingCart /> Cart · {cart.reduce((s, x) => s + x.quantity, 0)}
        </Button>
      </section>
      <Notice tone="info" title="Commercial neutrality">
        Supplier payment cannot influence the agronomic recommendation. Sponsored placement is not used in
        this build.
      </Notice>
      <div className="market-tools">
        <div className="filter-tabs">
          {['All', 'Seed', 'Monitoring', 'Equipment', 'Safety'].map((x) => (
            <button className={category === x ? 'active' : ''} onClick={() => setCategory(x)} key={x}>
              {x}
            </button>
          ))}
        </div>
        <input
          className="market-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search verified catalog…"
        />
      </div>
      {visible.length ? (
        <div className="product-grid">
          {visible.map((p) => (
            <article className="product-card" key={p.id}>
              <div className="product-art">
                <PackageCheck />
                <Status tone="green">Verified</Status>
              </div>
              <div className="product-info">
                <small>
                  {p.category} · {p.pack}
                </small>
                <h3>{p.name}</h3>
                <p>{p.specification}</p>
                <div className="supplier-inline">
                  <Store />
                  <span>
                    <b>{p.supplier}</b>
                    <small>
                      {p.distance} · {p.stock} in stock
                    </small>
                  </span>
                </div>
                <div className="safety-note">
                  <ShieldCheck />
                  <span>{p.safety}</span>
                </div>
                <div className="product-bottom">
                  <strong>LKR {Number(p.price).toLocaleString()}</strong>
                  <Button onClick={() => add(p)}>Add to cart</Button>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Card>
          <Empty title="No verified product matches this filter" />
        </Card>
      )}
    </>
  );
}
