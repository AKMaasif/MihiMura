import { useEffect, useState } from 'react';
import { CloudRain, CloudSun, Droplets, MapPin, RefreshCcw, ThermometerSun, Wind } from 'lucide-react';
import { Card, Metric, Notice, Button } from '../../components/common/UI';
import { platformApi } from '../../services/platformApi';
import { coordinatePair } from '../../services/location';
import { useAuth } from '../../context/AuthContext';

export function LocalSituationPage() {
  const { profile } = useAuth();
  const [weather, setWeather] = useState<any>(null),
    [history, setHistory] = useState<any>(null),
    [error, setError] = useState('');
  const coords = coordinatePair(profile?.lat, profile?.lon);
  const load = async () => {
    if (!coords) {
      setWeather(null);
      setHistory(null);
      setError('Add a farm or profile location before requesting a local forecast. No default district was used.');
      return;
    }
    setError('');
    const [a, b] = await Promise.allSettled([
      platformApi.weather(coords.lat, coords.lon, 14),
      platformApi.climateHistory(coords.lat, coords.lon),
    ]);
    if (a.status === 'fulfilled') setWeather(a.value);
    else setError(a.reason instanceof Error ? a.reason.message : 'The forecast could not be loaded.');
    if (b.status === 'fulfilled') setHistory(b.value);
  };
  useEffect(() => {
    void load();
  }, [profile?.lat, profile?.lon]);
  const live = Boolean(weather?.live);
  const rain = live ? weather?.daily?.precipitation_probability_max?.[1] : undefined;
  const temperature = live ? weather?.current?.temperature_2m : undefined;
  const wind = live ? weather?.current?.wind_speed_10m : undefined;
  return (
    <>
      <section className="page-intro">
        <div>
          <span className="eyebrow">
            <MapPin /> GPS-aware local intelligence
          </span>
          <h2>{profile?.district || 'Your district'} situation card</h2>
          <p>
            Current field context, near-term forecast and longer climate baseline are shown separately so
            freshness is not confused.
          </p>
        </div>
        <Button variant="secondary" onClick={() => void load()}>
          <RefreshCcw /> Refresh sources
        </Button>
      </section>
      {error && (
        <Notice tone="warning" title="Local forecast">
          {error}
        </Notice>
      )}
      <div className="dashboard-metrics">
        <Metric
          label="GPS context"
          value={coords ? `${coords.lat.toFixed(3)}, ${coords.lon.toFixed(3)}` : 'Not set'}
          note={coords ? (profile?.location_consent ? 'permission granted' : 'saved profile location') : 'no default coordinate'}
          icon={MapPin}
        />
        <Metric
          label="Temperature"
          value={temperature == null ? '—' : `${temperature}°C`}
          note={live ? 'Current 2 m temperature' : 'Shown only from a live forecast'}
          icon={ThermometerSun}
          tone="orange"
        />
        <Metric
          label="Forecast rain"
          value={rain == null ? '—' : `${rain}%`}
          note={live ? 'Tomorrow' : 'Live forecast unavailable'}
          icon={CloudRain}
          tone="blue"
        />
        <Metric
          label="Wind"
          value={wind == null ? '—' : `${wind} km/h`}
          note="Current 10 m wind"
          icon={Wind}
        />
        <Metric
          label="Water wallet"
          value="Not calculated"
          note="Needs a verified soil and crop coefficient"
          icon={Droplets}
          tone="blue"
        />
      </div>
      <div className="two-col">
        <Card title="Local risk card" subtitle="Field-level composite; each component remains visible">
          <Notice tone="info" title="Composite scores">
            Drought, flood, heat and pest scores are not shown here until a verified local model returns them.
            Sample percentages are not used as a stand-in.
          </Notice>
          <Notice tone="info" title="Data freshness">
            Forecast: {live ? weather?.source || 'live source' : weather?.source || 'not loaded'}
            {weather && !live ? ' (not valid for a field decision)' : ''}. Climate baseline:{' '}
            {history?.live ? history?.source || 'loaded' : history?.source || 'not loaded'}.
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
                <b>Check drainage before heavy rain</b>
                <p>Use the live forecast above. Do not assume a rain peak that was not returned.</p>
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
        {live && Array.isArray(weather?.daily?.time) ? (
          <div className="forecast-grid">
            {weather.daily.time.slice(0, 14).map((d: string, i: number) => (
              <div
                className={(weather.daily.precipitation_probability_max?.[i] ?? 0) > 65 ? 'wet' : ''}
                key={d}
              >
                <small>{String(d).slice(5) || d}</small>
                <CloudSun />
                <b>
                  {weather.daily.temperature_2m_max?.[i] == null ? '—' : `${weather.daily.temperature_2m_max[i]}°`}
                </b>
                <span>
                  <Droplets />{' '}
                  {weather.daily.precipitation_probability_max?.[i] == null
                    ? '—'
                    : `${weather.daily.precipitation_probability_max[i]}%`}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <Notice tone="warning" title="Forecast window">
            No live daily forecast is available for this location.
          </Notice>
        )}
      </Card>
    </>
  );
}
