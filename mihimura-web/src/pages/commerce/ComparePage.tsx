import { useEffect, useState } from 'react';
import { PackageSearch } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';

export function ComparePage() {
  const nav = useNavigate();
  const [products, setProducts] = useState<any[]>([]),
    [ids, setIds] = useState<string[]>([]);
  useEffect(() => {
    platformApi
      .products()
      .then((x) => {
        setProducts(x);
        setIds(x.slice(0, 2).map((p: any) => p.id));
      })
      .catch(() => {});
  }, []);
  const selected = products.filter((x) => ids.includes(x.id));
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <PackageSearch /> Transparent selection
          </span>
          <h2>Compare verified options</h2>
          <p>
            Compare specification, safety, price, stock and supplier status without changing the underlying
            agronomic recommendation.
          </p>
        </div>
        <Button onClick={() => nav('/app/marketplace')}>Back to catalog</Button>
      </section>
      <Card title="Choose up to three products to compare">
        <div className="compare-picker">
          {products.map((p) => (
            <label key={p.id}>
              <input
                type="checkbox"
                checked={ids.includes(p.id)}
                disabled={!ids.includes(p.id) && ids.length >= 3}
                onChange={(e) =>
                  setIds((x) => (e.target.checked ? [...x, p.id] : x.filter((id) => id !== p.id)))
                }
              />
              <span>{p.name}</span>
            </label>
          ))}
        </div>
      </Card>
      {selected.length > 0 && (
        <div className="compare-table">
          <div className="compare-head">
            <span>Attribute</span>
            {selected.map((p) => (
              <b key={p.id}>{p.name}</b>
            ))}
          </div>
          {[
            ['Category', 'category'],
            ['Specification', 'specification'],
            ['Pack', 'pack'],
            ['Price', 'price'],
            ['Stock', 'stock'],
            ['Supplier', 'supplier'],
            ['Compatibility', 'compatibility'],
            ['Safety', 'safety'],
            ['Why shown', 'why'],
          ].map(([label, key]) => (
            <div key={key}>
              <strong>{label}</strong>
              {selected.map((p) => (
                <span key={p.id}>
                  {key === 'price' ? `LKR ${Number(p[key]).toLocaleString()}` : String(p[key])}
                </span>
              ))}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
