import { useEffect, useState } from 'react';
import { ArrowRight, Map, MapPin, Plus, Save, Sprout } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Empty, Notice, Status } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { districts } from '../../data/platformData';
import { useAuth } from '../../context/AuthContext';
import { farmBoundary } from './boundary';
import { provinces } from './farmShared';

export function FarmsPage() {
  const nav = useNavigate();
  const { profile } = useAuth();
  const [farms, setFarms] = useState<any[]>([]),
    [show, setShow] = useState(false),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState('');
  const [form, setForm] = useState<any>({
    name: '',
    district: profile?.district || 'Ampara',
    province: 'Eastern',
    area: 1,
    water_source: '',
    soil_type: '',
    land_type: '',
    crop: '',
    lat: profile?.lat || 7.291,
    lon: profile?.lon || 81.674,
  });
  const load = () =>
    platformApi
      .farms()
      .then(setFarms)
      .catch((e) => setNotice(`Farm data could not be loaded: ${e.message}`));
  useEffect(() => {
    void load();
  }, []);
  const locate = () =>
    navigator.geolocation?.getCurrentPosition(
      (p) => setForm((x: any) => ({ ...x, lat: p.coords.latitude, lon: p.coords.longitude })),
      () => setNotice('Location permission was unavailable. Manual coordinates remain available.'),
    );
  const add = async () => {
    if (!form.name || !form.district || Number(form.area) <= 0) {
      setNotice('Farm name, district and a positive area are required.');
      return;
    }
    setBusy(true);
    try {
      await platformApi.addFarm(form);
      setShow(false);
      setForm({ ...form, name: '', area: 1 });
      await load();
      setNotice('Farm created. Add or draw a boundary in Farm Map, then create a cultivation project.');
    } catch (e: any) {
      setNotice(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <Sprout /> Farm ownership & spatial memory
          </span>
          <h2>My farms</h2>
          <p>
            Each farm keeps a spatial identity, water source, soil context, managed area and active crop
            projects.
          </p>
        </div>
        <Button onClick={() => setShow(true)}>
          <Plus /> Add farm
        </Button>
      </section>
      {notice && (
        <Notice tone="info" title="Farm workspace">
          {notice}
        </Notice>
      )}
      {farms.length ? (
        <div className="farm-card-grid">
          {farms.map((f) => (
            <article className="farm-card" key={f.id}>
              <div className="farm-map-thumb">
                <Map />
                <span>{f.district}</span>
                <i />
              </div>
              <div className="farm-card-body">
                <div>
                  <Status tone={f.status === 'active' ? 'green' : 'gray'}>{f.status}</Status>
                  <small>{f.province} Province</small>
                </div>
                <h3>{f.name}</h3>
                <p>
                  {f.crop || 'No current crop'} · {f.area} acres
                </p>
                <dl>
                  <div>
                    <dt>Water</dt>
                    <dd>{f.water_source || 'Not recorded'}</dd>
                  </div>
                  <div>
                    <dt>Soil</dt>
                    <dd>{f.soil_type || 'Not recorded'}</dd>
                  </div>
                  <div>
                    <dt>Location</dt>
                    <dd>
                      {f.lat ? `${Number(f.lat).toFixed(3)}, ${Number(f.lon).toFixed(3)}` : 'Manual region'}
                    </dd>
                  </div>
                  <div>
                    <dt>Boundary</dt>
                    <dd>{farmBoundary(f).length ? 'Mapped' : 'Not mapped'}</dd>
                  </div>
                </dl>
                <div className="farm-card-actions">
                  <Button variant="secondary" onClick={() => nav(`/app/farm-map?farm=${f.id}`)}>
                    Open boundary
                  </Button>
                  <Button onClick={() => nav('/app/projects')}>
                    Projects <ArrowRight />
                  </Button>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Card>
          <Empty
            title="No farm has been added yet"
            detail="Create your first farm to activate spatial weather, crop projects and field-level decision support."
          />
          <div className="empty-actions">
            <Button onClick={() => setShow(true)}>
              <Plus /> Create first farm
            </Button>
          </div>
        </Card>
      )}
      {show && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <header>
              <div>
                <span className="eyebrow">New farm</span>
                <h2>Start the spatial identity</h2>
              </div>
              <button aria-label="Close" onClick={() => setShow(false)}>
                ×
              </button>
            </header>
            <div className="field-grid">
              <label>
                Farm name
                <input
                  autoFocus
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. East Paddy Block"
                />
              </label>
              <label>
                District
                <select
                  value={form.district}
                  onChange={(e) => setForm({ ...form, district: e.target.value })}
                >
                  {districts.map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
              </label>
              <label>
                Province
                <select
                  value={form.province}
                  onChange={(e) => setForm({ ...form, province: e.target.value })}
                >
                  {provinces.map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
              </label>
              <label>
                Area (acres)
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={form.area}
                  onChange={(e) => setForm({ ...form, area: Number(e.target.value) })}
                />
              </label>
              <label>
                Land type
                <input
                  value={form.land_type}
                  onChange={(e) => setForm({ ...form, land_type: e.target.value })}
                  placeholder="Lowland, upland…"
                />
              </label>
              <label>
                Water source
                <input
                  value={form.water_source}
                  onChange={(e) => setForm({ ...form, water_source: e.target.value })}
                  placeholder="Canal, well, rain-fed…"
                />
              </label>
              <label>
                Soil info
                <input
                  value={form.soil_type}
                  onChange={(e) => setForm({ ...form, soil_type: e.target.value })}
                  placeholder="Known soil class / observation"
                />
              </label>
              <label>
                Current crop <em>optional</em>
                <input value={form.crop} onChange={(e) => setForm({ ...form, crop: e.target.value })} />
              </label>
              <label>
                Latitude
                <input
                  type="number"
                  step="0.000001"
                  value={form.lat}
                  onChange={(e) => setForm({ ...form, lat: Number(e.target.value) })}
                />
              </label>
              <label>
                Longitude
                <input
                  type="number"
                  step="0.000001"
                  value={form.lon}
                  onChange={(e) => setForm({ ...form, lon: Number(e.target.value) })}
                />
              </label>
            </div>
            <Button variant="secondary" onClick={locate}>
              <MapPin /> Use current GPS for centroid
            </Button>
            <Notice tone="info" title="Boundary workflow">
              Save the farm first, then use Farm Map to draw or import the actual polygon. Production
              deployments should store polygons in PostGIS with capture accuracy and method.
            </Notice>
            <div className="modal-actions">
              <Button variant="ghost" onClick={() => setShow(false)}>
                Cancel
              </Button>
              <Button disabled={busy} onClick={() => void add()}>
                <Save /> {busy ? 'Saving…' : 'Save farm'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
