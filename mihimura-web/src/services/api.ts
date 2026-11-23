import { platformApi } from './platformApi';
export type DashboardPayload = any;
export async function fetchDashboard() {
  try {
    const payload = await platformApi.dashboard();
    return { ...payload, _connection: 'backend', _error: '' };
  } catch (error) {
    return {
      _connection: 'offline',
      _error: error instanceof Error ? error.message : 'The national overview could not be loaded.',
      live: false,
      generatedAt: '',
      source: 'unavailable',
      summary: null,
      provinces: {},
    };
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
