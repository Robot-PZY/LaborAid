import { CheckCircle2, CircleAlert, CircleDashed } from 'lucide-react';
import type { CaseReadinessSummary } from '@/lib/api';
import { DonutChart, CHART_COLORS } from '@/components/charts/SimpleCharts';
import { cn } from '@/lib/utils';

interface EvidenceCoveragePanelProps {
  readiness: CaseReadinessSummary;
  className?: string;
}

export default function EvidenceCoveragePanel({ readiness, className }: EvidenceCoveragePanelProps) {
  const suggestions = readiness.evidence_suggestions ?? [];
  const required = suggestions.filter((s) => s.priority === 'required');
  const covered = required.filter((s) => s.status === 'covered').length;
  const missing = required.filter((s) => s.status === 'missing').length;
  const optional = suggestions.filter((s) => s.priority === 'optional');
  const displayScore =
    readiness.combined_score ?? readiness.readiness_score;

  const segments = [
    { label: '已覆盖', value: covered, color: CHART_COLORS.evidence },
    { label: '待补充', value: missing, color: 'hsl(32 90% 48%)' },
  ];

  if (required.length === 0) return null;

  return (
    <div className={cn('rounded-xl border border-border/70 bg-card p-4 shadow-sm', className)}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <DonutChart
          segments={segments}
          size={140}
          stroke={18}
          centerLabel={`${displayScore}%`}
          centerSub="综合完整度"
        />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">
            关键证据覆盖 {covered}/{required.length}
          </p>
          {readiness.cause_label && (
            <p className="mt-0.5 text-xs text-muted-foreground">案由：{readiness.cause_label}</p>
          )}
          {readiness.chain_completeness_score != null && (
            <p className="mt-1 text-[11px] text-muted-foreground">
              材料完整度 {readiness.readiness_score}% · 证据链 {readiness.chain_completeness_score}%
              → 综合 {displayScore}%
            </p>
          )}
          <ul className="mt-3 max-h-48 space-y-1.5 overflow-y-auto">
            {required.map((s) => (
              <li
                key={s.item}
                className={cn(
                  'flex items-start gap-2 rounded-md px-2 py-1.5 text-xs',
                  s.status === 'covered'
                    ? 'bg-emerald-500/10 text-emerald-900 dark:text-emerald-100'
                    : 'bg-amber-500/10 text-amber-950 dark:text-amber-100',
                )}
              >
                {s.status === 'covered' ? (
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                ) : (
                  <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                )}
                <span>{s.item}</span>
              </li>
            ))}
            {optional.map((s) => (
              <li
                key={s.item}
                className="flex items-start gap-2 rounded-md px-2 py-1 text-[11px] text-muted-foreground"
              >
                <CircleDashed className="mt-0.5 h-3 w-3 shrink-0" />
                <span>
                  {s.item}
                  {s.status === 'covered' ? '（已有）' : '（可选）'}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
