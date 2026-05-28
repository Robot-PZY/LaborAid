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

// ── Evidence Chain & Cross-examination API ──────────────────────────────

export const evidenceChainApi = {
  analyzeChain: async (caseId: number): Promise<ChainAnalysisResult> => {
    const res = await apiClient.post(`/evidence/chain-analysis/${caseId}`, null, { timeout: TIMEOUT.ai });
    return res.data;
  },

  crossExamination: async (evidenceId: number): Promise<{ cross_examination: string }> => {
    const res = await apiClient.post(`/evidence/${evidenceId}/cross-examination`, null, { timeout: TIMEOUT.ai });
    return res.data;
  },
};
