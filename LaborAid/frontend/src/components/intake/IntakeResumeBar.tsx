import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, ListChecks, Sparkles, X } from 'lucide-react';
import {
  clearIntakeSession,
  getIntakeResumeUrl,
  hasActiveIntakePlan,
  loadIntakeSession,
  subscribeIntakeSession,
  type IntakeSession,
} from '@/lib/intake-session';
import { Button } from '@/components/ui/primitives';

function getStepLabel(session: IntakeSession): string {
  const plan = session.actionPlan;
  if (!plan?.steps?.length) return '';
  const cur = session.currentStep ?? 1;
  const step = plan.steps.find((s) => s.step === cur) ?? plan.steps[0];
  return `第 ${cur}/${plan.steps.length} 步：${step.label}`;
}

export default function IntakeResumeBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [session, setSession] = useState<IntakeSession | null>(() =>
    hasActiveIntakePlan() ? loadIntakeSession() : null,
  );
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const refresh = () => {
      setSession(hasActiveIntakePlan() ? loadIntakeSession() : null);
      setDismissed(false);
    };
    refresh();
    return subscribeIntakeSession(refresh);
  }, []);

  useEffect(() => {
    setDismissed(false);
  }, [location.pathname]);

  if (!session || dismissed) return null;

  // 首页自带快速咨询区块，不在此重复提示
  if (location.pathname === '/') return null;

  const stepHint = getStepLabel(session);

  return (
    <div
      className="mb-4 flex flex-col gap-3 rounded-xl border border-accent/30 bg-gradient-to-r from-accent/10 via-card to-card px-4 py-3 shadow-sm sm:flex-row sm:items-center"
      role="region"
      aria-label="维权咨询方案"
    >
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-accent">
          <Sparkles className="h-4 w-4" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">
            您的维权方案
            <span className="ml-2 font-normal text-muted-foreground">· {session.causeLabel}</span>
          </p>
          <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
            {session.summary}
          </p>
          {stepHint && (
            <p className="mt-1 flex items-center gap-1 text-xs text-accent">
              <ListChecks className="h-3.5 w-3.5 shrink-0" />
              {stepHint}
            </p>
          )}
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          onClick={() => navigate(getIntakeResumeUrl(session))}
        >
          <ArrowRight className="h-3.5 w-3.5" />
          查看完整方案
        </Button>
        {location.pathname !== '/' && (
          <Button type="button" size="sm" variant="outline" onClick={() => navigate('/')}>
            回首页
          </Button>
        )}
        <button
          type="button"
          onClick={() => {
            if (window.confirm('确定结束本次咨询方案？可随时重新描述案情。')) {
              clearIntakeSession();
              setSession(null);
            }
          }}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="结束本次方案"
          title="结束本次方案"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
