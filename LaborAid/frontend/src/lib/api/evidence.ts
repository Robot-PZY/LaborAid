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

// ── Evidence API ──────────────────────────────────────────────────────

export const evidenceApi = {
  list: async (caseId: number): Promise<EvidenceItem[]> => {
    const res = await apiClient.get('/evidence', { params: { case_id: caseId }, timeout: TIMEOUT.short });
    return res.data;
  },

  create: async (data: {
    case_id: number;
    type: string;
    title: string;
    tags?: string[];
  }): Promise<EvidenceItem> => {
    const res = await apiClient.post('/evidence', data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  upload: async (id: number, file: File): Promise<EvidenceItem> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post(`/evidence/${id}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  /** 选定案件后一步创建证据并上传，同步写入材料库 */
  quickUpload: async (
    caseId: number,
    file: File,
    opts?: { title?: string; evidence_type?: string },
  ): Promise<EvidenceItem> => {
    const formData = new FormData();
    formData.append('case_id', String(caseId));
    formData.append('file', file);
    if (opts?.title) formData.append('title', opts.title);
    if (opts?.evidence_type) formData.append('evidence_type', opts.evidence_type);
    const res = await apiClient.post('/evidence/quick-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  get: async (id: number): Promise<EvidenceItem> => {
    const res = await apiClient.get(`/evidence/${id}`, { timeout: TIMEOUT.short });
    return res.data;
  },

  update: async (id: number, data: {
    title?: string;
    type?: string;
    tags?: string[];
    sort_order?: number;
  }): Promise<EvidenceItem> => {
    const res = await apiClient.put(`/evidence/${id}`, data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/evidence/${id}`, { timeout: TIMEOUT.medium });
  },

  analyze: async (id: number): Promise<EvidenceItem> => {
    const res = await apiClient.post(`/evidence/${id}/analyze`, null, { timeout: TIMEOUT.ai });
    return res.data;
  },

  download: async (id: number): Promise<void> => {
    const res = await apiClient.get(`/evidence/${id}/download`, {
      responseType: 'blob',
      timeout: TIMEOUT.long,
    });
    const url = window.URL.createObjectURL(res.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = `evidence_${id}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },
};
