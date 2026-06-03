import { useState } from 'react';
import {
  Loader2,
  Bot,
  ArrowUpRight,
  CircleAlert,
  ChevronDown,
  ChevronUp,
  MessageCircle,
  Send,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { caseApi, type CaseAgentNextStep } from '@/lib/api';
import { loadChainAnalysis } from '@/lib/case-ai-cache';
import { cn } from '@/lib/utils';
import CaseAgentsStrip from '@/components/cases/CaseAgentsStrip';
import { useCaseAgents } from '@/hooks/useCaseAgents';

const STAGE_LABELS: Record<string, string> = {
  path: '路径',
  evidence: '证据',
  documents: '文书',
  research: '报告',
  complete: '完成',
};

const QUICK_QUESTIONS = [
  '我还缺什么证据？',
  '现在能生成文书吗？',
  '下一步该做什么？',
];

interface CaseAgentCoachProps {
  step: CaseAgentNextStep | null;
  caseId?: number | null;
  loading?: boolean;
  error?: string;
  onRefresh?: () => void;
  className?: string;
  compact?: boolean;
}

function taskStatusClass(status: string) {
  if (status === 'done') return 'bg-emerald-500/15 text-emerald-800 dark:text-emerald-200';
  if (status === 'active') return 'bg-violet-500/15 text-violet-800 dark:text-violet-200';
  return 'bg-muted text-muted-foreground';
}

export default function CaseAgentCoach({
  step,
  caseId,
  loading = false,
  error,
  onRefresh,
  className,
  compact = false,
}: CaseAgentCoachProps) {
  const navigate = useNavigate();
  const { agents: agentsList, loading: agentsLoading } = useCaseAgents(caseId ?? null);
  const [chatOpen, setChatOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);
  const [askError, setAskError] = useState('');
  const [suggestedRoute, setSuggestedRoute] = useState<string | null>(null);

  const handleAsk = async (q: string) => {
    if (!caseId || !q.trim()) return;
    setAsking(true);
    setAskError('');
    setAnswer(null);
    try {
      const cached = loadChainAnalysis(caseId);
      const raw = cached?.completeness_score;
      const chainScore =
        raw != null && !Number.isNaN(Number(raw)) ? Math.round(Number(raw)) : undefined;
      const res = await caseApi.askAgent(caseId, q.trim(), { chainScore });
      setAnswer(res.answer);
      setSuggestedRoute(res.suggested_route);
    } catch {
      setAskError('暂时无法回答，请稍后重试');
    } finally {
      setAsking(false);
    }
  };

  if (loading) {
    return (
      <div
        className={cn(
          'rounded-xl border border-violet-500/20 bg-violet-500/5 p-4 text-sm text-muted-foreground',
          className,
        )}
      >
        <Loader2 className="mr-2 inline h-4 w-4 animate-spin text-violet-600" />
        维权助手正在分析下一步…
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-xs', className)}>
        <p className="text-amber-900 dark:text-amber-100">{error}</p>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            className="mt-2 text-xs font-medium text-accent hover:underline"
          >
            重试
          </button>
        )}
      </div>
    );
  }

  if (!step) return null;

  const stageLabel = STAGE_LABELS[step.pipeline_stage] || step.pipeline_stage;
  const showTasks = step.pipeline_tasks.length > 0 && !compact;

  return (
    <div
      className={cn(
        'rounded-xl border border-violet-500/25 bg-gradient-to-br from-violet-500/8 via-card to-card p-4 shadow-sm',
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="flex items-center gap-2 text-sm font-semibold">
          <Bot className="h-4 w-4 text-violet-600 dark:text-violet-400" />
          协作调度
          <span className="rounded-full bg-violet-500/15 px-2 py-0.5 text-[10px] font-medium text-violet-800 dark:text-violet-200">
            {stageLabel}
          </span>
        </h3>
        <div className="flex items-center gap-2">
          {caseId && (
            <button
              type="button"
              onClick={() => setChatOpen((v) => !v)}
              className="inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground"
            >
              <MessageCircle className="h-3 w-3" />
              提问
              {chatOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
          )}
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              className="text-[10px] text-muted-foreground hover:text-foreground"
            >
              刷新
            </button>
          )}
        </div>
      </div>

      <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{step.explanation}</p>

      <CaseAgentsStrip
        agents={agentsList}
        loading={agentsLoading}
        compact={compact}
        className="mt-3"
      />

      {showTasks && (
        <ul className="mt-3 space-y-1.5">
          {step.pipeline_tasks.map((task) => (
            <li key={task.id}>
              <button
                type="button"
                onClick={() => navigate(task.route)}
                className="flex w-full cursor-pointer items-center gap-2 rounded-lg border border-border/60 bg-background/60 px-2.5 py-1.5 text-left text-[11px] transition-colors hover:border-violet-500/30"
              >
                <span
                  className={cn(
                    'shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium',
                    taskStatusClass(task.status),
                  )}
                >
                  {task.status === 'done' ? '完成' : task.status === 'active' ? '进行' : '待做'}
                </span>
                <span className="min-w-0 flex-1 font-medium text-foreground">
                  {task.label}
                  {task.optional && (
                    <span className="ml-1 font-normal text-muted-foreground">（可选）</span>
                  )}
                </span>
                <ArrowUpRight className="h-3 w-3 shrink-0 text-muted-foreground" />
              </button>
            </li>
          ))}
        </ul>
      )}

      {step.blockers.length > 0 && !compact && (
        <ul className="mt-2 space-y-1">
          {step.blockers.slice(0, 3).map((b) => (
            <li
              key={b}
              className="flex items-start gap-1.5 text-[11px] text-amber-900 dark:text-amber-100"
            >
              <CircleAlert className="mt-0.5 h-3 w-3 shrink-0" />
              {b}
            </li>
          ))}
        </ul>
      )}

      <button
        type="button"
        onClick={() => navigate(step.route)}
        className="mt-3 inline-flex w-full cursor-pointer items-center justify-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-violet-700 dark:bg-violet-700 dark:hover:bg-violet-600"
      >
        {step.label}
        <ArrowUpRight className="h-3.5 w-3.5" />
      </button>

      {step.alternatives.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {step.alternatives.map((alt) => (
            <button
              key={`${alt.agent_id}-${alt.route}`}
              type="button"
              onClick={() => navigate(alt.route)}
              title={alt.reason}
              className="cursor-pointer rounded-md border border-border/70 px-2 py-0.5 text-[10px] text-muted-foreground transition-colors hover:border-violet-500/40 hover:text-foreground"
            >
              {alt.label}
            </button>
          ))}
        </div>
      )}

      {chatOpen && caseId && (
        <div className="mt-3 border-t border-border/60 pt-3">
          <div className="flex flex-wrap gap-1.5">
            {QUICK_QUESTIONS.map((q) => (
              <button
                key={q}
                type="button"
                disabled={asking}
                onClick={() => {
                  setQuestion(q);
                  void handleAsk(q);
                }}
                className="cursor-pointer rounded-full border border-border/70 px-2 py-0.5 text-[10px] text-muted-foreground hover:bg-muted/50 disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
          <div className="mt-2 flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void handleAsk(question);
              }}
              placeholder="例如：仲裁时效还剩多久？"
              className="min-w-0 flex-1 rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs"
              maxLength={500}
            />
            <button
              type="button"
              disabled={asking || !question.trim()}
              onClick={() => void handleAsk(question)}
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600 text-white disabled:opacity-50"
            >
              {asking ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
          {askError && <p className="mt-2 text-[11px] text-amber-800">{askError}</p>}
          {answer && (
            <div className="mt-2 rounded-lg border border-violet-500/20 bg-background/80 p-2.5 text-xs leading-relaxed text-foreground">
              {answer}
              {suggestedRoute && (
                <button
                  type="button"
                  onClick={() => navigate(suggestedRoute)}
                  className="mt-2 flex cursor-pointer items-center gap-1 text-[11px] font-medium text-violet-700 dark:text-violet-300"
                >
                  前往建议页面
                  <ArrowUpRight className="h-3 w-3" />
                </button>
              )}
            </div>
          )}
        </div>
      )}

      <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground/80">{step.disclaimer}</p>
    </div>
  );
}
