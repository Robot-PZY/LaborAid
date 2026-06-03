import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  CheckCircle2,
  Circle,
  ExternalLink,
  Loader2,
  MapPin,
} from 'lucide-react';
import type { IntakeAnalyzeResult } from '@/lib/api/intake';
import type { IntakePlanStep, IntakeSession } from '@/lib/intake-session';
import CredibilityBar from '@/components/ui/CredibilityBar';
import { Button, Badge } from '@/components/ui/primitives';
import { useToast } from '@/lib/toast';
import {
  buildFallbackPlanFromTools,
  executePlanStep,
  resolveOfficialLinkUrl,
  resolveStepExternalUrl,
  resultToSession,
  startRecommendedPlan,
} from '@/lib/intake-plan';
import {
  EMPTY_CASE_PROGRESS,
  fetchCaseProgress,
  getActivePlanStepNumber,
  isIntakePlanStepDone,
  type CaseProgress,
} from '@/lib/case-progress';
import { loadIntakeSession, saveIntakeSession } from '@/lib/intake-session';

interface IntakePlanResultProps {
  result: IntakeAnalyzeResult;
  inputText: string;
  onReset: () => void;
  onBack?: () => void;
}

function stepIcon(done: boolean, active: boolean) {
  if (done) return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
  if (active) return <MapPin className="h-4 w-4 text-accent" />;
  return <Circle className="h-4 w-4 text-muted-foreground/50" />;
}

export default function IntakePlanResult({ result, inputText, onReset, onBack }: IntakePlanResultProps) {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState<string | null>(null);
  const [planStarting, setPlanStarting] = useState(false);
  const [progress, setProgress] = useState<CaseProgress>(EMPTY_CASE_PROGRESS);
  const [progressTick, setProgressTick] = useState(0);

  const session =
    loadIntakeSession() ||
    resultToSession(result, [inputText, result.extracted_from_images].filter(Boolean).join('\n\n'));

  const plan = session.actionPlan || buildFallbackPlanFromTools(result);
  const steps = plan?.steps ?? [];

  const refreshProgress = useCallback(() => {
    setProgressTick((n) => n + 1);
  }, []);

  useEffect(() => {
    const caseId = session.createdCaseId ?? null;
    if (!caseId) {
      setProgress(EMPTY_CASE_PROGRESS);
      return;
    }
    let cancelled = false;
    fetchCaseProgress(caseId).then((p) => {
      if (!cancelled) setProgress(p);
    });
    return () => {
      cancelled = true;
    };
  }, [session.createdCaseId, progressTick]);

  useEffect(() => {
    const onFocus = () => refreshProgress();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [refreshProgress]);

  const activeStepNum = getActivePlanStepNumber(steps, progress, session.createdCaseId);

  const handleStartPlan = async () => {
    setPlanStarting(true);
    try {
      const s = loadIntakeSession() || session;
      await startRecommendedPlan(s, navigate);
      refreshProgress();
      toast('已为您建立案件，请继续下一步', 'success');
    } catch {
      toast('执行计划失败，请重试', 'error');
    } finally {
      setPlanStarting(false);
    }
  };

  const handleStep = async (step: IntakePlanStep) => {
    setLoading(`step-${step.step}`);
    try {
      const s = loadIntakeSession() || session;
      if (step.step_type === 'official_external' || step.action === 'external') {
        const url = resolveStepExternalUrl(step);
        if (url) {
          window.open(url, '_blank', 'noopener,noreferrer');
          toast('已打开官方网页', 'success');
        }
        saveIntakeSession({ ...s, currentStep: step.step + 1 });
        return;
      }
      await executePlanStep(step, s, navigate);
      if (step.step_type === 'create_case') {
        toast('案件已创建', 'success');
      }
      refreshProgress();
    } catch {
      toast('操作失败，请重试', 'error');
    } finally {
      setLoading(null);
    }
  };
  return (
    <div className="mt-4 space-y-4">
      <div>
        <Badge tone="accent">{result.cause_label}</Badge>
        {result.intake_mode === 'structured' && result.channel_id && (
          <Badge className="ml-2" tone="neutral">
            专项通道
          </Badge>
        )}
        <p className="mt-2 text-sm text-muted-foreground">{result.summary}</p>
      </div>

      <CredibilityBar
        score={result.credibility.score}
        needsHumanReview={result.credibility.needs_human_review}
        reason={result.credibility.reason}
      />

      {result.missing_info.length > 0 && (
        <div className="rounded-[var(--radius-md)] border border-amber-200/80 bg-amber-50/60 px-3 py-2 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/40 dark:text-amber-100">
          <p className="font-medium">建议补充以下信息</p>
          <ul className="mt-1 list-inside list-disc">
            {result.missing_info.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      )}

      {result.evidence_checklist.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground">建议准备的证据</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {result.evidence_checklist.map((item) => (
              <Badge key={item} tone="neutral">
                {item}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {plan && (
        <div className="rounded-xl border border-accent/25 bg-card p-4 shadow-sm">
          <h3 className="font-display text-sm font-semibold">{plan.title}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            共 {steps.length} 步，第一步将建立您的案件档案
          </p>
          <ol className="mt-3 space-y-2">
            {steps.map((step) => {
              const done = isIntakePlanStepDone(step, progress, session.createdCaseId);
              const active = step.step === activeStepNum && !done;
              const isExternal = step.step_type === 'official_external' || step.action === 'external';
              return (
                <li
                  key={step.step}
                  className={`flex flex-col gap-2 rounded-lg border p-3 sm:flex-row sm:items-center sm:justify-between ${
                    active ? 'border-accent/40 bg-accent/5' : 'border-border/60'
                  }`}
                >
                  <div className="flex gap-2">
                    <span className="mt-0.5 shrink-0">{stepIcon(done, active)}</span>
                    <div>
                      <p className="text-sm font-medium">
                        {step.step}. {step.label}
                        {step.optional && (
                          <span className="ml-1 text-xs font-normal text-muted-foreground">
                            （可选）
                          </span>
                        )}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{step.reason}</p>
                    </div>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant={active ? 'secondary' : 'outline'}
                    disabled={loading === `step-${step.step}`}
                    onClick={() => handleStep(step)}
                  >
                    {loading === `step-${step.step}` ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : isExternal ? (
                      <ExternalLink className="h-3.5 w-3.5" />
                    ) : (
                      <ArrowRight className="h-3.5 w-3.5" />
                    )}
                    {isExternal ? '打开官方' : active && step.step_type === 'create_case' ? '建案' : '前往'}
                  </Button>
                </li>
              );
            })}
          </ol>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button type="button" onClick={handleStartPlan} disabled={planStarting}>
              {planStarting ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
              开始办理
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={onReset}>
              {result.intake_mode === 'structured' ? '重新填写' : '重新描述'}
            </Button>
            {onBack && (
              <Button type="button" variant="ghost" size="sm" onClick={onBack}>
                返回选择
              </Button>
            )}
          </div>
        </div>
      )}

      {result.official_links.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground">相关办事渠道</p>
          <ul className="mt-1.5 space-y-1.5">
            {result.official_links.map((link) => {
              const url = resolveOfficialLinkUrl(link.id);
              return (
                <li key={link.id} className="text-xs">
                  {url ? (
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-accent hover:underline"
                    >
                      {link.title}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    <span className="text-muted-foreground">{link.title}</span>
                  )}
                  {link.when && <span className="text-muted-foreground"> — {link.when}</span>}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
