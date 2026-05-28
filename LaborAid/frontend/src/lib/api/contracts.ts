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

// ── Contract Review API ───────────────────────────────────────────────

export const contractApi = {
  list: async (caseId?: number): Promise<ContractItem[]> => {
    const res = await apiClient.get('/contracts', { params: { case_id: caseId }, timeout: TIMEOUT.short });
    return res.data;
  },

  draft: async (data: {
    title: string;
    description: string;
    case_id?: number;
    file?: File;
  }): Promise<ContractItem> => {
    const formData = new FormData();
    formData.append('title', data.title);
    formData.append('description', data.description);
    if (data.case_id) formData.append('case_id', String(data.case_id));
    if (data.file) formData.append('file', data.file);
    const res = await apiClient.post('/contracts/draft', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: TIMEOUT.ai,
    });
    return res.data;
  },

  upload: async (file: File, title: string, caseId?: number): Promise<ContractItem> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    if (caseId) formData.append('case_id', String(caseId));
    const res = await apiClient.post('/contracts/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  get: async (id: number): Promise<ContractItem> => {
    const res = await apiClient.get(`/contracts/${id}`, { timeout: TIMEOUT.short });
    return res.data;
  },

  review: async (id: number): Promise<ContractItem> => {
    const res = await apiClient.post(`/contracts/${id}/review`, null, { timeout: TIMEOUT.ai });
    return res.data;
  },

  exportReport: async (id: number, format: string = 'markdown'): Promise<Blob> => {
    const res = await apiClient.post(`/contracts/${id}/export`, { format }, {
      responseType: 'blob',
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/contracts/${id}`, { timeout: TIMEOUT.medium });
  },
};
