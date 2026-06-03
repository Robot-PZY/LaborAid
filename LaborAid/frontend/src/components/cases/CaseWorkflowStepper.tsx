import { useNavigate } from 'react-router-dom';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';
import type { CaseWorkflow } from '@/lib/api';
import { cn } from '@/lib/utils';

interface CaseWorkflowStepperProps {
  workflow: CaseWorkflow | null;
  loading?: boolean;
  error?: string;
  className?: string;
  compact?: boolean;
}

function stepCircle(status: string, index: number) {
  if (status === 'done') {
    return (
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white">
        <CheckCircle2 className="h-4 w-4" />
      </span>
    );
  }
  if (status === 'active') {
    return (
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-violet-600 text-xs font-bold text-white">
        {index + 1}
      </span>
    );
  }
  return (
    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-muted text-xs font-medium text-muted-foreground">
      {index + 1}
    </span>
  );
}

export default function CaseWorkflowStepper({
  workflow,
  loading = false,
  error,
  className,
  compact = false,
}: CaseWorkflowStepperProps) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className={cn('text-xs text-muted-foreground', className)}>
        <Loader2 className="mr-1 inline h-3.5 w-3.5 animate-spin" />
        工作流加载中…
      </div>
    );
  }

  if (error) {
    return <p className={cn('text-xs text-amber-800 dark:text-amber-200', className)}>{error}</p>;
  }

  if (!workflow?.steps.length) return null;

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium text-foreground">案件工作流</p>
        <span className="text-[11px] tabular-nums text-muted-foreground">
          {workflow.progress}/{workflow.total_steps} 步
        </span>
      </div>

      {!compact && workflow.summary && (
        <p className="text-xs text-muted-foreground">{workflow.summary}</p>
      )}

      {workflow.ai_hint && !compact && (
        <p className="rounded-lg border border-violet-500/20 bg-violet-500/5 px-2.5 py-2 text-xs leading-relaxed text-foreground">
          {workflow.ai_hint}
        </p>
      )}

      <ol className={cn(compact ? 'flex flex-wrap gap-2' : 'grid gap-2 sm:grid-cols-2 lg:grid-cols-4')}>
        {workflow.steps.map((step, index) => (
          <li key={step.id}>
            <button
              type="button"
              onClick={() => navigate(step.route)}
              className={cn(
                'flex w-full cursor-pointer items-start gap-2.5 rounded-lg border p-3 text-left transition-colors hover:shadow-sm',
                step.status === 'done' && 'border-emerald-500/30 bg-emerald-500/5',
                step.status === 'active' && 'border-violet-500/40 bg-violet-500/8',
                step.status === 'pending' && 'border-border/70 bg-muted/20 opacity-90',
              )}
            >
              {stepCircle(step.status, index)}
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-1.5 text-sm font-medium">
                  {step.label}
                  {step.status === 'active' && (
                    <Circle className="h-2 w-2 fill-violet-500 text-violet-500" />
                  )}
                </span>
                {!compact && (
                  <span className="mt-0.5 block text-[11px] leading-snug text-muted-foreground">
                    {step.hint}
                  </span>
                )}
              </span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
