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

// ── App Config API ──────────────────────────────────────────────────────

export const appConfigApi = {
  list: async (category?: string): Promise<AppConfigItem[]> => {
    const res = await apiClient.get('/app-config', { params: { category }, timeout: TIMEOUT.short });
    return res.data;
  },

  update: async (id: number, data: { config_value?: string; description?: string }): Promise<AppConfigItem> => {
    const res = await apiClient.put(`/app-config/${id}`, data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  batchUpdate: async (items: { config_key: string; config_value: string }[]): Promise<AppConfigItem[]> => {
    const res = await apiClient.post('/app-config/batch-update', items, { timeout: TIMEOUT.medium });
    return res.data;
  },

  resetVectorConnection: async (): Promise<{ message: string }> => {
    const res = await apiClient.post('/app-config/reset-vector-connection', null, { timeout: TIMEOUT.medium });
    return res.data;
  },
};
