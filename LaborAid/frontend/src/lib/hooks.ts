/**
 * Custom React hooks for LaborAid frontend.
 *
 * Provides reusable stateful logic: debounce, localStorage, async ops,
 * pagination, confirmation dialogs, form validation, and API integration.
 */

import { useState, useEffect, useCallback, useRef, type Dispatch, type SetStateAction } from 'react';
import { useToast } from '@/lib/toast';
import { getErrorMessage } from '@/lib/errors';

// ── useDebounce ──────────────────────────────────────────────────────────

/**
 * Debounce a value by a given delay.
 *
 * Returns the latest `value` only after `delay` ms have elapsed
 * since the last change. Useful for search inputs and resize handlers.
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

// ── useLocalStorage ──────────────────────────────────────────────────────

/**
 * Typed localStorage hook with JSON serialization.
 *
 * Reads the stored value on mount. Writes on every state update.
 * Falls back to `initialValue` when the key is missing or parsing fails.
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, Dispatch<SetStateAction<T>>] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = localStorage.getItem(key);
      return item !== null ? (JSON.parse(item) as T) : initialValue;
    } catch {
      return initialValue;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(storedValue));
    } catch {
      // quota exceeded — silently ignore
    }
  }, [key, storedValue]);

  return [storedValue, setStoredValue];
}

// ── useAsync ─────────────────────────────────────────────────────────────

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface UseAsyncReturn<T> extends AsyncState<T> {
  /** Execute an async function, updating loading/data/error accordingly. */
  execute: (fn: () => Promise<T>) => Promise<T | null>;
  /** Reset state back to initial idle values. */
  reset: () => void;
}

/**
 * Async operation state management.
 *
 * Tracks `loading`, `error`, and `data` for any async function.
 * Call `execute(fn)` to run an async operation and have state updated
 * automatically. Call `reset()` to clear back to initial state.
 */
export function useAsync<T>(): UseAsyncReturn<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(async (fn: () => Promise<T>): Promise<T | null> => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const result = await fn();
      setState({ data: result, loading: false, error: null });
      return result;
    } catch (err: unknown) {
      const message = getErrorMessage(err);
      setState((prev) => ({ ...prev, loading: false, error: message }));
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset };
}

// ── usePagination ────────────────────────────────────────────────────────

interface UsePaginationOptions {
  /** Initial page number (default 1) */
  initialPage?: number;
  /** Items per page (default 10) */
  pageSize?: number;
  /** Total number of items */
  total: number;
}

interface UsePaginationReturn {
  page: number;
  pageSize: number;
  totalPages: number;
  setPage: (page: number) => void;
  nextPage: () => void;
  prevPage: () => void;
  /** Convenience: whether current page is the first. */
  isFirstPage: boolean;
  /** Convenience: whether current page is the last. */
  isLastPage: boolean;
}

/**
 * Pagination state management.
 *
 * Provides the current page, total pages, and navigation helpers.
 * Automatically clamps the page when `total` or `pageSize` changes.
 */
export function usePagination(options: UsePaginationOptions): UsePaginationReturn {
  const { initialPage = 1, pageSize = 10, total } = options;
  const [page, setPageInternal] = useState(initialPage);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  // Clamp page when totalPages shrinks
  useEffect(() => {
    setPageInternal((p) => Math.min(p, totalPages));
  }, [totalPages]);

  const setPage = useCallback(
    (p: number) => setPageInternal(Math.max(1, Math.min(p, totalPages))),
    [totalPages],
  );

  const nextPage = useCallback(() => {
    setPageInternal((p) => Math.min(p + 1, totalPages));
  }, [totalPages]);

  const prevPage = useCallback(() => {
    setPageInternal((p) => Math.max(p - 1, 1));
  }, []);

  return {
    page,
    pageSize,
    totalPages,
    setPage,
    nextPage,
    prevPage,
    isFirstPage: page <= 1,
    isLastPage: page >= totalPages,
  };
}

// ── useConfirm ───────────────────────────────────────────────────────────

interface ConfirmState {
  isOpen: boolean;
  title: string;
  message: string;
}

interface UseConfirmReturn extends ConfirmState {
  /** Trigger the confirmation dialog with a title and message. */
  requestConfirm: (title: string, message: string) => Promise<boolean>;
  /** User clicked confirm — resolves the promise with `true`. */
  confirm: () => void;
  /** User clicked cancel — resolves the promise with `false`. */
  cancel: () => void;
}

/**
 * Confirmation dialog state management.
 *
 * Call `requestConfirm(title, message)` which returns a Promise<boolean>.
 * The promise resolves to `true` when `confirm()` is called, or `false`
 * when `cancel()` is called. Wire `confirm`/`cancel` to dialog buttons.
 */
export function useConfirm(): UseConfirmReturn {
  const [state, setState] = useState<ConfirmState>({
    isOpen: false,
    title: '',
    message: '',
  });

  // Store the resolve callback in a ref so it survives re-renders
  const resolverRef = useRef<((value: boolean) => void) | null>(null);

  const requestConfirm = useCallback((title: string, message: string): Promise<boolean> => {
    return new Promise<boolean>((resolve) => {
      resolverRef.current = resolve;
      setState({ isOpen: true, title, message });
    });
  }, []);

  const confirm = useCallback(() => {
    resolverRef.current?.(true);
    resolverRef.current = null;
    setState((prev) => ({ ...prev, isOpen: false }));
  }, []);

  const cancel = useCallback(() => {
    resolverRef.current?.(false);
    resolverRef.current = null;
    setState((prev) => ({ ...prev, isOpen: false }));
  }, []);

  return { ...state, requestConfirm, confirm, cancel };
}

// ── useFormValidation ────────────────────────────────────────────────────

type ValidationRule<T> = {
  /** Return an error message string if invalid, or `undefined` / empty string if valid. */
  validate: (value: T, formValues: Record<string, T>) => string | undefined;
};

type FieldRules<T extends Record<string, unknown>> = {
  [K in keyof T]?: ValidationRule<T[K]> | ValidationRule<T[K]>[];
};

interface UseFormValidationReturn<T extends Record<string, unknown>> {
  /** Current field-level error messages (keyed by field name). */
  errors: Partial<Record<keyof T, string>>;
  /** Validate the entire form. Returns `true` if no errors. */
  validateForm: (values: T) => boolean;
  /** Validate a single field immediately. */
  validateField: (field: keyof T, value: T[keyof T], values: T) => string | undefined;
  /** Clear errors for one field, or all fields if no argument. */
  clearErrors: (field?: keyof T) => void;
  /** Whether the form currently has any errors. */
  hasErrors: boolean;
}

/**
 * Simple form validation hook.
 *
 * Pass a map of field names to validation rules (single rule or array).
 * Use `validateForm(values)` before submit and `validateField` for
 * inline / blur validation.
 */
export function useFormValidation<T extends Record<string, unknown>>(
  rules: FieldRules<T>,
): UseFormValidationReturn<T> {
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});

  const validateField = useCallback(
    (field: keyof T, value: T[keyof T], values: T): string | undefined => {
      const fieldRules = rules[field];
      if (!fieldRules) return undefined;

      const ruleArray = Array.isArray(fieldRules) ? fieldRules : [fieldRules];
      for (const rule of ruleArray) {
        const msg = rule.validate(value, values);
        if (msg) return msg;
      }
      return undefined;
    },
    [rules],
  );

  const validateForm = useCallback(
    (values: T): boolean => {
      const newErrors: Partial<Record<keyof T, string>> = {};
      for (const field of Object.keys(rules) as (keyof T)[]) {
        const msg = validateField(field, values[field], values);
        if (msg) newErrors[field] = msg;
      }
      setErrors(newErrors);
      return Object.keys(newErrors).length === 0;
    },
    [rules, validateField],
  );

  const clearErrors = useCallback((field?: keyof T) => {
    if (field) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    } else {
      setErrors({});
    }
  }, []);

  const hasErrors = Object.keys(errors).length > 0;

  return { errors, validateForm, validateField, clearErrors, hasErrors };
}

// ── useApi ───────────────────────────────────────────────────────────────

interface UseApiOptions {
  /** Show a success toast with this title when the call resolves. */
  successToast?: string;
  /** Show an error toast on rejection (default true). */
  errorToast?: boolean;
}

interface UseApiReturn<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  /** Execute the API call. Resolves with data or null on error. */
  call: (fn: () => Promise<T>, options?: UseApiOptions) => Promise<T | null>;
  /** Reset to idle state. */
  reset: () => void;
}

/**
 * Wrapper for API calls with loading/error state and toast integration.
 *
 * Automatically shows error toasts via `useToast()` and optionally
 * shows success toasts. Uses the project's centralized `getErrorMessage`
 * to produce user-friendly Chinese error strings.
 *
 * @example
 * ```tsx
 * const { call, loading, data } = useApi<Case>();
 *
 * const handleSave = () => {
 *   call(() => caseApi.create(formData), { successToast: '案件创建成功' });
 * };
 * ```
 */
export function useApi<T>(): UseApiReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const call = useCallback(
    async (fn: () => Promise<T>, options?: UseApiOptions): Promise<T | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await fn();
        setData(result);
        setLoading(false);

        if (options?.successToast) {
          toast.toast({ type: 'success', title: options.successToast });
        }
        return result;
      } catch (err: unknown) {
        const message = getErrorMessage(err);
        setError(message);
        setLoading(false);

        if (options?.errorToast !== false) {
          toast.toast({ type: 'error', title: message });
        }
        return null;
      }
    },
    [toast],
  );

  const reset = useCallback(() => {
    setData(null);
    setLoading(false);
    setError(null);
  }, []);

  return { data, loading, error, call, reset };
}
