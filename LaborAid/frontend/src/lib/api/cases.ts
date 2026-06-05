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

  getDocFacts: async (id: number): Promise<{ case_facts: string }> => {
    const res = await apiClient.get(`/cases/${id}/doc-facts`, { timeout: TIMEOUT.short });
    return res.data;
  },

  getDocRecommendations: async (id: number): Promise<CaseDocRecommendations> => {
    const res = await apiClient.get(`/cases/${id}/doc-recommendations`, { timeout: TIMEOUT.medium });
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

  getAgentNextStep: async (
    id: number,
    opts?: { chainScore?: number },
  ): Promise<CaseAgentNextStep> => {
    const res = await apiClient.get(`/cases/${id}/agent/next-step`, {
      timeout: TIMEOUT.short,
      params:
        opts?.chainScore != null ? { chain_score: opts.chainScore } : undefined,
    });
    return res.data;
  },

  getCaseAgents: async (
    id: number,
    opts?: { chainScore?: number },
  ): Promise<CaseAgentsList> => {
    const res = await apiClient.get(`/cases/${id}/agents`, {
      timeout: TIMEOUT.short,
      params:
        opts?.chainScore != null ? { chain_score: opts.chainScore } : undefined,
    });
    return res.data;
  },

  getCaseWorkflow: async (
    id: number,
    opts?: { chainScore?: number },
  ): Promise<CaseWorkflow> => {
    const res = await apiClient.get(`/cases/${id}/workflow`, {
      timeout: TIMEOUT.short,
      params:
        opts?.chainScore != null ? { chain_score: opts.chainScore } : undefined,
    });
    return res.data;
  },

  getAgentSnapshot: async (id: number): Promise<CaseAgentSnapshot> => {
    const res = await apiClient.get(`/cases/${id}/agent/snapshot`, { timeout: TIMEOUT.short });
    return res.data;
  },

  askAgent: async (
    id: number,
    question: string,
    opts?: { chainScore?: number },
  ): Promise<CaseAgentAskResponse> => {
    const res = await apiClient.post(
      `/cases/${id}/agent/ask`,
      { question },
      {
        timeout: TIMEOUT.ai,
        params:
          opts?.chainScore != null ? { chain_score: opts.chainScore } : undefined,
      },
    );
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

  runDocPipelineStream: (
    caseId: number,
    data: {
      doc_type: string;
      case_facts: string;
      extra_instructions?: string;
      skip_research?: boolean;
      research_report_ids?: number[];
    },
    onProgress: (event: DocPipelineProgressEvent) => void,
    onError: (error: string) => void,
    onComplete: (payload: {
      document_id: number;
      run_id?: string;
      quality_score?: number;
      quality_summary?: string;
      vault_archived?: boolean;
    }) => void,
  ): AbortController => {
    const controller = new AbortController();
    const token = localStorage.getItem('token');

    fetch(`/api/v1/cases/${caseId}/agent/doc-pipeline-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token ? `Bearer ${token}` : '',
      },
      body: JSON.stringify(data),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const err = await response.json().catch(() => ({ detail: '流水线启动失败' }));
          onError(err.detail || '流水线启动失败');
          return;
        }
        const reader = response.body?.getReader();
        if (!reader) {
          onError('无法读取响应流');
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';
        let finished = false;
        let lastDocumentId: number | null = null;

        const finish = (payload: {
          document_id: number;
          quality_score?: number;
          quality_summary?: string;
          vault_archived?: boolean;
        }) => {
          if (finished) return;
          finished = true;
          onComplete(payload);
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            try {
              const event = JSON.parse(line.slice(6)) as DocPipelineProgressEvent;
              if (event.document_id) {
                lastDocumentId = event.document_id;
              }
              if (event.step === 'completed' && event.document_id) {
                finish({
                  document_id: event.document_id,
                  quality_score: event.quality_score,
                  quality_summary: event.quality_summary,
                  vault_archived: event.vault_archived,
                });
              } else if (event.step === 'error') {
                if (lastDocumentId) {
                  finish({ document_id: lastDocumentId });
                } else if (!finished) {
                  onError(event.error || event.label || '流水线失败');
                }
              } else {
                onProgress(event);
              }
            } catch {
              /* skip malformed */
            }
          }
        }

        if (!finished && lastDocumentId) {
          finish({ document_id: lastDocumentId });
        }
      })
      .catch((e) => {
        if ((e as Error).name !== 'AbortError') onError('网络错误，请重试');
      });

    return controller;
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

export interface CaseAgentContext {
  case_id: number;
  cause_type?: string | null;
  cause_label?: string | null;
  channel_id?: string | null;
  documents_count: number;
  evidence_count: number;
  research_reports_count: number;
  has_intake_plan: boolean;
  readiness_score: number;
  combined_score?: number | null;
}

export interface CaseAgentAlternative {
  agent_id: string;
  label: string;
  route: string;
  reason: string;
}

export interface CaseAgentPipelineTask {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'done' | string;
  route: string;
  hint?: string | null;
  optional?: boolean;
}

export interface CaseAgentNextStep {
  case_id: number;
  agent_id: string;
  action: string;
  label: string;
  route: string;
  reason: string;
  explanation: string;
  pipeline_stage: string;
  workflow_stage?: string;
  blockers: string[];
  prefill: Record<string, unknown>;
  context: CaseAgentContext;
  alternatives: CaseAgentAlternative[];
  pipeline_tasks: CaseAgentPipelineTask[];
  disclaimer: string;
}

export interface CaseAgentSnapshot {
  case_id: number;
  snapshot: {
    last_next_step?: Record<string, unknown>;
    last_ask?: Record<string, unknown>;
    doc_pipeline_runs?: Array<{
      run_id: string;
      document_id?: number;
      quality_check?: { quality_score?: number; summary?: string };
      completed_at?: string;
      error?: string;
    }>;
    updated_at?: string;
  };
}

export type DocPipelineProgressEvent = {
  step: string;
  label: string;
  status?: string;
  document_id?: number;
  vault_archived?: boolean;
  quality_score?: number;
  quality_summary?: string;
  error?: string;
};

export interface CaseAgentAskResponse {
  case_id: number;
  answer: string;
  suggested_route: string;
  suggested_label: string;
  pipeline_stage: string;
  used_llm: boolean;
  disclaimer: string;
}

export type CaseAgentStatus = 'done' | 'active' | 'blocked' | 'idle' | 'optional';

export interface CaseAgentStatusItem {
  agent_id: string;
  name: string;
  role: string;
  status: CaseAgentStatus;
  summary: string;
  tool_ids: string[];
  blockers: string[];
  route: string;
  pipeline_stage?: string | null;
  suggested_label?: string | null;
  suggested_reason?: string | null;
}

export interface CaseAgentsList {
  case_id: number;
  active_agent_id: string | null;
  agents: CaseAgentStatusItem[];
  handoffs: { from_agent: string; to_agent: string; reason: string }[];
  supervisor_summary: string;
}

export type CaseWorkflowStepStatus = 'done' | 'active' | 'pending';

export interface CaseWorkflowStep {
  id: string;
  label: string;
  hint: string;
  status: CaseWorkflowStepStatus;
  route: string;
  agent_id?: string | null;
}

export interface CaseWorkflow {
  case_id: number;
  current_stage: string;
  progress: number;
  total_steps: number;
  steps: CaseWorkflowStep[];
  summary: string;
  ai_hint?: string | null;
  active_agent_id?: string | null;
}

export interface CaseDocRecommendationItem {
  doc_type: string;
  label: string;
  reason: string;
  priority: number;
  generated: boolean;
  document_id?: number | null;
}

export interface CaseDocRecommendations {
  cause_type: string;
  cause_label: string;
  summary: string;
  recommendations: CaseDocRecommendationItem[];
  case_facts_preview?: string | null;
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
  intake_checklist?: string[];
}
