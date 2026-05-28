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
  CrawlSeedsResponse,
  CrawlRunResponse,
  CrawlScheduleStatus,
  ExternalApiConfig,
  ExternalApiPreset,
  AppConfigItem,
  LawVerifyResult,
} from './types';

// ── Knowledge Base API ──────────────────────────────────────────────────

export const knowledgeApi = {
  list: async (params?: { skip?: number; limit?: number; tag?: string }): Promise<KnowledgeItem[]> => {
    const res = await apiClient.get('/knowledge', { params, timeout: TIMEOUT.short });
    return res.data;
  },

  create: async (data: {
    title: string;
    content: string;
    source?: string;
    tags?: string[];
    team_id?: number;
  }): Promise<KnowledgeItem> => {
    const res = await apiClient.post('/knowledge', data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  uploadFile: async (file: File): Promise<KnowledgeItem> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/knowledge/upload-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  get: async (id: number): Promise<KnowledgeItem> => {
    const res = await apiClient.get(`/knowledge/${id}`, { timeout: TIMEOUT.short });
    return res.data;
  },

  update: async (id: number, data: {
    title?: string;
    content?: string;
    source?: string;
    tags?: string[];
  }): Promise<KnowledgeItem> => {
    const res = await apiClient.put(`/knowledge/${id}`, data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/knowledge/${id}`, { timeout: TIMEOUT.medium });
  },

  stats: async (): Promise<KnowledgeStats> => {
    const res = await apiClient.get('/knowledge/stats', { timeout: TIMEOUT.short });
    return res.data;
  },

  search: async (q: string, skip?: number, limit?: number): Promise<KnowledgeItem[]> => {
    const res = await apiClient.get('/knowledge/search/results', {
      params: { q, skip, limit },
      timeout: TIMEOUT.short,
    });
    return res.data;
  },

  batchDelete: async (ids: number[]): Promise<{ message: string; deleted_count: number; not_found_count: number }> => {
    const res = await apiClient.post('/knowledge/batch-delete', ids, { timeout: TIMEOUT.medium });
    return res.data;
  },

  crawlSeeds: async (): Promise<CrawlSeedsResponse> => {
    const res = await apiClient.get('/knowledge/crawl/seeds', { timeout: TIMEOUT.short });
    return res.data;
  },

  crawlRun: async (data: {
    seed_ids?: string[];
    keywords?: string[];
    source_ids?: string[];
    include_statutes?: boolean;
    include_topic_discovery?: boolean;
    dry_run?: boolean;
  }): Promise<CrawlRunResponse> => {
    const res = await apiClient.post('/knowledge/crawl/run', data, { timeout: TIMEOUT.long });
    return res.data;
  },

  crawlStatus: async (): Promise<CrawlScheduleStatus> => {
    const res = await apiClient.get('/knowledge/crawl/status', { timeout: TIMEOUT.short });
    return res.data;
  },

  crawlSetSchedule: async (enabled: boolean): Promise<CrawlScheduleStatus> => {
    const res = await apiClient.put('/knowledge/crawl/schedule', { enabled }, { timeout: TIMEOUT.short });
    return res.data;
  },

  crawlRunScheduled: async (): Promise<CrawlScheduleStatus> => {
    const res = await apiClient.post('/knowledge/crawl/run-scheduled', {}, { timeout: TIMEOUT.long });
    return res.data;
  },

  seedBundle: async (): Promise<{ inserted: number; skipped: number; total: number }> => {
    const res = await apiClient.post('/knowledge/seed-bundle', {}, { timeout: TIMEOUT.medium });
    return res.data;
  },
};
