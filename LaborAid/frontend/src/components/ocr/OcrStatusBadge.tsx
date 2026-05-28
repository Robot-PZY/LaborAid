import { Loader2, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { userFacingOcrMessage } from '@/lib/ocr-display';

export type OcrStatus = 'pending' | 'processing' | 'success' | 'failed';

const STYLES: Record<
  OcrStatus,
  { label: string; className: string; icon: typeof Clock }
> = {
  pending: {
    label: '待识别',
    className: 'border-border bg-muted/50 text-muted-foreground',
    icon: Clock,
  },
  processing: {
    label: '识别中',
    className: 'border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-200',
    icon: Loader2,
  },
  success: {
    label: '识别成功',
    className: 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200',
    icon: CheckCircle2,
  },
  failed: {
    label: '识别失败',
    className: 'border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200',
    icon: AlertCircle,
  },
};

export default function OcrStatusBadge({
  status,
  message,
  className,
  compact,
}: {
  status?: OcrStatus | string | null;
  message?: string | null;
  className?: string;
  compact?: boolean;
}) {
  const key = (status && status in STYLES ? status : 'pending') as OcrStatus;
  const cfg = STYLES[key];
  const Icon = cfg.icon;
  const spin = key === 'processing';
  const displayMessage = userFacingOcrMessage(key, message);

  return (
    <div
      className={cn(
        'inline-flex max-w-full flex-col gap-0.5 rounded-md border px-2.5 py-1.5 text-xs',
        cfg.className,
        className,
      )}
      role="status"
    >
      <span className="inline-flex items-center gap-1.5 font-medium">
        <Icon className={cn('h-3.5 w-3.5 shrink-0', spin && 'animate-spin')} />
        {cfg.label}
      </span>
      {displayMessage && !compact && (
        <span className="text-[11px] leading-snug opacity-90 break-words">{displayMessage}</span>
      )}
    </div>
  );
}
