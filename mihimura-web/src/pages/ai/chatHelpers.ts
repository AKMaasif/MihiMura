import type { AppLanguage } from '../../context/LanguageContext';

export function projectContext(
  p: any,
  profile: any,
  lang: string,
  languageMode: 'auto' | AppLanguage = 'auto',
) {
  return {
    province: p?.province || '',
    location: p?.district || profile?.district || 'Sri Lanka',
    project_id: p?.id || '',
    farm_id: p?.farm_id || '',
    lat: p?.lat || profile?.lat || null,
    lon: p?.lon || profile?.lon || null,
    crop: p?.crop || '',
    stage: p?.stage || '',
    language: lang,
    language_mode: languageMode === 'auto' ? 'auto' : 'manual',
  };
}

export function messageText(m: any) {
  return String(m?.content ?? m?.text ?? '');
}

export function decisionFromMessage(message: any) {
  const metadata = message?.metadata || {};
  return metadata.decision || null;
}

export type AgentMode = 'auto' | 'simple_chat' | 'decision_support' | 'full_report';

export const AGENT_MODES: Array<{ id: AgentMode; label: string; description: string }> = [
  { id: 'auto', label: 'Auto', description: 'MihiMura detects the best workflow from each message.' },
  {
    id: 'simple_chat',
    label: 'Simple chat',
    description: 'Natural explanations and general farming conversation without unnecessary live tools.',
  },
  {
    id: 'decision_support',
    label: 'Decision support',
    description: 'Farm-grounded, current-data and safety-aware operational decisions.',
  },
  {
    id: 'full_report',
    label: 'Full report',
    description: 'Complete cultivation, equipment, inputs, costs, profit, harvest and marketing planning.',
  },
];

export function modeLabel(mode?: string) {
  return AGENT_MODES.find((x) => x.id === mode)?.label || 'Auto';
}

export function isAgentMode(value: any): value is AgentMode {
  return AGENT_MODES.some((x) => x.id === value);
}

export function thinkingCopy(mode: AgentMode) {
  if (mode === 'simple_chat') return 'Reading the conversation and preparing a clear answer…';
  if (mode === 'decision_support') return 'Checking farm context, current evidence and safety constraints…';
  if (mode === 'full_report') return 'Planning agronomy, resources, economics, risks and marketing sections…';
  return 'Understanding your intent and choosing the right MihiMura workflow…';
}

export type ChatLanguageMode = 'auto' | AppLanguage;

export function detectMessageLanguage(text: string, fallback: AppLanguage): AppLanguage {
  const sinhala = Array.from(text || '').filter((ch) => ch >= '\u0D80' && ch <= '\u0DFF').length;
  const tamil = Array.from(text || '').filter((ch) => ch >= '\u0B80' && ch <= '\u0BFF').length;
  const latin = (text.match(/[A-Za-z]/g) || []).length;
  if (sinhala >= 2 && sinhala >= tamil) return 'Sinhala';
  if (tamil >= 2 && tamil > sinhala) return 'Tamil';
  if (latin > 0) return 'English';
  return fallback;
}
