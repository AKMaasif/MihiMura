import { useEffect, useState } from 'react';
import { provinceData, type ProvinceSituation } from '../data/mockApi';
import { platformApi } from '../services/platformApi';

const BASELINE: ProvinceSituation = {
  live: false,
  generatedAt: '',
  source: 'Baseline reference values (live data unavailable)',
  provinces: provinceData,
};

/** Live province risk indices shared by every Sri Lanka map (refreshes every 30 minutes). */
export function useProvinceSituation() {
  const [situation, setSituation] = useState<ProvinceSituation>(BASELINE);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const load = () =>
      platformApi
        .situation()
        .then((data) => alive && data?.provinces && setSituation(data))
        .catch(() => alive && setSituation(BASELINE))
        .finally(() => alive && setLoading(false));
    void load();
    const id = window.setInterval(() => void load(), 30 * 60 * 1000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  return { ...situation, loading };
}

/** Short label such as "Live · updated 10:42" or "Baseline · live data unavailable". */
export function situationLabel(situation: { live: boolean; generatedAt: string }) {
  if (!situation.live) return 'Baseline · live data unavailable';
  const time = situation.generatedAt
    ? new Date(situation.generatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';
  return `Live · updated ${time}`;
}
