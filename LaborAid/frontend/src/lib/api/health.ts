import { apiClient, TIMEOUT } from './client';

export interface LlmHealthStatus {
  status: 'ok' | 'not_configured' | 'timeout' | 'connection_error' | 'error';
  model?: string;
  latency_ms?: number;
  sample?: string;
  detail?: string;
  timeout_s?: number;
}

export const healthApi = {
  /** Lightweight LLM connectivity test (sends a tiny prompt). */
  checkLlm: async (): Promise<LlmHealthStatus> => {
    const res = await apiClient.get('/health/llm', { timeout: TIMEOUT.short });
    return res.data;
  },
};
