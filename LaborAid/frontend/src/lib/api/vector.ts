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

// ── Vector API ────────────────────────────────────────────────────────

export const vectorApi = {
  ingest: async (collection: string, items: Record<string, unknown>[]): Promise<Record<string, unknown>> => {
    const res = await apiClient.post('/vector/ingest', { collection, items }, { timeout: TIMEOUT.long });
    return res.data;
  },

  search: async (query: string, collection: string = 'all', top_k: number = 10): Promise<Record<string, unknown>> => {
    const res = await apiClient.post('/vector/search', { query, collection, top_k }, { timeout: TIMEOUT.medium });
    return res.data;
  },

  stats: async (): Promise<VectorStats> => {
    const res = await apiClient.get('/vector/stats', { timeout: TIMEOUT.short });
    return res.data;
  },
};
