export type RiskLevel = 'Healthy' | 'Watch' | 'Moderate Risk' | 'High Risk';
export type MapLayer = 'cropHealth' | 'rainfallRisk' | 'pestRisk';

export interface ProvinceData {
  id: string;
  name: string;
  healthScore: number;
  rainfallRisk: number;
  pestRisk: number;
  trend: number;
  activeAlerts: number;
  rainfall7d: number;
  rainfallAvgDiff: number;
  cropCoverage: number;
  atRiskArea: number;
  soilMoisture: number;
  topCrop: string;
  nextAction: string;
}

export interface PriorityAction {
  id: string;
  province: string;
  severity: 'Critical' | 'High' | 'Medium';
  title: string;
  description: string;
  evidence: string;
  deadline: string;
  impact: string;
  buttonText: string;
}

export interface ChangeItem {
  id: string;
  title: string;
  detail: string;
  province: string;
  tone: 'danger' | 'warning' | 'positive' | 'info';
}

export interface AgentActivity {
  id: string;
  agent: string;
  action: string;
  time: string;
  status: 'complete' | 'working';
}

export const provinceData: Record<string, ProvinceData> = {
  Western: {
    id: 'WP',
    name: 'Western',
    healthScore: 82,
    rainfallRisk: 34,
    pestRisk: 22,
    trend: 4,
    activeAlerts: 1,
    rainfall7d: 45,
    rainfallAvgDiff: 5,
    cropCoverage: 45,
    atRiskArea: 6,
    soilMoisture: 38,
    topCrop: 'Vegetables',
    nextAction: 'Continue routine monitoring',
  },
  Central: {
    id: 'CP',
    name: 'Central',
    healthScore: 76,
    rainfallRisk: 62,
    pestRisk: 38,
    trend: 2,
    activeAlerts: 2,
    rainfall7d: 110,
    rainfallAvgDiff: 15,
    cropCoverage: 60,
    atRiskArea: 11,
    soilMoisture: 44,
    topCrop: 'Tea',
    nextAction: 'Inspect slope drainage channels',
  },
  Northern: {
    id: 'NP',
    name: 'Northern',
    healthScore: 74,
    rainfallRisk: 29,
    pestRisk: 44,
    trend: 1,
    activeAlerts: 2,
    rainfall7d: 25,
    rainfallAvgDiff: -10,
    cropCoverage: 55,
    atRiskArea: 14,
    soilMoisture: 31,
    topCrop: 'Paddy',
    nextAction: 'Monitor tank water levels',
  },
  Sabaragamuwa: {
    id: 'SG',
    name: 'Sabaragamuwa',
    healthScore: 64,
    rainfallRisk: 58,
    pestRisk: 47,
    trend: -1,
    activeAlerts: 2,
    rainfall7d: 85,
    rainfallAvgDiff: 0,
    cropCoverage: 65,
    atRiskArea: 13,
    soilMoisture: 41,
    topCrop: 'Rubber',
    nextAction: 'Check fungal symptoms after rainfall',
  },
  'North Central': {
    id: 'NC',
    name: 'North Central',
    healthScore: 58,
    rainfallRisk: 23,
    pestRisk: 51,
    trend: -3,
    activeAlerts: 4,
    rainfall7d: 15,
    rainfallAvgDiff: -25,
    cropCoverage: 80,
    atRiskArea: 21,
    soilMoisture: 24,
    topCrop: 'Paddy',
    nextAction: 'Plan supplemental irrigation',
  },
  Southern: {
    id: 'SP',
    name: 'Southern',
    healthScore: 55,
    rainfallRisk: 46,
    pestRisk: 57,
    trend: -2,
    activeAlerts: 3,
    rainfall7d: 40,
    rainfallAvgDiff: -5,
    cropCoverage: 50,
    atRiskArea: 12,
    soilMoisture: 29,
    topCrop: 'Tea',
    nextAction: 'Inspect chilli and vegetable plots',
  },
  Eastern: {
    id: 'EP',
    name: 'Eastern',
    healthScore: 48,
    rainfallRisk: 76,
    pestRisk: 69,
    trend: -6,
    activeAlerts: 5,
    rainfall7d: 68,
    rainfallAvgDiff: -12,
    cropCoverage: 71,
    atRiskArea: 24,
    soilMoisture: 22,
    topCrop: 'Chilli',
    nextAction: 'Delay urea and inspect pest hotspots',
  },
  'North Western': {
    id: 'NW',
    name: 'North Western',
    healthScore: 44,
    rainfallRisk: 18,
    pestRisk: 72,
    trend: -5,
    activeAlerts: 5,
    rainfall7d: 10,
    rainfallAvgDiff: -40,
    cropCoverage: 65,
    atRiskArea: 15,
    soilMoisture: 20,
    topCrop: 'Coconut',
    nextAction: 'Prioritise irrigation and pest scouting',
  },
  Uva: {
    id: 'UP',
    name: 'Uva',
    healthScore: 42,
    rainfallRisk: 31,
    pestRisk: 78,
    trend: -4,
    activeAlerts: 6,
    rainfall7d: 30,
    rainfallAvgDiff: -20,
    cropCoverage: 55,
    atRiskArea: 8,
    soilMoisture: 25,
    topCrop: 'Vegetables',
    nextAction: 'Inspect fall armyworm reports today',
  },
};

export const provinceLabelPositions: Record<string, { x: number; y: number; short: string }> = {
  Northern: { x: 183, y: 120, short: 'Northern' },
  'North Central': { x: 228, y: 325, short: 'North Central' },
  'North Western': { x: 120, y: 390, short: 'North Western' },
  Eastern: { x: 342, y: 405, short: 'Eastern' },
  Central: { x: 208, y: 510, short: 'Central' },
  Western: { x: 74, y: 590, short: 'Western' },
  Sabaragamuwa: { x: 164, y: 605, short: 'Sabaragamuwa' },
  Uva: { x: 274, y: 604, short: 'Uva' },
  Southern: { x: 180, y: 715, short: 'Southern' },
};
