import apiClient, { TIMEOUT } from './client';

export interface UserMaterial {
  id: number;
  user_id: number;
  case_id: number | null;
  source: string;
  source_id: number | null;
  title: string;
  original_filename: string;
  mime_type: string | null;
  size_bytes: number;
  stage: string;
  tags: string[] | null;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface VaultStats {
  total_files: number;
  total_bytes: number;
  quota_bytes: number;
  by_stage: Record<string, number>;
}

export const vaultApi = {
  getStats: () =>
    apiClient.get<VaultStats>('/vault/stats', { timeout: TIMEOUT.short }).then((r) => r.data),

  list: (params?: {
    stage?: string;
    source?: string;
    case_id?: number;
    q?: string;
    skip?: number;
    limit?: number;
  }) =>
    apiClient.get<UserMaterial[]>('/vault', { params, timeout: TIMEOUT.medium }).then((r) => r.data),

  upload: (file: File, opts?: { stage?: string; case_id?: number; note?: string }) => {
    const form = new FormData();
    form.append('file', file);
    const params: Record<string, string | number> = {};
    if (opts?.stage) params.stage = opts.stage;
    if (opts?.case_id != null) params.case_id = opts.case_id;
    if (opts?.note) params.note = opts.note;
    return apiClient
      .post<UserMaterial>('/vault/upload', form, {
        params,
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: TIMEOUT.long,
      })
      .then((r) => r.data);
  },

  update: (id: number, data: Partial<Pick<UserMaterial, 'title' | 'stage' | 'case_id' | 'tags' | 'note'>>) =>
    apiClient.patch<UserMaterial>(`/vault/${id}`, data, { timeout: TIMEOUT.short }).then((r) => r.data),

  remove: (id: number) => apiClient.delete(`/vault/${id}`, { timeout: TIMEOUT.short }),

  bulkRemove: (ids: number[]) =>
    apiClient
      .post<{ deleted: number }>('/vault/bulk-delete', { ids }, { timeout: TIMEOUT.medium })
      .then((r) => r.data),

  download: (id: number) =>
    apiClient
      .get<Blob>(`/vault/${id}/download`, { responseType: 'blob', timeout: TIMEOUT.long })
      .then((r) => r.data),
};
