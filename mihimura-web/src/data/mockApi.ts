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

export interface DashboardSummary {
  cropHealth: number;
  cropHealthChange: number;
  atRiskArea: number;
  newlyAtRiskArea: number;
  waterDeficit: number;
  irrigationNeed: number;
  activeThreats: number;
  criticalThreats: number;
  yieldProtected: number;
  yieldProtectedChange: number;
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

export const dashboardSummary: DashboardSummary = {
  cropHealth: 64,
  cropHealthChange: 2.8,
  atRiskArea: 124,
  newlyAtRiskArea: 18,
  waterDeficit: 18,
  irrigationNeed: 36_400,
  activeThreats: 17,
  criticalThreats: 3,
  yieldProtected: 14.8,
  yieldProtectedChange: 1.7,
};

export const provinceData: Record<string, ProvinceData> = {
  Western: {
    id: 'WP', name: 'Western', healthScore: 82, rainfallRisk: 34, pestRisk: 22, trend: 4,
    activeAlerts: 1, rainfall7d: 45, rainfallAvgDiff: 5, cropCoverage: 45, atRiskArea: 6,
    soilMoisture: 38, topCrop: 'Vegetables', nextAction: 'Continue routine monitoring',
  },
  Central: {
    id: 'CP', name: 'Central', healthScore: 76, rainfallRisk: 62, pestRisk: 38, trend: 2,
    activeAlerts: 2, rainfall7d: 110, rainfallAvgDiff: 15, cropCoverage: 60, atRiskArea: 11,
    soilMoisture: 44, topCrop: 'Tea', nextAction: 'Inspect slope drainage channels',
  },
  Northern: {
    id: 'NP', name: 'Northern', healthScore: 74, rainfallRisk: 29, pestRisk: 44, trend: 1,
    activeAlerts: 2, rainfall7d: 25, rainfallAvgDiff: -10, cropCoverage: 55, atRiskArea: 14,
    soilMoisture: 31, topCrop: 'Paddy', nextAction: 'Monitor tank water levels',
  },
  Sabaragamuwa: {
    id: 'SG', name: 'Sabaragamuwa', healthScore: 64, rainfallRisk: 58, pestRisk: 47, trend: -1,
    activeAlerts: 2, rainfall7d: 85, rainfallAvgDiff: 0, cropCoverage: 65, atRiskArea: 13,
    soilMoisture: 41, topCrop: 'Rubber', nextAction: 'Check fungal symptoms after rainfall',
  },
  'North Central': {
    id: 'NC', name: 'North Central', healthScore: 58, rainfallRisk: 23, pestRisk: 51, trend: -3,
    activeAlerts: 4, rainfall7d: 15, rainfallAvgDiff: -25, cropCoverage: 80, atRiskArea: 21,
    soilMoisture: 24, topCrop: 'Paddy', nextAction: 'Plan supplemental irrigation',
  },
  Southern: {
    id: 'SP', name: 'Southern', healthScore: 55, rainfallRisk: 46, pestRisk: 57, trend: -2,
    activeAlerts: 3, rainfall7d: 40, rainfallAvgDiff: -5, cropCoverage: 50, atRiskArea: 12,
    soilMoisture: 29, topCrop: 'Tea', nextAction: 'Inspect chilli and vegetable plots',
  },
  Eastern: {
    id: 'EP', name: 'Eastern', healthScore: 48, rainfallRisk: 76, pestRisk: 69, trend: -6,
    activeAlerts: 5, rainfall7d: 68, rainfallAvgDiff: -12, cropCoverage: 71, atRiskArea: 24,
    soilMoisture: 22, topCrop: 'Chilli', nextAction: 'Delay urea and inspect pest hotspots',
  },
  'North Western': {
    id: 'NW', name: 'North Western', healthScore: 44, rainfallRisk: 18, pestRisk: 72, trend: -5,
    activeAlerts: 5, rainfall7d: 10, rainfallAvgDiff: -40, cropCoverage: 65, atRiskArea: 15,
    soilMoisture: 20, topCrop: 'Coconut', nextAction: 'Prioritise irrigation and pest scouting',
  },
  Uva: {
    id: 'UP', name: 'Uva', healthScore: 42, rainfallRisk: 31, pestRisk: 78, trend: -4,
    activeAlerts: 6, rainfall7d: 30, rainfallAvgDiff: -20, cropCoverage: 55, atRiskArea: 8,
    soilMoisture: 25, topCrop: 'Vegetables', nextAction: 'Inspect fall armyworm reports today',
  },
};

export const priorityActions: PriorityAction[] = [
  {
    id: 'action-1', province: 'Eastern', severity: 'Critical',
    title: 'Delay urea application',
    description: 'Heavy rainfall is expected across high-coverage chilli and paddy zones.',
    evidence: '76/100 rainfall risk · 68 mm observed · runoff probability elevated',
    deadline: 'Before 8:00 AM', impact: 'LKR 18,500 loss avoided', buttonText: 'Review action',
  },
  {
    id: 'action-2', province: 'Uva', severity: 'High',
    title: 'Scout fall armyworm hotspots',
    description: 'Farmer reports and climate conditions indicate increasing pest pressure.',
    evidence: '78/100 pest risk · 6 active alerts · 3 image reports pending',
    deadline: 'Due today', impact: 'Protect 8 acres', buttonText: 'Assign scout',
  },
  {
    id: 'action-3', province: 'North Central', severity: 'High',
    title: 'Schedule supplemental irrigation',
    description: 'Soil moisture is below the target range for current paddy growth stages.',
    evidence: '24% moisture · 25% rainfall deficit · 21 acres at risk',
    deadline: 'Within 24 hours', impact: '18,000 L recommended', buttonText: 'Schedule',
  },
  {
    id: 'action-4', province: 'Sabaragamuwa', severity: 'Medium',
    title: 'Verify fungal stress signals',
    description: 'Persistent humidity may increase leaf-disease pressure in rubber zones.',
    evidence: '85 mm rainfall · 47/100 pest risk · NDVI trend down 1 point',
    deadline: 'Due in 3 days', impact: 'Prevent spread', buttonText: 'Open evidence',
  },
];

export const changes: ChangeItem[] = [
  {
    id: 'change-1', title: '18 acres moved into high-risk status',
    detail: 'Most of the change occurred in Eastern and North Western provinces.',
    province: 'National', tone: 'danger',
  },
  {
    id: 'change-2', title: 'Rainfall risk increased by 14 points',
    detail: 'Eastern Province now has a 76/100 rainfall-risk score.',
    province: 'Eastern', tone: 'warning',
  },
  {
    id: 'change-3', title: 'Soil moisture recovered after irrigation',
    detail: 'Three monitored blocks in Western Province returned to the optimal range.',
    province: 'Western', tone: 'positive',
  },
  {
    id: 'change-4', title: 'Five new farmer observations received',
    detail: 'Three pest images and two irrigation reports are awaiting verification.',
    province: 'Uva', tone: 'info',
  },
];

export const agentActivity: AgentActivity[] = [
  { id: 'agent-1', agent: 'Satellite Agent', action: 'Detected an 11% vegetation-index decline in Eastern Province', time: '2 min ago', status: 'complete' },
  { id: 'agent-2', agent: 'Climate Agent', action: 'Updated the 7-day rainfall and heat-risk forecast', time: '3 min ago', status: 'complete' },
  { id: 'agent-3', agent: 'Vision Agent', action: 'Analysing three farmer crop images from Uva', time: 'Now', status: 'working' },
  { id: 'agent-4', agent: 'Intervention Agent', action: 'Generated four prioritised field actions', time: '6 min ago', status: 'complete' },
];

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
