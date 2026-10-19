export const provinces = [
  'Eastern',
  'Western',
  'Central',
  'Southern',
  'Northern',
  'North Western',
  'North Central',
  'Uva',
  'Sabaragamuwa',
];

export const stageOrder = [
  'Planning',
  'Land preparation',
  'Establishment',
  'Vegetative',
  'Reproductive',
  'Maturity',
  'Harvest',
];

export const defaultProjectForm = {
  farm_id: '',
  crop: 'Paddy',
  variety: '',
  purpose: 'Food production',
  season: 'Yala',
  stage: 'Planning',
  start_date: new Date().toISOString().slice(0, 10),
  actual_start_date: '',
  target_harvest: '',
  irrigation_mode: '',
  seed_source: '',
  budget: 0,
  notes: '',
};

export function projectProgress(p: any) {
  if (p.start_date && p.target_harvest) {
    const a = Date.parse(p.start_date),
      b = Date.parse(p.target_harvest),
      n = Date.now();
    if (b > a) return Math.max(2, Math.min(100, Math.round(((n - a) / (b - a)) * 100)));
  }
  return Math.max(8, ((stageOrder.indexOf(p.stage) + 1) / stageOrder.length) * 100);
}
