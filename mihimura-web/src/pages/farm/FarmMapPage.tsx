import { useEffect, useRef, useState } from 'react';
import { ArrowRight, MapPin, Save, Sprout, Upload } from 'lucide-react';
import { Button, Card, Empty, Notice } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { farmBoundary, fromCanvas, toCanvas } from './boundary';

export function FarmMapPage() {
  const [farms, setFarms] = useState<any[]>([]),
    [active, setActive] = useState<any>(null),
    [points, setPoints] = useState<{ x: number; y: number }[]>([]),
    [mode, setMode] = useState<'view' | 'draw'>('view'),
    [importText, setImportText] = useState(''),
    [notice, setNotice] = useState('');
  const svgRef = useRef<SVGSVGElement>(null);
  const load = () =>
    platformApi
      .farms()
      .then((x: any[]) => {
        setFarms(x);
        if (x.length && !active) {
          setActive(x[0]);
          setPoints(toCanvas(farmBoundary(x[0]), x[0]));
        }
      })
      .catch((e) => setNotice(e.message));
  useEffect(() => {
    void load();
  }, []);
  const choose = (f: any) => {
    setActive(f);
    setPoints(toCanvas(farmBoundary(f), f));
    setMode('view');
  };
  const clickMap = (e: any) => {
    if (mode !== 'draw' || !svgRef.current) return;
    const r = svgRef.current.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * 600,
      y = ((e.clientY - r.top) / r.height) * 380;
    setPoints((p) => [...p, { x, y }]);
  };
  const save = async () => {
    if (!active) return;
    if (points.length < 3) {
      setNotice('A field polygon needs at least three points.');
      return;
    }
    const boundary = fromCanvas(points, active);
    await platformApi.patchFarm(active.id, { boundary });
    setNotice(`Boundary saved with ${points.length} vertices.`);
    await load();
  };
  const importCoords = () => {
    try {
      const coords = importText
        .split(/\n|;/)
        .map((x) => x.trim())
        .filter(Boolean)
        .map((line) => line.split(',').map(Number))
        .filter((x) => x.length === 2 && !x.some(Number.isNaN));
      if (coords.length < 3) throw new Error('Need at least three lat,lon pairs');
      const lonLat = coords.map(([lat, lon]) => [lon, lat]);
      setPoints(toCanvas(lonLat, active));
      setMode('draw');
      setNotice(`${coords.length} coordinate points imported. Review the shape and save.`);
    } catch (e: any) {
      setNotice(e.message);
    }
  };
  const poly = points.map((p) => `${p.x},${p.y}`).join(' ');
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <MapPin /> Field boundary workspace
          </span>
          <h2>Farm map</h2>
          <p>
            Draw or import a polygon so risk, weather and satellite calculations can use the managed area
            rather than only a GPS point.
          </p>
        </div>
      </section>
      {notice && (
        <Notice tone="info" title="Boundary editor">
          {notice}
        </Notice>
      )}
      {farms.length ? (
        <div className="farm-map-layout">
          <Card title="Mapped farms" subtitle="Choose a farm context">
            <div className="farm-map-list">
              {farms.map((f) => (
                <button className={active?.id === f.id ? 'active' : ''} onClick={() => choose(f)} key={f.id}>
                  <Sprout />
                  <span>
                    <b>{f.name}</b>
                    <small>
                      {f.area} ac · {f.crop || 'No crop'}
                    </small>
                  </span>
                  <ArrowRight />
                </button>
              ))}
            </div>
            <div className="boundary-import">
              <label>
                Import lat,lon pairs
                <textarea
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                  placeholder={'7.2910,81.6700\n7.2960,81.6760\n7.2870,81.6800'}
                />
              </label>
              <Button variant="secondary" onClick={importCoords}>
                <Upload /> Import
              </Button>
            </div>
          </Card>
          <Card
            className="field-map-card"
            title={active?.name || 'Field boundary'}
            subtitle={`${active?.district || ''} · conceptual editor; preserve capture method/accuracy in production`}
          >
            <div className={`field-map-canvas ${mode === 'draw' ? 'drawing' : ''}`}>
              <div className="map-grid-bg" />
              <svg ref={svgRef} viewBox="0 0 600 380" onClick={clickMap}>
                {points.length >= 3 && <polygon points={poly} />}{' '}
                {points.map((p, i) => (
                  <g key={i}>
                    <circle cx={p.x} cy={p.y} r="7" />
                    <text x={p.x + 9} y={p.y - 9}>
                      {i + 1}
                    </text>
                  </g>
                ))}
              </svg>
              {active?.lat && (
                <div className="map-coordinate">
                  Centroid {Number(active.lat).toFixed(4)}, {Number(active.lon).toFixed(4)}
                </div>
              )}
            </div>
            <div className="map-toolbar">
              <Button
                variant={mode === 'draw' ? 'primary' : 'secondary'}
                onClick={() => setMode(mode === 'draw' ? 'view' : 'draw')}
              >
                <MapPin /> {mode === 'draw' ? 'Finish drawing' : 'Draw boundary'}
              </Button>
              <Button
                variant="secondary"
                disabled={!points.length}
                onClick={() => setPoints((p) => p.slice(0, -1))}
              >
                Undo point
              </Button>
              <Button variant="secondary" disabled={!points.length} onClick={() => setPoints([])}>
                Clear
              </Button>
              <Button disabled={points.length < 3} onClick={() => void save()}>
                <Save /> Save boundary
              </Button>
            </div>
          </Card>
        </div>
      ) : (
        <Card>
          <Empty title="Add a farm before mapping a boundary" />
          <div className="empty-actions">
            <Button onClick={() => (window.location.hash = '#/app/farms')}>Open My Farms</Button>
          </div>
        </Card>
      )}
    </>
  );
}
