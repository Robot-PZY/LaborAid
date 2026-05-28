/**
 * Centralized error handling utilities.
 *
 * Maps backend HTTP error codes to user-friendly Chinese messages,
 * handles network errors, timeouts, and rate-limit retries.
 */

import { AxiosError } from 'axios';

// ── Error code to Chinese message mapping ────────────────────────────────

const ERROR_MESSAGES: Record<number, string> = {
  400: '请求参数错误，请检查输入内容',
  401: '登录已过期，请重新登录',
  403: '您没有权限执行此操作',
  404: '请求的资源不存在',
  409: '数据冲突，请刷新后重试',
  422: '提交的数据格式不正确',
  429: '请求过于频繁，请稍后再试',
  500: '服务器内部错误，请稍后重试',
  502: '服务器正在维护，请稍后重试',
  503: '服务暂不可用，请稍后重试',
};

// ── Public helpers ───────────────────────────────────────────────────────

/**
 * Extract a human-readable error message from any thrown value.
 *
 * Priority:
 *  1. Axios response: use backend `detail` if present, else map status code
 *  2. Network error: offline message
 *  3. Timeout: timeout message
 *  4. Fallback: generic error
 */
export function getErrorMessage(err: unknown): string {
  if (err instanceof AxiosError) {
    // Rate limit with Retry-After
    if (err.response?.status === 429) {
      const retryAfter = err.response.headers?.['retry-after'];
      if (retryAfter) {
        const seconds = Number(retryAfter);
        if (seconds > 0 && seconds < 3600) {
          return `请求过于频繁，请 ${Math.ceil(seconds)} 秒后再试`;
        }
      }
      return err.response?.data?.detail || ERROR_MESSAGES[429];
    }

    // Backend returned a structured error
    if (err.response?.data?.detail) {
      return err.response.data.detail;
    }

    // Map status code
    if (err.response?.status) {
      return ERROR_MESSAGES[err.response.status] || `请求失败 (${err.response.status})`;
    }

    // Timeout
    if (err.code === 'ECONNABORTED' || err.code === 'ERR_CANCELED') {
      return '请求超时，请检查网络后重试';
    }

    // Network error (no response at all)
    if (!err.response && err.message === 'Network Error') {
      return '网络连接失败，请检查您的网络设置';
    }
  }

  if (err instanceof Error) {
    return err.message;
  }

  return '未知错误，请稍后重试';
}

/**
 * Get the HTTP status code from an error, or 0 if not an HTTP error.
 */
export function getErrorStatus(err: unknown): number {
  if (err instanceof AxiosError && err.response?.status) {
    return err.response.status;
  }
  return 0;
}

/**
 * Check if an error is a network connectivity error.
 */
export function isNetworkError(err: unknown): boolean {
  if (err instanceof AxiosError) {
    return !err.response && err.message === 'Network Error';
  }
  return false;
}

/**
 * Check if an error is a timeout error.
 */
export function isTimeoutError(err: unknown): boolean {
  if (err instanceof AxiosError) {
    return err.code === 'ECONNABORTED';
  }
  return false;
}

/**
 * Check if an error is a rate-limit error (429).
 */
export function isRateLimitError(err: unknown): boolean {
  return getErrorStatus(err) === 429;
}

/**
 * Get the Retry-After seconds from a 429 response, or 0.
 */
export function getRetryAfterSeconds(err: unknown): number {
  if (err instanceof AxiosError && err.response?.status === 429) {
    const val = err.response.headers?.['retry-after'];
    const n = Number(val);
    return Number.isFinite(n) && n > 0 ? Math.ceil(n) : 0;
  }
  return 0;
}
