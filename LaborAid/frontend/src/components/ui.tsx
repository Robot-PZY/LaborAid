/**
 * LaborAid shared UI components
 *
 * Exports reusable components: LoadingSpinner, PageLoader, EmptyState,
 * ErrorBanner, ConfirmDialog, Badge, StatCard, Pagination, SearchInput, Modal
 */
import {
  useState,
  useEffect,
  useRef,
  useCallback,
  type ReactNode,
  type ElementType,
} from 'react';
import {
  Loader2,
  AlertCircle,
  CheckCircle,
  X,
  Search,
  ChevronLeft,
  ChevronRight,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// LoadingSpinner
// ---------------------------------------------------------------------------

const spinnerSizes = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-10 w-10',
} as const;

interface LoadingSpinnerProps {
  /** Visual size of the spinner */
  size?: keyof typeof spinnerSizes;
  /** Optional text displayed next to the spinner */
  text?: string;
  /** Additional class names */
  className?: string;
}

export function LoadingSpinner({ size = 'md', text, className }: LoadingSpinnerProps) {
  return (
    <div className={cn('flex items-center justify-center gap-2', className)} role="status" aria-label={text || '加载中'}>
      <Loader2 className={cn('animate-spin text-primary', spinnerSizes[size])} />
      {text && <span className="text-sm text-muted-foreground">{text}</span>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PageLoader
// ---------------------------------------------------------------------------

interface PageLoaderProps {
  /** Optional loading message */
  text?: string;
  className?: string;
}

export function PageLoader({ text = '加载中...', className }: PageLoaderProps) {
  return (
    <div className={cn('flex h-full min-h-[40vh] flex-col items-center justify-center gap-3', className)}>
      <Loader2 className="h-10 w-10 animate-spin text-primary" />
      {text && <p className="text-sm text-muted-foreground">{text}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// EmptyState
// ---------------------------------------------------------------------------

interface EmptyStateProps {
  /** Icon component rendered in the hero area */
  icon?: ElementType;
  /** Primary heading */
  title: string;
  /** Secondary description text */
  description?: string;
  /** Optional action button label */
  actionLabel?: string;
  /** Click handler for the action button */
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border bg-card py-16 px-6',
        className,
      )}
    >
      {Icon && (
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
          <Icon className="h-8 w-8 text-primary/60" />
        </div>
      )}
      <h3 className="mb-2 text-lg font-semibold text-muted-foreground">{title}</h3>
      {description && (
        <p className="max-w-md text-center text-sm text-muted-foreground">{description}</p>
      )}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-6 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ErrorBanner
// ---------------------------------------------------------------------------

interface ErrorBannerProps {
  /** Error message to display */
  message: string;
  /** Dismiss callback -- if provided, a close button is shown */
  onDismiss?: () => void;
  className?: string;
}

export function ErrorBanner({ message, onDismiss, className }: ErrorBannerProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700',
        className,
      )}
      role="alert"
      aria-live="polite"
    >
      <AlertCircle className="h-4 w-4 shrink-0" />
      <p className="flex-1">{message}</p>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="ml-auto shrink-0 rounded p-0.5 transition-colors hover:bg-red-100 hover:text-red-900"
          aria-label="关闭错误提示"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ConfirmDialog
// ---------------------------------------------------------------------------

interface ConfirmDialogProps {
  /** Whether the dialog is visible */
  open: boolean;
  /** Dialog title */
  title: string;
  /** Body message or JSX */
  message: string | ReactNode;
  /** Label for the confirm button (default: "确认") */
  confirmLabel?: string;
  /** Label for the cancel button (default: "取消") */
  cancelLabel?: string;
  /** Variant styling for the confirm button */
  variant?: 'danger' | 'primary';
  /** Whether the confirm action is in progress */
  loading?: boolean;
  /** Fires when user clicks confirm */
  onConfirm: () => void;
  /** Fires when user clicks cancel or backdrop */
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = '确认',
  cancelLabel = '取消',
  variant = 'primary',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onCancel]);

  // Trap focus
  useEffect(() => {
    if (!open) return;
    dialogRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onCancel}>
      <div
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-desc"
        tabIndex={-1}
        className="w-full max-w-md rounded-xl border bg-card p-6 shadow-xl outline-none"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-3">
          <div
            className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-full',
              variant === 'danger' ? 'bg-red-100' : 'bg-primary/10',
            )}
          >
            {variant === 'danger' ? (
              <AlertCircle className="h-5 w-5 text-red-600" />
            ) : (
              <CheckCircle className="h-5 w-5 text-primary" />
            )}
          </div>
          <div className="flex-1">
            <h2 id="confirm-dialog-title" className="text-lg font-semibold">
              {title}
            </h2>
            <div id="confirm-dialog-desc" className="mt-2 text-sm text-muted-foreground">
              {message}
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={cn(
              'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors disabled:opacity-50',
              variant === 'danger'
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-primary hover:bg-primary/90',
            )}
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? '处理中...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Badge
// ---------------------------------------------------------------------------

const badgeVariants = {
  success: 'bg-green-100 text-green-700',
  warning: 'bg-yellow-100 text-yellow-700',
  error: 'bg-red-100 text-red-700',
  info: 'bg-blue-100 text-blue-700',
  neutral: 'bg-gray-100 text-gray-700',
} as const;

type BadgeVariant = keyof typeof badgeVariants;

interface BadgeProps {
  /** Visual variant */
  variant?: BadgeVariant;
  /** Badge content */
  children: ReactNode;
  className?: string;
}

export function Badge({ variant = 'neutral', children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        badgeVariants[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

// ---------------------------------------------------------------------------
// StatCard
// ---------------------------------------------------------------------------

interface StatCardProps {
  /** Card label (displayed below the value) */
  title: string;
  /** Primary numeric or text value */
  value: number | string;
  /** Optional icon component */
  icon?: ElementType;
  /** Tailwind background colour class for the icon container */
  iconColor?: string;
  /** Optional trend direction */
  trend?: 'up' | 'down' | 'neutral';
  /** Label rendered inside the trend badge */
  trendLabel?: string;
  /** Click handler -- makes the card interactive */
  onClick?: () => void;
  /** Shows a skeleton loader when true */
  loading?: boolean;
  className?: string;
}

export function StatCard({
  title,
  value,
  icon: Icon,
  iconColor = 'bg-blue-500',
  trend,
  trendLabel,
  onClick,
  loading,
  className,
}: StatCardProps) {
  if (loading) {
    return (
      <div className={cn('flex items-center gap-4 rounded-xl border bg-card p-5 shadow-sm', className)}>
        {Icon && (
          <div className={cn('flex h-12 w-12 items-center justify-center rounded-lg', iconColor)}>
            <Icon className="h-6 w-6 text-white" />
          </div>
        )}
        <div>
          <div className="h-7 w-12 animate-pulse rounded bg-muted" />
          <div className="mt-1 h-4 w-16 animate-pulse rounded bg-muted" />
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className={cn(
        'flex items-center gap-4 rounded-xl border bg-card p-5 shadow-sm transition-colors',
        onClick ? 'cursor-pointer hover:border-primary/50 hover:shadow-md' : '',
        className,
      )}
    >
      {Icon && (
        <div className={cn('flex h-12 w-12 shrink-0 items-center justify-center rounded-lg', iconColor)}>
          <Icon className="h-6 w-6 text-white" />
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-sm text-muted-foreground">{title}</p>
      </div>
      {trend && trend !== 'neutral' && trendLabel && (
        <div
          className={cn(
            'flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
            trend === 'up' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700',
          )}
        >
          {trend === 'up' ? (
            <ChevronRight className="h-3 w-3 rotate-[-90deg]" />
          ) : (
            <ChevronRight className="h-3 w-3 rotate-90" />
          )}
          {trendLabel}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

interface PaginationProps {
  /** Current active page (1-indexed) */
  currentPage: number;
  /** Total number of pages */
  totalPages: number;
  /** Callback when page changes */
  onPageChange: (page: number) => void;
  /** Optional total item count string displayed alongside */
  totalCount?: number | string;
  className?: string;
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  totalCount,
  className,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  // Determine which page numbers to show, with ellipsis
  const pages: (number | 'ellipsis')[] = [];
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || Math.abs(i - currentPage) <= 1) {
      pages.push(i);
    } else if (pages[pages.length - 1] !== 'ellipsis') {
      pages.push('ellipsis');
    }
  }

  return (
    <div className={cn('flex items-center justify-between pt-2', className)}>
      {totalCount !== undefined ? (
        <p className="text-xs text-muted-foreground">
          第 {currentPage} / {totalPages} 页，共 {totalCount} 条
        </p>
      ) : (
        <p className="text-xs text-muted-foreground">
          第 {currentPage} / {totalPages} 页
        </p>
      )}
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className="rounded-md border p-2 transition-colors hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="上一页"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        {pages.map((page, idx) =>
          page === 'ellipsis' ? (
            <span key={`ellipsis-${idx}`} className="px-1 text-xs text-muted-foreground">
              ...
            </span>
          ) : (
            <button
              key={page}
              onClick={() => onPageChange(page)}
              className={cn(
                'min-w-[32px] rounded-md border px-2 py-1 text-xs font-medium transition-colors',
                page === currentPage
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'hover:bg-accent',
              )}
            >
              {page}
            </button>
          ),
        )}

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className="rounded-md border p-2 transition-colors hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="下一页"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SearchInput
// ---------------------------------------------------------------------------

interface SearchInputProps {
  /** Current search value */
  value: string;
  /** Fires when the value changes (after debounce) */
  onChange: (value: string) => void;
  /** Fires on immediate keystrokes (before debounce) */
  onValueChange?: (value: string) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Debounce delay in milliseconds (default 300) */
  debounceMs?: number;
  /** Additional class names for the wrapper */
  className?: string;
  /** Accessible label */
  ariaLabel?: string;
}

export function SearchInput({
  value: controlledValue,
  onChange,
  onValueChange,
  placeholder = '搜索...',
  debounceMs = 300,
  className,
  ariaLabel = '搜索',
}: SearchInputProps) {
  const [internalValue, setInternalValue] = useState(controlledValue);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync external value changes
  useEffect(() => {
    setInternalValue(controlledValue);
  }, [controlledValue]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const next = e.target.value;
      setInternalValue(next);
      onValueChange?.(next);

      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => onChange(next), debounceMs);
    },
    [onChange, onValueChange, debounceMs],
  );

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleClear = () => {
    setInternalValue('');
    onChange('');
    onValueChange?.('');
  };

  return (
    <div className={cn('relative', className)}>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <input
        type="text"
        value={internalValue}
        onChange={handleChange}
        placeholder={placeholder}
        aria-label={ariaLabel}
        className="w-full rounded-lg border border-input bg-background py-2.5 pl-10 pr-10 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
      />
      {internalValue && (
        <button
          onClick={handleClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
          aria-label="清除搜索"
        >
          <XCircle className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

interface ModalProps {
  /** Whether the modal is open */
  open: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** Modal title */
  title: string;
  /** Modal body content */
  children: ReactNode;
  /** Optional footer actions; if not provided, a default close button is shown */
  footer?: ReactNode;
  /** Max width class (default: "max-w-lg") */
  maxWidth?: string;
  className?: string;
}

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  maxWidth = 'max-w-lg',
  className,
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  // Focus management
  useEffect(() => {
    if (open) {
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
      modalRef.current?.focus();
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      aria-modal="true"
      role="dialog"
      aria-labelledby="modal-title"
    >
      <div
        ref={modalRef}
        tabIndex={-1}
        className={cn(
          'w-full rounded-xl border bg-card shadow-xl outline-none',
          maxWidth,
          className,
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 id="modal-title" className="text-lg font-semibold">
            {title}
          </h2>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            aria-label="关闭"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5">{children}</div>

        {/* Footer */}
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          {footer ?? (
            <button
              onClick={onClose}
              className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
            >
              关闭
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
