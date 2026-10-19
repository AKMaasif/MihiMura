import { platformApi } from './platformApi';
export type DashboardPayload = any;
export async function fetchDashboard() {
  try {
    const payload = await platformApi.dashboard();
    return { ...payload, _connection: 'backend' };
  } catch {
    return import('../data/mockApi').then((m) => ({
      generatedAt: new Date().toISOString(),
      source: 'demo',
      _connection: 'demo',
      live: false,
      summary: {
        cropHealth: Math.round(
          Object.values(m.provinceData).reduce((sum, p) => sum + p.healthScore, 0) /
            Object.keys(m.provinceData).length,
        ),
        cropHealthChange: 0,
        atRiskArea: Object.values(m.provinceData).reduce((sum, p) => sum + p.atRiskArea, 0),
        newlyAtRiskArea: 0,
        waterDeficit: 0,
        irrigationNeed: 0,
        activeThreats: 0,
        criticalThreats: 0,
        provincesNeedingAction: Object.values(m.provinceData).filter((p) => p.healthScore < 60).length,
      },
      provinces: m.provinceData,
      priorityActions: [],
      changes: [],
      agentActivity: [],
    }));
  }
}
export async function askMihimura(question: string, province = 'Eastern') {
  return platformApi.ask(question, { province, lat: 7.291, lon: 81.674, scope: 'national-overview' });
}
