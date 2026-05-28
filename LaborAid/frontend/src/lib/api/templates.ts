import { apiClient, TIMEOUT } from './client';
import type {
  User,
  Case,
  CaseCreate,
  Document,
  Template,
  SearchResults,
  EvidenceItem,
  LLMSetting,
  ActiveLLM,
  ConnectivityTestResult,
  ResearchReport,
  VectorStats,
  ContractItem,
  ChainAnalysisResult,
  KnowledgeItem,
  KnowledgeStats,
  ExternalApiConfig,
  ExternalApiPreset,
  AppConfigItem,
  LawVerifyResult,
} from './types';

// ── Templates API ──────────────────────────────────────────────────────

export const templateApi = {
  list: async (params?: { type?: string }): Promise<Template[]> => {
    const res = await apiClient.get('/templates', { params, timeout: TIMEOUT.short });
    return res.data;
  },

  create: async (data: Record<string, unknown>): Promise<Template> => {
    const res = await apiClient.post('/templates', data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  get: async (id: number): Promise<Template> => {
    const res = await apiClient.get(`/templates/${id}`, { timeout: TIMEOUT.short });
    return res.data;
  },

  update: async (id: number, data: Record<string, unknown>): Promise<Template> => {
    const res = await apiClient.put(`/templates/${id}`, data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/templates/${id}`, { timeout: TIMEOUT.medium });
  },

  seedPlatform: async (): Promise<{ message: string; ok: boolean }> => {
    const res = await apiClient.post('/templates/seed-platform', {}, { timeout: TIMEOUT.long });
    return res.data;
  },
};
