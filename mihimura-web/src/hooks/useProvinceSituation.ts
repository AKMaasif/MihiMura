import { useEffect, useState } from 'react';
import type { ProvinceSituation } from '../data/mockApi';
import { platformApi } from '../services/platformApi';

const EMPTY: ProvinceSituation = {
  live: false,
  generatedAt: '',
  source: 'Province situation has not loaded',
  provinces: {},
};

/** Live province risk indices shared by every Sri Lanka map (refreshes every 30 minutes). */
export function useProvinceSituation() {
  const [situation, setSituation] = useState<ProvinceSituation>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    const load = () =>
      platformApi
        .situation()
        .then((data) => {
          if (!alive || !data?.provinces) return;
          setSituation(data);
          setOffline(false);
          setError('');
        })
        .catch((reason) => {
          if (!alive) return;
          setSituation(EMPTY);
          setOffline(true);
          setError(reason instanceof Error ? reason.message : 'Live province data could not be loaded.');
        })
        .finally(() => alive && setLoading(false));
    void load();
    const id = window.setInterval(() => void load(), 30 * 60 * 1000);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  return { ...situation, loading, offline, error };
}

/** Short label such as "Live · updated 10:42" or an explicit offline/baseline state. */
export function situationLabel(situation: { live: boolean; generatedAt: string; offline?: boolean }) {
  if (situation.offline) return 'Offline · live province data could not be loaded';
  if (!situation.live) return 'Baseline · live data unavailable';
  const time = situation.generatedAt
    ? new Date(situation.generatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';
  return `Live · updated ${time}`;
}
