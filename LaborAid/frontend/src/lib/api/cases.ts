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

// ── Cases API ──────────────────────────────────────────────────────────

export const caseApi = {
  list: async (params?: {
    status?: string;
    case_type?: string;
    skip?: number;
    limit?: number;
  }): Promise<Case[]> => {
    const res = await apiClient.get('/cases', { params, timeout: TIMEOUT.short });
    return res.data;
  },

  create: async (data: CaseCreate): Promise<Case> => {
    const res = await apiClient.post('/cases', data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  get: async (id: number): Promise<Case> => {
    const res = await apiClient.get(`/cases/${id}`, { timeout: TIMEOUT.short });
    return res.data;
  },

  update: async (id: number, data: Partial<CaseCreate & { status: string }>): Promise<Case> => {
    const res = await apiClient.put(`/cases/${id}`, data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  analyze: async (id: number): Promise<{ case_id: number; analysis: string }> => {
    const res = await apiClient.post(`/cases/${id}/analyze`, null, { timeout: TIMEOUT.ai });
    return res.data;
  },

  getMaterials: async (id: number): Promise<CaseMaterialsSummary> => {
    const res = await apiClient.get(`/cases/${id}/materials`, { timeout: TIMEOUT.short });
    return res.data;
  },

  getReadiness: async (
    id: number,
    opts?: { chainScore?: number },
  ): Promise<CaseReadinessSummary> => {
    const res = await apiClient.get(`/cases/${id}/readiness`, {
      timeout: TIMEOUT.short,
      params:
        opts?.chainScore != null ? { chain_score: opts.chainScore } : undefined,
    });
    return res.data;
  },

  createCaseReport: async (
    id: number,
    data?: { extra_notes?: string },
  ): Promise<ResearchReport> => {
    const res = await apiClient.post(`/cases/${id}/case-report`, data ?? {}, { timeout: TIMEOUT.ai });
    return res.data;
  },

  delete: async (id: number): Promise<{ message: string; id: number }> => {
    const res = await apiClient.delete(`/cases/${id}`, { timeout: TIMEOUT.medium });
    return res.data;
  },
};

export interface CaseMaterialsSummary {
  case_id: number;
  case_title: string;
  has_description: boolean;
  documents_count: number;
  evidence_count: number;
  documents: { id: number; title: string; type: string; status: string; updated_at: string }[];
  evidence: { id: number; title: string; evidence_type: string; has_ocr: boolean }[];
  ready_for_analysis: boolean;
}

export interface CaseEvidenceSuggestion {
  item: string;
  status: 'missing' | 'covered' | 'optional';
  priority: 'required' | 'optional';
}

export interface CaseReadinessSummary {
  case_id: number;
  readiness_score: number;
  readiness_level: 'low' | 'medium' | 'high' | string;
  summary: string;
  strengths: string[];
  missing_items: string[];
  next_actions: { label: string; route: string; reason: string }[];
  cause_type?: string | null;
  cause_label?: string | null;
  evidence_suggestions?: CaseEvidenceSuggestion[];
  docgen_ready?: boolean;
  docgen_blockers?: string[];
  chain_completeness_score?: number | null;
  combined_score?: number | null;
}
