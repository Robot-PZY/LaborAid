import { apiClient, TIMEOUT, createCancelToken } from './client';
import type { AxiosRequestConfig } from 'axios';
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

// ── Research API ──────────────────────────────────────────────────────

export const researchApi = {
  create: async (data: {
    query: string;
    sources: string[];
    case_id?: number;
  }, cancelKey?: string): Promise<ResearchReport> => {
    const config: AxiosRequestConfig = { timeout: TIMEOUT.ai };
    if (cancelKey) {
      config.cancelToken = createCancelToken(cancelKey).token;
    }
    const res = await apiClient.post('/research', data, config);
    return res.data;
  },

  list: async (params?: {
    skip?: number;
    limit?: number;
    case_id?: number;
  }): Promise<ResearchReport[]> => {
    const res = await apiClient.get('/research', { params, timeout: TIMEOUT.short });
    return res.data;
  },

  get: async (id: number): Promise<ResearchReport> => {
    const res = await apiClient.get(`/research/${id}`, { timeout: TIMEOUT.short });
    return res.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/research/${id}`, { timeout: TIMEOUT.medium });
  },

  exportWord: async (id: number): Promise<Blob> => {
    const res = await apiClient.post(`/research/${id}/export`, { format: 'docx' }, {
      responseType: 'blob',
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  exportMarkdown: async (id: number): Promise<Blob> => {
    const res = await apiClient.post(`/research/${id}/export`, { format: 'markdown' }, {
      responseType: 'blob',
      timeout: TIMEOUT.long,
    });
    return res.data;
  },
};
