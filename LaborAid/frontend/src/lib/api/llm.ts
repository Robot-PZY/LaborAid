import { apiClient, TIMEOUT } from './client';
import type { LLMSetting, ActiveLLM, ConnectivityTestResult, LLMRuntimeSummary } from './types';

// ── LLM Settings API ──────────────────────────────────────────────────

export const llmSettingsApi = {
  list: async (): Promise<LLMSetting[]> => {
    const res = await apiClient.get('/llm-settings', { timeout: TIMEOUT.short });
    return res.data;
  },

  getActive: async (): Promise<ActiveLLM> => {
    const res = await apiClient.get('/llm-settings/active', { timeout: TIMEOUT.short });
    return res.data;
  },

  getActiveVision: async (): Promise<ActiveLLM> => {
    const res = await apiClient.get('/llm-settings/active-vision', { timeout: TIMEOUT.short });
    return res.data;
  },

  getRuntimeSummary: async (): Promise<LLMRuntimeSummary> => {
    const res = await apiClient.get('/llm-settings/runtime-summary', { timeout: TIMEOUT.short });
    return res.data;
  },

  testVisionConnectivity: async (data: {
    base_url: string;
    api_key: string;
    model_name: string;
    setting_id?: number;
  }): Promise<ConnectivityTestResult> => {
    const res = await apiClient.post('/llm-settings/test-vision-connectivity', data, {
      timeout: TIMEOUT.long,
    });
    return res.data;
  },

  create: async (data: {
    name: string;
    base_url: string;
    api_key: string;
    model_name: string;
    max_tokens: number;
    is_default: boolean;
  }): Promise<LLMSetting> => {
    const res = await apiClient.post('/llm-settings', data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  update: async (id: number, data: {
    name?: string;
    base_url?: string;
    api_key?: string;
    model_name?: string;
    max_tokens?: number;
    is_default?: boolean;
  }): Promise<LLMSetting> => {
    const res = await apiClient.put(`/llm-settings/${id}`, data, { timeout: TIMEOUT.medium });
    return res.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/llm-settings/${id}`, { timeout: TIMEOUT.medium });
  },

  testConnectivity: async (data: {
    base_url: string;
    api_key: string;
    model_name: string;
    setting_id?: number;
  }): Promise<ConnectivityTestResult> => {
    const res = await apiClient.post('/llm-settings/test-connectivity', data, { timeout: TIMEOUT.long });
    return res.data;
  },

  presets: async (): Promise<Record<string, unknown>[]> => {
    const res = await apiClient.get('/llm-settings/presets', { timeout: TIMEOUT.short });
    return res.data;
  },
};
