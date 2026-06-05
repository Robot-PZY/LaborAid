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

// ── Auth API ───────────────────────────────────────────────────────────

export const authApi = {
  login: async (email: string, password: string): Promise<{ access_token: string; user: User }> => {
    const res = await apiClient.post('/auth/login', { email, password }, { timeout: TIMEOUT.medium });
    const token = res.data.access_token;
    localStorage.setItem('token', token);
    const userRes = await apiClient.get('/auth/me', { timeout: TIMEOUT.short });
    return { access_token: token, user: userRes.data };
  },

  register: async (data: {
    email: string;
    password: string;
    name: string;
  }): Promise<{ access_token: string; user: User }> => {
    await apiClient.post('/auth/register', data, { timeout: TIMEOUT.medium });
    const loginRes = await apiClient.post('/auth/login', {
      email: data.email,
      password: data.password,
    }, { timeout: TIMEOUT.medium });
    const token = loginRes.data.access_token;
    localStorage.setItem('token', token);
    const userRes = await apiClient.get('/auth/me', { timeout: TIMEOUT.short });
    return { access_token: token, user: userRes.data };
  },

  getMe: async (): Promise<User> => {
    const res = await apiClient.get('/auth/me', { timeout: TIMEOUT.short });
    return res.data;
  },

  updateMe: async (data: { name?: string }): Promise<User> => {
    const res = await apiClient.put('/auth/me', data, { timeout: TIMEOUT.short });
    return res.data;
  },
};
