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

// ── Law Verification API ──────────────────────────────────────────────

export const lawVerifyApi = {
  verify: async (data: {
    law_name: string;
    article_number: string;
    quoted_text?: string;
  }): Promise<LawVerifyResult> => {
    const res = await apiClient.post('/law-verify/verify', data, { timeout: TIMEOUT.ai });
    return res.data;
  },

  verifyBatch: async (documentContent: string): Promise<{
    total_references: number;
    verified: LawVerifyResult[];
    warnings: string[];
  }> => {
    const res = await apiClient.post('/law-verify/verify-batch', {
      document_content: documentContent,
    }, { timeout: TIMEOUT.ai });
    return res.data;
  },
};
