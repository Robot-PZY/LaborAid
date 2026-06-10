import { Loader2, Sparkles, CheckCircle2, CircleAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { CaseReadinessSummary } from '@/lib/api';
import { cn } from '@/lib/utils';

interface CaseReadinessHintProps {
  readiness: CaseReadinessSummary | null;
  loading?: boolean;
  variant?: 'compact' | 'evidence' | 'docgen';
  className?: string;
}

const levelBarClass: Record<string, string> = {
  high: 'bg-emerald-500',
  medium: 'bg-amber-500',
  low: 'bg-rose-500',
};

export default function CaseReadinessHint({
  readiness,
  loading = false,
  variant = 'compact',
  className,
}: CaseReadinessHintProps) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className={cn('rounded-xl border bg-muted/20 p-4 text-sm text-muted-foreground', className)}>
        <Loader2 className="mr-2 inline h-4 w-4 animate-spin" />
        正在分析案件材料完整度…
      </div>
    );
  }

  if (!readiness) return null;

  const displayScore = readiness.combined_score ?? readiness.readiness_score;
  const barClass = levelBarClass[readiness.readiness_level] || 'bg-muted-foreground';
  const requiredSuggestions = readiness.evidence_suggestions?.filter((s) => s.priority === 'required') ?? [];
  const missingEvidence = requiredSuggestions.filter((s) => s.status === 'missing');

  return (
    <div
      className={cn(
        'rounded-xl border border-accent/25 bg-gradient-to-br from-accent/8 via-card to-card p-4 shadow-sm',
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="flex items-center gap-2 text-sm font-semibold">
          <Sparkles className="h-4 w-4 text-primary" />
          AI 材料评估
          {readiness.cause_label && (
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
              {readiness.cause_label}
            </span>
          )}
        </h3>
        <span className="text-xs font-medium tabular-nums">
          完整度 {displayScore}%
          {readiness.chain_completeness_score != null && (
            <span className="ml-1 font-normal text-muted-foreground">
              （材料 {readiness.readiness_score}% + 证据链 {readiness.chain_completeness_score}%）
            </span>
          )}
        </span>
      </div>

      <div className="mt-3 h-2 rounded-full bg-muted">
        <div
          className={cn('h-full rounded-full transition-all duration-300', barClass)}
          style={{ width: `${Math.max(0, Math.min(100, displayScore))}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-muted-foreground leading-relaxed">{readiness.summary}</p>

      {variant === 'evidence' && missingEvidence.length > 0 && (
        <div className="mt-3">
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            建议优先补充
          </p>
          <ul className="space-y-1.5">
            {missingEvidence.map((s) => (
              <li
                key={s.item}
                className="flex items-start gap-2 rounded-md border border-amber-200/60 bg-amber-50/80 px-2.5 py-1.5 text-xs text-amber-950 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100"
              >
                <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {s.item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {variant === 'evidence' && requiredSuggestions.some((s) => s.status === 'covered') && (
        <div className="mt-2 flex flex-wrap gap-1">
          {requiredSuggestions
            .filter((s) => s.status === 'covered')
            .map((s) => (
              <span
                key={s.item}
                className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-800 dark:text-emerald-200"
              >
                <CheckCircle2 className="h-3 w-3" />
                {s.item}
              </span>
            ))}
        </div>
      )}

      {variant === 'docgen' && readiness.docgen_blockers && readiness.docgen_blockers.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs text-amber-900 dark:text-amber-100">
          {readiness.docgen_blockers.map((b) => (
            <li key={b} className="flex items-start gap-1.5">
              <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {b}
            </li>
          ))}
        </ul>
      )}

      {variant === 'docgen' && readiness.docgen_recommendation === 'ready' && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 className="h-3.5 w-3.5" />
          材料充分，可直接生成文书。
        </p>
      )}

      {variant === 'docgen' && readiness.docgen_recommendation === 'caution' && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-300">
          <CircleAlert className="h-3.5 w-3.5 shrink-0" />
          综合评分 {readiness.combined_score ?? readiness.readiness_score} 分，可生成文书但材料可能不够完整。
        </p>
      )}

      {variant === 'docgen' && readiness.docgen_recommendation === 'not_ready' && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-rose-700 dark:text-rose-300">
          <CircleAlert className="h-3.5 w-3.5 shrink-0" />
          综合评分 {readiness.combined_score ?? readiness.readiness_score} 分，请先补充材料再生成文书。
        </p>
      )}

      {readiness.next_actions.length > 0 && variant === 'compact' && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {readiness.next_actions.slice(0, 2).map((action) => (
            <button
              key={`${action.label}-${action.route}`}
              type="button"
              onClick={() => navigate(action.route)}
              className="cursor-pointer rounded-md border px-2 py-0.5 text-[10px] font-medium transition-colors hover:bg-accent"
              title={action.reason}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}

      {readiness.next_actions.length > 0 && variant !== 'compact' && (
        <div className="mt-3 flex flex-wrap gap-2">
          {readiness.next_actions.slice(0, 3).map((action) => (
            <button
              key={`${action.label}-${action.route}`}
              type="button"
              onClick={() => navigate(action.route)}
              className="cursor-pointer rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors hover:bg-accent"
              title={action.reason}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
