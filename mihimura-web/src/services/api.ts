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
/** Main district used as the location when a whole province is selected on the map. */
export const PROVINCE_MAIN_DISTRICT: Record<string, string> = {
  Western: 'Colombo',
  Central: 'Kandy',
  Southern: 'Galle',
  Northern: 'Jaffna',
  Eastern: 'Ampara',
  'North Western': 'Kurunegala',
  'North Central': 'Anuradhapura',
  Uva: 'Badulla',
  Sabaragamuwa: 'Ratnapura',
};

/** Ask the agents about a province selected on the national map, keeping one conversation. */
export async function askMihimura(
  question: string,
  province = 'Eastern',
  conversationId?: string,
  language = 'English',
) {
  return platformApi.ask(
    question,
    {
      district: PROVINCE_MAIN_DISTRICT[province] || 'Ampara',
      language,
      language_mode: 'auto',
      scope: 'national-overview',
    },
    conversationId,
  );
}
