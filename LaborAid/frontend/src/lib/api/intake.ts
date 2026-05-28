import apiClient, { TIMEOUT } from './client';
import type { Case } from './types';
import type { IntakeActionPlan, IntakeSession } from '@/lib/intake-session';

export interface IntakeAnalyzeResult {
  cause_type: string;
  cause_label: string;
  summary: string;
  parties: { plaintiff?: string | null; defendant?: string | null };
  missing_info: string[];
  evidence_checklist: string[];
  recommended_tools: {
    agent_id: string;
    priority: number;
    reason: string;
    action: string;
    prefill: Record<string, unknown>;
  }[];
  official_links: { id: string; title: string; when?: string }[];
  credibility: { score: number; needs_human_review: boolean; reason: string };
  extracted_from_images: string;
  search_query: string;
  channel_id?: string | null;
  scenario_id?: string | null;
  action_plan?: IntakeActionPlan | null;
}

export const intakeApi = {
  analyze: async (text: string, images: File[] = []): Promise<IntakeAnalyzeResult> => {
    const form = new FormData();
    form.append('text', text);
    images.forEach((img) => form.append('images', img));
    const res = await apiClient.post<IntakeAnalyzeResult>('/intake/analyze', form, {
      timeout: TIMEOUT.ai,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  createCase: async (payload: {
    title: string;
    case_type?: string;
    description?: string;
    plaintiff?: string;
    defendant?: string;
    cause_type?: string;
  }): Promise<Case> => {
    const res = await apiClient.post<Case>('/intake/create-case', payload);
    return res.data;
  },

  exportCasePack: async (caseId: number): Promise<Blob> => {
    const res = await apiClient.get(`/cases/${caseId}/export-pack`, {
      responseType: 'blob',
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  getSession: async (): Promise<{ session: IntakeSession; updated_at: string } | null> => {
    const res = await apiClient.get<{ session: IntakeSession; updated_at: string } | null>(
      '/intake/session',
      { timeout: TIMEOUT.short },
    );
    return res.data ?? null;
  },

  saveSession: async (session: IntakeSession): Promise<{ session: IntakeSession; updated_at: string }> => {
    const res = await apiClient.put<{ session: IntakeSession; updated_at: string }>(
      '/intake/session',
      { session },
      { timeout: TIMEOUT.medium },
    );
    return res.data;
  },

  clearSession: async (): Promise<void> => {
    await apiClient.delete('/intake/session', { timeout: TIMEOUT.short });
  },
};
