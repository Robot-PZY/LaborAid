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

// ── Documents API ──────────────────────────────────────────────────────

export const documentApi = {
  list: async (params?: {
    case_id?: number;
    type?: string;
    skip?: number;
    limit?: number;
  }): Promise<Document[]> => {
    const res = await apiClient.get('/documents', { params, timeout: TIMEOUT.short });
    return res.data;
  },

  generate: async (data: {
    type: string;
    case_facts: string;
    case_id?: number;
    template_id?: number;
    extra_instructions?: string;
    research_report_ids?: number[];
  }, cancelKey?: string): Promise<Document> => {
    const config: AxiosRequestConfig = { timeout: TIMEOUT.ai };
    if (cancelKey) {
      config.cancelToken = createCancelToken(cancelKey).token;
    }
    const res = await apiClient.post('/documents/generate', data, config);
    return res.data;
  },

  extractText: async (file: File): Promise<{ filename: string; text: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/documents/extract-text', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  get: async (id: number): Promise<Document> => {
    const res = await apiClient.get(`/documents/${id}`, { timeout: TIMEOUT.short });
    return res.data;
  },

  /** 法院标准版式预览 HTML（与 Word 导出同源解析） */
  renderPreview: async (content: string, title?: string): Promise<{ html: string; css: string }> => {
    const res = await apiClient.post(
      '/documents/preview/render',
      { content, title: title ?? null },
      { timeout: TIMEOUT.medium },
    );
    return res.data;
  },

  update: async (id: number, data: { title?: string; content?: string; status?: string }): Promise<Document> => {
    const res = await apiClient.put(`/documents/${id}`, data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  delete: async (id: number): Promise<{ message: string; id: number; files_removed?: number }> => {
    const res = await apiClient.delete(`/documents/${id}`, { timeout: TIMEOUT.medium });
    return res.data;
  },

  batchDelete: async (
    ids: number[],
  ): Promise<{
    message: string;
    deleted_count: number;
    not_found_count: number;
    files_removed?: number;
    deleted_ids?: number[];
  }> => {
    const res = await apiClient.post('/documents/batch-delete', { ids }, { timeout: TIMEOUT.medium });
    return res.data;
  },

  exportWord: async (id: number): Promise<Blob> => {
    const res = await apiClient.post(`/documents/${id}/export`, { format: 'docx' }, {
      responseType: 'blob',
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  exportMarkdown: async (id: number): Promise<Blob> => {
    const res = await apiClient.post(`/documents/${id}/export`, { format: 'markdown' }, {
      responseType: 'blob',
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  exportHtml: async (id: number): Promise<Blob> => {
    const res = await apiClient.post(`/documents/${id}/export`, { format: 'html' }, {
      responseType: 'blob',
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  exportPdf: async (id: number): Promise<Blob> => {
    const res = await apiClient.post(`/documents/${id}/export`, { format: 'pdf' }, {
      responseType: 'blob',
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  verifyLaws: async (id: number): Promise<{
    document_id: number;
    verification_results: Record<string, unknown>[];
    total: number;
  }> => {
    const res = await apiClient.post(`/documents/${id}/verify-laws`, null, {
      timeout: TIMEOUT.ai,
    });
    return res.data;
  },

  review: async (id: number): Promise<Document> => {
    const res = await apiClient.post(`/documents/${id}/review`, null, {
      timeout: TIMEOUT.ai,
    });
    return res.data;
  },

  generateBundle: async (data: {
    case_id?: number;
    doc_types?: string[];
    preset?: string;
    case_facts: string;
    extra_instructions?: string;
    research_report_ids?: number[];
  }): Promise<{ documents: Record<string, unknown>[]; consistency_check: Record<string, unknown>; total: number }> => {
    const res = await apiClient.post('/documents/generate-bundle', data, {
      timeout: TIMEOUT.ai,
    });
    return res.data;
  },

  generateStream: (
    data: {
      type: string;
      case_facts: string;
      case_id?: number;
      template_id?: number;
      extra_instructions?: string;
      research_report_ids?: number[];
    },
    onProgress: (event: { step: string; label: string; elapsed: number }) => void,
    onError: (error: string) => void,
    onComplete: (documentId: number) => void,
  ): AbortController => {
    const controller = new AbortController();
    const token = localStorage.getItem('token');

    fetch('/api/v1/documents/generate-stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token ? `Bearer ${token}` : '',
      },
      body: JSON.stringify(data),
      signal: controller.signal,
    }).then(async (response) => {
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: '生成失败' }));
        onError(err.detail || '生成失败');
        return;
      }
      const reader = response.body?.getReader();
      if (!reader) { onError('无法读取响应流'); return; }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));
              if (event.step === 'completed') {
                onComplete(event.document_id);
              } else if (event.step === 'error') {
                onError(event.error || event.label);
              } else {
                onProgress(event);
              }
            } catch { /* skip malformed events */ }
          }
        }
      }
    }).catch((e) => {
      if (e.name !== 'AbortError') onError('网络错误，请重试');
    });

    return controller;
  },

  qualityCheck: async (id: number): Promise<{
    document_id: number;
    quality_check: {
      passed: boolean;
      issues: Record<string, unknown>[];
      checks: Record<string, unknown>[];
      quality_score: number;
      summary: string;
    };
  }> => {
    const res = await apiClient.post(`/documents/${id}/quality-check`, null, {
      timeout: TIMEOUT.ai,
    });
    return res.data;
  },
};
