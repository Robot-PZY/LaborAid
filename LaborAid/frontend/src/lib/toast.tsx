import { useState, useCallback, useContext, createContext, useEffect, useRef, type ReactNode } from 'react';
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

// ── Types ──────────────────────────────────────────────────────────────

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
  /** When true, toast is being dismissed (for exit animation) */
  exiting?: boolean;
}

type ToastInput = Omit<Toast, 'id' | 'exiting'> | string;

function normalizeToast(input: ToastInput, fallbackType: ToastType = 'info'): Omit<Toast, 'id' | 'exiting'> {
  if (typeof input === 'string') {
    return { title: input, type: fallbackType };
  }
  return input;
}

interface ToastContextValue {
  /** `toast('提示')` 或 `toast({ type, title, description })`；第二参数可传 type */
  toast: (opts: ToastInput, type?: ToastType) => void;
  dismiss: (id: string) => void;
}

// ── Context ────────────────────────────────────────────────────────────

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within <ToastProvider>');
  return ctx;
}

// ── Icons & styles per type ────────────────────────────────────────────

const TOAST_STYLES: Record<ToastType, { icon: typeof CheckCircle2; border: string; bg: string; iconColor: string; progressColor: string }> = {
  success: {
    icon: CheckCircle2,
    border: 'border-green-200 dark:border-green-800',
    bg: 'bg-green-50 dark:bg-green-950/50',
    iconColor: 'text-green-600 dark:text-green-400',
    progressColor: 'bg-green-500',
  },
  error: {
    icon: AlertCircle,
    border: 'border-red-200 dark:border-red-800',
    bg: 'bg-red-50 dark:bg-red-950/50',
    iconColor: 'text-red-600 dark:text-red-400',
    progressColor: 'bg-red-500',
  },
  warning: {
    icon: AlertTriangle,
    border: 'border-amber-200 dark:border-amber-800',
    bg: 'bg-amber-50 dark:bg-amber-950/50',
    iconColor: 'text-amber-600 dark:text-amber-400',
    progressColor: 'bg-amber-500',
  },
  info: {
    icon: Info,
    border: 'border-blue-200 dark:border-blue-800',
    bg: 'bg-blue-50 dark:bg-blue-950/50',
    iconColor: 'text-blue-600 dark:text-blue-400',
    progressColor: 'bg-blue-500',
  },
};

// ── Single toast component (with progress bar + animation) ─────────────

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const style = TOAST_STYLES[toast.type];
  const Icon = style.icon;
  const duration = toast.duration ?? (toast.type === 'error' ? 6000 : 4000);

  return (
    <div
      role="alert"
      className={cn(
        'relative flex items-start gap-3 rounded-lg border shadow-lg overflow-hidden',
        'animate-in slide-in-from-right-full duration-300',
        toast.exiting && 'animate-out slide-out-to-right-full fade-out duration-200',
        style.border,
        style.bg,
      )}
    >
      {/* Progress bar */}
      {duration > 0 && (
        <div
          className="absolute bottom-0 left-0 h-0.5 animate-toast-progress"
          style={{
            backgroundColor: 'currentColor',
            color: 'var(--tw-prog-color, #3b82f6)',
            animationDuration: `${duration}ms`,
          }}
        >
          <div className={cn('h-full', style.progressColor)} style={{ width: '100%', animation: `toast-progress ${duration}ms linear forwards` }} />
        </div>
      )}

      <div className="flex items-start gap-3 px-4 py-3 w-full">
        <Icon className={cn('h-5 w-5 mt-0.5 shrink-0', style.iconColor)} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground">{toast.title}</p>
          {toast.description && (
            <p className="text-xs text-muted-foreground mt-0.5">{toast.description}</p>
          )}
        </div>
        <button
          onClick={() => onDismiss(toast.id)}
          className="shrink-0 rounded p-0.5 transition-colors hover:bg-black/10 dark:hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="关闭通知"
        >
          <X className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
      </div>
    </div>
  );
}

// ── Provider ───────────────────────────────────────────────────────────

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = useCallback((id: string) => {
    // Clear any pending auto-dismiss timer
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }

    // Mark as exiting for animation
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)));

    // Remove after exit animation completes
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 200);
  }, []);

  const addToast = useCallback((opts: ToastInput, type?: ToastType) => {
    const normalized = normalizeToast(opts, type);
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const duration = normalized.duration ?? (normalized.type === 'error' ? 6000 : 4000);

    setToasts((prev) => [...prev, { ...normalized, id }]);

    if (duration > 0) {
      const timer = setTimeout(() => dismiss(id), duration);
      timersRef.current.set(id, timer);
    }
  }, [dismiss]);

  // Cleanup timers on unmount
  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach((timer) => clearTimeout(timer));
      timers.clear();
    };
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast, dismiss }}>
      {children}
      {/* Toast container - stacked with proper spacing */}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="fixed bottom-4 right-4 z-[100] flex flex-col-reverse gap-2 max-w-sm pointer-events-none"
      >
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto">
            <ToastItem toast={t} onDismiss={dismiss} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export default ToastProvider;
