import { firebaseAuth } from './firebase';

const BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

async function headers(json = true): Promise<Record<string, string>> {
  const token = firebaseAuth?.currentUser ? await firebaseAuth.currentUser.getIdToken().catch(() => null) : null;
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}`, 'X-Demo-User': firebaseAuth?.currentUser?.uid || 'demo_farmer_001' } : { 'X-Demo-User': 'demo_farmer_001' }),
  };
}

async function request<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { ...options, headers: { ...(await headers(!(options.body instanceof FormData))), ...(options.headers || {}) } });
  if (!response.ok) { const detail = await response.text(); throw new Error(detail || `Request failed: ${response.status}`) }
  return response.json();
}

export const platformApi = {
  health: () => request('/health'), me: () => request('/users/me'), saveProfile: (data: any) => request('/users/me', { method: 'PUT', body: JSON.stringify({ data }) }), requestAccountDeletion: () => request('/users/me', { method: 'DELETE' }), adminUsers: () => request('/admin/users'), adminVerify: (uid: string, verified = true) => request(`/admin/users/${uid}/verification`, { method: 'PATCH', body: JSON.stringify({ data: { verified } }) }),
  dashboard: () => request('/dashboard'), weather: (lat = 7.291, lon = 81.674, days = 14) => request(`/weather?lat=${lat}&lon=${lon}&days=${days}`),
  climateHistory: (lat = 7.291, lon = 81.674) => request(`/climate-history?lat=${lat}&lon=${lon}`), satellite: (lat = 7.291, lon = 81.674) => request(`/satellite/catalog?lat=${lat}&lon=${lon}`),
  farms: () => request('/farms'), addFarm: (data: any) => request('/farms', { method: 'POST', body: JSON.stringify({ data }) }), patchFarm: (id: string, data: any) => request(`/farms/${id}`, { method: 'PATCH', body: JSON.stringify({ data }) }),
  projects: () => request('/projects'), addProject: (data: any) => request('/projects', { method: 'POST', body: JSON.stringify({ data }) }),
  tasks: () => request('/tasks'), addTask: (data: any) => request('/tasks', { method: 'POST', body: JSON.stringify({ data }) }), patchTask: (id: string, data: any) => request(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  observations: () => request('/observations'), addObservation: (data: any) => request('/observations', { method: 'POST', body: JSON.stringify({ data }) }),
  expenses: () => request('/expenses'), addExpense: (data: any) => request('/expenses', { method: 'POST', body: JSON.stringify({ data }) }),
  harvests: () => request('/harvests'), addHarvest: (data: any) => request('/harvests', { method: 'POST', body: JSON.stringify({ data }) }),
  products: () => request('/products'), suppliers: () => request('/suppliers'), orders: () => request('/orders'), addOrder: (data: any) => request('/orders', { method: 'POST', body: JSON.stringify({ data }) }),
  expertCases: () => request('/expert-cases'), addExpertCase: (data: any) => request('/expert-cases', { method: 'POST', body: JSON.stringify({ data }) }), patchExpertCase: (id: string, data: any) => request(`/expert-cases/${id}`, { method: 'PATCH', body: JSON.stringify({ data }) }),
  notifications: () => request<any[]>('/notifications'),

  addNotification: (data: any) =>
    request('/notifications', {
      method: 'POST',
      body: JSON.stringify({ data }),
    }),

  ackNotification: (id: string) =>
    request(`/notifications/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        data: {
          acknowledged: true,
        },
      }),
    }),

  deviceToken: (token: string) =>
    request('/device-tokens', {
      method: 'POST',
      body: JSON.stringify({
        data: {
          token,
          platform: 'web',
        },
      }),
    }),

  community: () => request('/community'), addCommunity: (data: any) => request('/community', { method: 'POST', body: JSON.stringify({ data }) }), audit: () => request('/audit'), agentRuns: () => request('/agent-runs'), voiceSessionToken: (
    data: {
      language: string;
      project_id?: string;
    }
  ) =>
    request('/voice/session-token', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  ask: (question: string, context: any = {}) => request('/ask-ai', { method: 'POST', body: JSON.stringify({ question, context }) }),
  diagnose: async (files: File[], crop_hint: string, symptoms: string, project_id = '') => { const fd = new FormData(); files.slice(0, 4).forEach(file => fd.append('images', file)); fd.append('crop_hint', crop_hint); fd.append('symptoms', symptoms); fd.append('project_id', project_id); return request('/diagnose-image', { method: 'POST', body: fd }); }
};
