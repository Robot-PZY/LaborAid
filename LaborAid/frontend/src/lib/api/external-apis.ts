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

// ── External API Config API ──────────────────────────────────────────────

export const externalApiConfigApi = {
  list: async (): Promise<ExternalApiConfig[]> => {
    const res = await apiClient.get('/external-apis', { timeout: TIMEOUT.short });
    return res.data;
  },

  create: async (data: Record<string, unknown>): Promise<ExternalApiConfig> => {
    const res = await apiClient.post('/external-apis', data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  update: async (id: number, data: Record<string, unknown>): Promise<ExternalApiConfig> => {
    const res = await apiClient.put(`/external-apis/${id}`, data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/external-apis/${id}`, { timeout: TIMEOUT.medium });
  },

  toggle: async (id: number): Promise<ExternalApiConfig> => {
    const res = await apiClient.post(`/external-apis/${id}/toggle`, null, { timeout: TIMEOUT.medium });
    return res.data;
  },

  test: async (id: number): Promise<{ success: boolean; message: string; latency_ms: number }> => {
    const res = await apiClient.post('/external-apis/test', { api_id: id }, { timeout: TIMEOUT.long });
    return res.data;
  },

  presets: async (): Promise<ExternalApiPreset[]> => {
    const res = await apiClient.get('/external-apis/presets', { timeout: TIMEOUT.short });
    return res.data;
  },
};
