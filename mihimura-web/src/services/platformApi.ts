import type { ProvinceSituation } from '../data/mockApi';
import { supabase, supabaseConfigured } from './supabase';

const BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';
const DEMO_KEY = 'mihimura_demo_session';

async function headers(json = true): Promise<Record<string, string>> {
  const base: Record<string, string> = json ? { 'Content-Type': 'application/json' } : {};

  if (supabase && supabaseConfigured) {
    const { data, error } = await supabase.auth.getSession();
    if (error) throw error;
    if (data.session?.access_token) {
      return { ...base, Authorization: `Bearer ${data.session.access_token}` };
    }
  }

  const rawDemo = localStorage.getItem(DEMO_KEY);
  if (rawDemo) {
    try {
      const demo = JSON.parse(rawDemo);
      return { ...base, 'X-Demo-User': demo?.uid || '00000000-0000-0000-0000-000000000001' };
    } catch {
      localStorage.removeItem(DEMO_KEY);
    }
  }

  return base;
}

/** Readable message from an API error body (FastAPI validation errors arrive as a list). */
async function errorMessage(response: Response): Promise<string> {
  const raw = await response.text();
  try {
    const parsed = JSON.parse(raw);
    const detail = parsed?.detail ?? parsed?.message;
    if (Array.isArray(detail)) {
      return detail
        .map((item: any) => {
          const field = Array.isArray(item?.loc) ? item.loc.filter((x: any) => x !== 'body').join('.') : '';
          return field ? `${field}: ${item?.msg}` : String(item?.msg ?? item);
        })
        .join('; ');
    }
    return typeof detail === 'string' ? detail : raw;
  } catch {
    return raw;
  }
}

async function request<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      ...(await headers(!(options.body instanceof FormData))),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    throw new Error((await errorMessage(response)) || `Request failed: ${response.status}`);
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return response.json();
  return (await response.text()) as T;
}

export const platformApi = {
  health: () => request('/health'),
  me: () => request('/users/me'),
  saveProfile: (data: any) => request('/users/me', { method: 'PUT', body: JSON.stringify({ data }) }),
  requestAccountDeletion: () => request('/users/me', { method: 'DELETE' }),
  adminUsers: () => request('/admin/users'),
  adminVerify: (uid: string, verified = true) =>
    request(`/admin/users/${uid}/verification`, {
      method: 'PATCH',
      body: JSON.stringify({ data: { verified } }),
    }),
  adminSetStatus: (uid: string, status: 'active' | 'suspended') =>
    request(`/admin/users/${uid}/status`, { method: 'PATCH', body: JSON.stringify({ data: { status } }) }),
  evaluationStatus: () => request('/evaluation/status'),
  evaluationCases: () => request<any[]>('/evaluation/cases'),
  evaluationRuns: (limit = 20) => request<any[]>(`/evaluation/runs?limit=${limit}`),
  evaluationRunDetail: (id: string) => request(`/evaluation/runs/${id}`),
  runEvaluation: (mode: 'policy' | 'live' = 'policy', case_ids: string[] = [], persist = true) =>
    request('/evaluation/run', { method: 'POST', body: JSON.stringify({ mode, case_ids, persist }) }),

  knowledgeSearch: (data: any) =>
    request('/knowledge/search', { method: 'POST', body: JSON.stringify({ data }) }),
  knowledgeDocuments: (status?: string, crop?: string) =>
    request<any[]>(
      `/knowledge/documents?${new URLSearchParams({ ...(status ? { status } : {}), ...(crop ? { crop } : {}) }).toString()}`,
    ),
  uploadKnowledgeDocument: (file: File, metadata: Record<string, any>) => {
    const fd = new FormData();
    fd.append('file', file);
    Object.entries(metadata).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') fd.append(key, String(value));
    });
    return request('/knowledge/documents', { method: 'POST', body: fd });
  },
  patchKnowledgeDocument: (id: string, data: any) =>
    request(`/knowledge/documents/${id}`, { method: 'PATCH', body: JSON.stringify({ data }) }),
  deleteKnowledgeDocument: (id: string) => request(`/knowledge/documents/${id}`, { method: 'DELETE' }),
  knowledgeIngestionJobs: (limit = 20) => request<any[]>(`/knowledge/ingestion-jobs?limit=${limit}`),
  knowledgeIngestionJob: (id: string) => request(`/knowledge/ingestion-jobs/${id}`),
  retryKnowledgeIngestion: (id: string) =>
    request(`/knowledge/ingestion-jobs/${id}/retry`, { method: 'POST' }),
  cancelKnowledgeIngestion: (id: string) =>
    request(`/knowledge/ingestion-jobs/${id}/cancel`, { method: 'POST' }),

  dashboard: () => request('/dashboard'),
  weather: (lat = 7.291, lon = 81.674, days = 14) => request(`/weather?lat=${lat}&lon=${lon}&days=${days}`),
  climateHistory: (lat = 7.291, lon = 81.674) => request(`/climate-history?lat=${lat}&lon=${lon}`),
  situation: () => request<ProvinceSituation>('/situation/provinces'),
  satellite: (lat = 7.291, lon = 81.674) => request(`/satellite/catalog?lat=${lat}&lon=${lon}`),

  farms: () => request('/farms'),
  addFarm: (data: any) => request('/farms', { method: 'POST', body: JSON.stringify({ data }) }),
  patchFarm: (id: string, data: any) =>
    request(`/farms/${id}`, { method: 'PATCH', body: JSON.stringify({ data }) }),
  projects: () => request('/projects'),
  addProject: (data: any) => request('/projects', { method: 'POST', body: JSON.stringify({ data }) }),
  tasks: () => request('/tasks'),
  addTask: (data: any) => request('/tasks', { method: 'POST', body: JSON.stringify({ data }) }),
  patchTask: (id: string, data: any) =>
    request(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  observations: () => request('/observations'),
  addObservation: (data: any) => request('/observations', { method: 'POST', body: JSON.stringify({ data }) }),
  expenses: () => request('/expenses'),
  addExpense: (data: any) => request('/expenses', { method: 'POST', body: JSON.stringify({ data }) }),
  harvests: () => request('/harvests'),
  addHarvest: (data: any) => request('/harvests', { method: 'POST', body: JSON.stringify({ data }) }),

  products: () => request('/products'),
  suppliers: () => request('/suppliers'),
  orders: () => request('/orders'),
  addOrder: (data: any) => request('/orders', { method: 'POST', body: JSON.stringify({ data }) }),
  expertCases: () => request('/expert-cases'),
  addExpertCase: (data: any) => request('/expert-cases', { method: 'POST', body: JSON.stringify({ data }) }),
  patchExpertCase: (id: string, data: any) =>
    request(`/expert-cases/${id}`, { method: 'PATCH', body: JSON.stringify({ data }) }),

  notifications: () => request<any[]>('/notifications'),
  addNotification: (data: any) =>
    request('/notifications', { method: 'POST', body: JSON.stringify({ data }) }),
  ackNotification: (id: string) =>
    request(`/notifications/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ data: { acknowledged: true } }),
    }),
  deviceToken: (token: string) =>
    request('/device-tokens', { method: 'POST', body: JSON.stringify({ data: { token, platform: 'web' } }) }),
  community: () => request('/community'),
  addCommunity: (data: any) => request('/community', { method: 'POST', body: JSON.stringify({ data }) }),
  audit: () => request('/audit'),
  agentRuns: () => request('/agent-runs'),

  conversations: () => request<any[]>('/conversations'),
  createConversation: (project_id?: string, title?: string) =>
    request('/conversations', {
      method: 'POST',
      body: JSON.stringify({ project_id: project_id || null, title: title || null }),
    }),
  conversationMessages: (id: string) => request<any[]>(`/conversations/${id}/messages`),
  conversationMemory: (id: string) => request(`/conversations/${id}/memory`),
  archiveConversation: (id: string) => request(`/conversations/${id}`, { method: 'DELETE' }),

  voiceSessionToken: (data: { language: string; project_id?: string }) =>
    request('/voice/session-token', { method: 'POST', body: JSON.stringify(data) }),
  voiceTts: async (text: string, language: string) => {
    const response = await fetch(`${BASE}/voice/tts`, {
      method: 'POST',
      headers: await headers(true),
      body: JSON.stringify({ text, language }),
    });
    if (!response.ok) {
      throw new Error((await errorMessage(response)) || `Voice TTS request failed: ${response.status}`);
    }
    return response.blob();
  },

  ask: (
    question: string,
    context: any = {},
    conversation_id?: string,
    clarification_answers: Record<string, any> = {},
    mode: 'auto' | 'simple_chat' | 'decision_support' | 'full_report' = 'auto',
    allow_mode_mismatch = false,
    resume_route = false,
  ) =>
    request('/ask-ai', {
      method: 'POST',
      body: JSON.stringify({
        question,
        context,
        conversation_id: conversation_id || null,
        clarification_answers,
        mode,
        allow_mode_mismatch,
        resume_route,
      }),
    }),

  reports: () => request<any[]>('/reports'),
  generateConversationReport: (conversationId: string) =>
    request(`/conversations/${conversationId}/reports`, { method: 'POST' }),

  diagnose: async (
    files: File[],
    crop_hint: string,
    symptoms: string,
    project_id = '',
    language = 'English',
  ) => {
    const fd = new FormData();
    files.slice(0, 4).forEach((file) => fd.append('images', file));
    fd.append('crop_hint', crop_hint);
    fd.append('symptoms', symptoms);
    fd.append('project_id', project_id);
    fd.append('language', language);
    return request('/diagnose-image', { method: 'POST', body: fd });
  },
};
