import { apiClient, TIMEOUT } from './client';

/** 管理端用户列表（含启用状态与注册时间） */
export interface AdminUser {
  id: number;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AdminStatsOverview {
  users_total: number;
  users_active: number;
  users_new_7d: number;
  cases_total: number;
  documents_total: number;
  evidence_total: number;
  research_total: number;
  llm_configured: boolean;
  vision_llm_configured: boolean;
  cases_with_description: number;
  cases_with_evidence: number;
  cases_material_ready: number;
  evidence_with_ocr: number;
  evidence_ocr_rate_pct: number;
  research_reports_7d: number;
  material_ready_rate_pct: number;
}

export interface UsageTrendDay {
  date: string;
  cases: number;
  documents: number;
  evidence: number;
  research: number;
}

export const adminApi = {
  getStats: async (): Promise<AdminStatsOverview> => {
    const res = await apiClient.get('/admin/stats/overview', { timeout: TIMEOUT.medium });
    return res.data;
  },

  getUsageTrend: async (days = 7): Promise<UsageTrendDay[]> => {
    const res = await apiClient.get('/admin/stats/usage-trend', {
      params: { days },
      timeout: TIMEOUT.medium,
    });
    return res.data;
  },

  listUsers: async (): Promise<AdminUser[]> => {
    const res = await apiClient.get('/admin/users', { timeout: TIMEOUT.short });
    return res.data;
  },

  updateUser: async (
    id: number,
    data: { role?: string; is_active?: boolean },
  ): Promise<AdminUser> => {
    const res = await apiClient.patch(`/admin/users/${id}`, data, { timeout: TIMEOUT.short });
    return res.data;
  },

  getPerformance: async (): Promise<Record<string, unknown>> => {
    const res = await apiClient.get('/admin/performance', { timeout: TIMEOUT.short });
    return res.data;
  },
};
