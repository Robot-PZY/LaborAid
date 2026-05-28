import { AlertCircle, Info } from 'lucide-react';

interface CredibilityBarProps {
  score: number;
  needsHumanReview?: boolean;
  reason?: string;
  className?: string;
}

export default function CredibilityBar({
  score,
  needsHumanReview = true,
  reason,
  className = '',
}: CredibilityBarProps) {
  const pct = Math.round(Math.min(1, Math.max(0, score)) * 100);
  const tone =
    pct >= 75 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-rose-500';

  return (
    <div className={`rounded-[var(--radius-md)] border border-border/70 bg-muted/30 px-3 py-2.5 text-xs ${className}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-foreground">材料完整度参考</span>
        <span className="tabular-nums text-muted-foreground">{pct}%</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
        <div className={`h-full rounded-full transition-all ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      {(reason || needsHumanReview) && (
        <div className="mt-2 flex items-start gap-1.5 text-muted-foreground">
          {needsHumanReview ? (
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
          ) : (
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          )}
          <span>{reason || '以上内容仅供参考，不构成法律意见，请以官方渠道为准'}</span>
        </div>
      )}
    </div>
  );
}
