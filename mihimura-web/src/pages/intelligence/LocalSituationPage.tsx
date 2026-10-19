import { useEffect, useState } from 'react';
import { CloudRain, CloudSun, Droplets, MapPin, RefreshCcw, ThermometerSun, Wind } from 'lucide-react';
import { Card, Metric, Notice, Status, Button } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { useAuth } from '../../context/AuthContext';

export function LocalSituationPage() {
  const { profile } = useAuth();
  const [weather, setWeather] = useState<any>(null),
    [history, setHistory] = useState<any>(null);
  const lat = profile?.lat || 7.291,
    lon = profile?.lon || 81.674;
  const load = async () => {
    const [a, b] = await Promise.allSettled([
      platformApi.weather(lat, lon, 14),
      platformApi.climateHistory(lat, lon),
    ]);
    if (a.status === 'fulfilled') setWeather(a.value);
    if (b.status === 'fulfilled') setHistory(b.value);
  };
  useEffect(() => {
    void load();
  }, []);
  const rain = weather?.daily?.precipitation_probability_max?.[1] ?? 82;
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <MapPin /> GPS-aware local intelligence
          </span>
          <h2>{profile?.district || 'Ampara'} situation card</h2>
          <p>
            Current field context, near-term forecast and longer climate baseline are shown separately so
            freshness is not confused.
          </p>
        </div>
        <Button variant="secondary" onClick={() => void load()}>
          <RefreshCcw /> Refresh sources
        </Button>
      </section>
      <div className="dashboard-metrics">
        <Metric
          label="GPS context"
          value={`${lat.toFixed(3)}, ${lon.toFixed(3)}`}
          note={profile?.location_consent ? 'permission granted' : 'manual fallback'}
          icon={MapPin}
        />
        <Metric
          label="Heat index proxy"
          value="36°C"
          note="Watch during exposed operations"
          icon={ThermometerSun}
          tone="orange"
        />
        <Metric label="Forecast rain" value={`${rain}%`} note="Tomorrow" icon={CloudRain} tone="blue" />
        <Metric
          label="Wind"
          value={`${weather?.current?.wind_speed_10m ?? 11} km/h`}
          note="Current 10 m wind"
          icon={Wind}
        />
        <Metric
          label="Water wallet"
          value="6.2 days"
          note="estimated remaining"
          icon={Droplets}
          tone="blue"
        />
      </div>
      <div className="two-col">
        <Card title="Local risk card" subtitle="Field-level composite; each component remains visible">
          <div className="risk-table">
            {[
              ['Drought proxy', 24, 'green'],
              ['Flood / runoff', 76, 'orange'],
              ['Heat', 52, 'amber'],
              ['Wind exposure', 31, 'green'],
              ['Pest / disease cluster', 69, 'orange'],
            ].map(([t, v, c]: any) => (
              <div key={t}>
                <span>{t}</span>
                <i>
                  <em style={{ width: `${v}%` }} />
                </i>
                <Status tone={c}>{v}/100</Status>
              </div>
            ))}
          </div>
          <Notice tone="info" title="Data freshness">
            Live forecast source: {weather?.source || 'Open-Meteo fallback'}. Climate baseline:{' '}
            {history?.source || 'NASA POWER fallback'}. Official warnings should remain visible when they
            differ.
          </Notice>
        </Card>
        <Card title="Top three precautions" subtitle="Specific to the selected local situation">
          <ol className="number-actions">
            <li>
              <i>01</i>
              <div>
                <b>Review fertilizer timing before tomorrow</b>
                <p>
                  Do not apply a rate based only on AI; verify the approved crop protocol and the latest
                  rainfall window.
                </p>
              </div>
            </li>
            <li>
              <i>02</i>
              <div>
                <b>Clear drainage at the western edge</b>
                <p>Reduce runoff exposure before the forecast rain peak.</p>
              </div>
            </li>
            <li>
              <i>03</i>
              <div>
                <b>Inspect representative plants</b>
                <p>If symptoms remain, capture leaf front, leaf back, whole plant and field-wide evidence.</p>
              </div>
            </li>
          </ol>
        </Card>
      </div>
      <Card
        title="14-day operating window"
        subtitle="Forecast confidence generally decreases with horizon; use near-term days for consequential scheduling"
      >
        <div className="forecast-grid">
          {(weather?.daily?.time || Array.from({ length: 14 }, (_, i) => `Day ${i + 1}`))
            .slice(0, 14)
            .map((d: string, i: number) => (
              <div
                className={
                  (weather?.daily?.precipitation_probability_max?.[i] ??
                    [45, 82, 67, 39, 27, 51, 35][i % 7]) > 65
                    ? 'wet'
                    : ''
                }
                key={d}
              >
                <small>{d.slice(5) || d}</small>
                <CloudSun />
                <b>{weather?.daily?.temperature_2m_max?.[i] ?? 32}°</b>
                <span>
                  <Droplets /> {weather?.daily?.precipitation_probability_max?.[i] ?? 35}%
                </span>
              </div>
            ))}
        </div>
      </Card>
    </>
  );
}
