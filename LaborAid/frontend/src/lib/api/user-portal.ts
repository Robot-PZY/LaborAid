import apiClient, { TIMEOUT } from './client';

export type RecentKind = 'case' | 'document' | 'evidence' | 'research' | 'contract';

export interface UserRecentItem {
  id: number;
  kind: RecentKind;
  title: string;
  updated_at: string;
}

export interface UserOverview {
  cases: number;
  documents: number;
  evidence: number;
  research: number;
  contracts: number;
  vault_files: number;
  vault_bytes: number;
  recent: UserRecentItem[];
}

export const userPortalApi = {
  getOverview: () =>
    apiClient.get<UserOverview>('/user/overview', { timeout: TIMEOUT.short }).then((r) => r.data),
};
