import axios, { type AxiosRequestConfig, type AxiosResponse, type CancelTokenSource } from 'axios';

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 180000,
  headers: {
    'Content-Type': 'application/json; charset=utf-8',
  },
});

// ── Timeout presets ────────────────────────────────────────────────────
export const TIMEOUT = {
  short: 15_000,    // GET endpoints (fast reads)
  medium: 60_000,  // Standard mutations
  long: 120_000,   // File uploads / exports
  ai: 300_000,     // AI generation / review tasks
} as const;

// ── Request interceptor: attach JWT token ──────────────────────────────
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (!token) return config;

    const headers = config.headers;
    const existing =
      typeof headers?.get === 'function'
        ? headers.get('Authorization')
        : (headers as Record<string, string | undefined>)?.Authorization;

    // Keep an explicit Authorization header (e.g. fresh token right after login).
    if (!existing) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

let isRedirecting = false;

export function resetAuthRedirectLock() {
  isRedirecting = false;
}

// ── Response interceptor: handle 401 + retry on network error ─────────
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 — redirect to login, preserve return path
    if (error.response?.status === 401 && !isRedirecting) {
      isRedirecting = true;
      const returnTo = `${window.location.pathname}${window.location.search}`;
      if (returnTo && returnTo !== '/login') {
        sessionStorage.setItem('auth_return_to', returnTo);
      }
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
      return Promise.reject(error);
    }

    // Retry once on network errors (no response) if not already retried
    if (!error.response && !originalRequest._retried) {
      originalRequest._retried = true;
      try {
        return await apiClient(originalRequest);
      } catch {
        // second attempt failed, fall through to reject
      }
    }

    return Promise.reject(error);
  },
);

// ── Cancellation helpers ───────────────────────────────────────────────
const cancelTokenSources = new Map<string, CancelTokenSource>();

export function createCancelToken(key: string): CancelTokenSource {
  // Cancel any previous request with the same key
  const existing = cancelTokenSources.get(key);
  if (existing) {
    existing.cancel(`Cancelled by newer request: ${key}`);
  }
  const source = axios.CancelToken.source();
  cancelTokenSources.set(key, source);
  return source;
}

export function cancelRequest(key: string) {
  const source = cancelTokenSources.get(key);
  if (source) {
    source.cancel(`Manually cancelled: ${key}`);
    cancelTokenSources.delete(key);
  }
}

// ── Request deduplication ──────────────────────────────────────────────
const pendingRequests = new Map<string, Promise<unknown>>();

/**
 * Deduplicate concurrent GET requests with the same URL+params.
 * If an identical request is already in-flight, returns the same Promise.
 * Otherwise, makes the request and caches it until completion.
 */
export function dedupedGet<T>(url: string, params?: Record<string, unknown>, config?: AxiosRequestConfig): Promise<T> {
  const cacheKey = `GET:${url}:${JSON.stringify(params || {})}`;
  const existing = pendingRequests.get(cacheKey);
  if (existing) return existing as Promise<T>;

  const promise = apiClient.get(url, { params, ...config })
    .then(res => res.data as T)
    .finally(() => { pendingRequests.delete(cacheKey); });

  pendingRequests.set(cacheKey, promise);
  return promise;
}

// ── Response type validation ───────────────────────────────────────────
export function validateResponse<T>(
  data: unknown,
  requiredKeys: (keyof T)[],
): data is T {
  if (typeof data !== 'object' || data === null) return false;
  return requiredKeys.every((key) => key in data);
}

export function ensureTypedResponse<T>(
  res: AxiosResponse,
  requiredKeys: (keyof T)[],
): T {
  if (!validateResponse<T>(res.data, requiredKeys)) {
    throw new Error('Unexpected response shape from server');
  }
  return res.data;
}

// ── Blob download helper ───────────────────────────────────────────────
export async function downloadBlob(
  fetchBlob: () => Promise<Blob>,
  filename: string,
): Promise<void> {
  const blob = await fetchBlob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export default apiClient;

