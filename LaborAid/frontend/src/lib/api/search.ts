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

// ── Search API ─────────────────────────────────────────────────────────

export const searchApi = {
  search: async (params: {
    query: string;
    result_type?: string;
    top_k?: number;
  }): Promise<SearchResults> => {
    const res = await apiClient.post('/search', params, { timeout: TIMEOUT.medium });
    return res.data;
  },
};
