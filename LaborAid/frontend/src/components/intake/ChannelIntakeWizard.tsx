import { useEffect, useMemo, useState } from 'react';
import { AxiosError } from 'axios';
import { AlertCircle, ArrowLeft, ChevronRight, Loader2 } from 'lucide-react';
import { getChannel, type ChannelConfig } from '@/lib/channels';
import {
  getScenarioFormFields,
  listIntakeScenarios,
  renderStructuredCaseFacts,
  validateFormAnswers,
} from '@/lib/intake-scenarios';
import { intakeApi, type IntakeAnalyzeResult } from '@/lib/api/intake';
import { resultToSession, sessionToAnalyzeResult } from '@/lib/intake-plan';
import { saveReportProvinceFromWorkRegion } from '@/lib/report-province';
import type { IntakeSession } from '@/lib/intake-session';
import DynamicForm from '@/components/intake/DynamicForm';
import IntakePlanResult from '@/components/intake/IntakePlanResult';
import { Button, Badge, Surface } from '@/components/ui/primitives';
import { cn } from '@/lib/utils';
import { CHANNEL_THEME } from '@/components/guidance/GuidanceHubPanel';

const CHANNEL_IDS = ['migrant-worker', 'intern-probation', 'female-worker'] as const;

type Props = {
  onBack: () => void;
  initialChannelId?: string | null;
  initialScenarioId?: string | null;
  resumeSession?: IntakeSession | null;
};

function resolveStructuredCaseFacts(
  data: IntakeAnalyzeResult,
  channelId: string,
  scenarioId: string,
  answers: Record<string, string>,
): string {
  if (data.case_facts?.trim()) return data.case_facts.trim();
  const channel = getChannel(channelId);
  const scenario = channel?.scenarios?.find((s) => s.id === scenarioId);
  if (channel && scenario) {
    const fields = getScenarioFormFields(channelId, scenarioId);
    return renderStructuredCaseFacts(channel.title, scenario.title, answers, fields);
  }
  return data.summary;
}

export default function ChannelIntakeWizard({
  onBack,
  initialChannelId,
  initialScenarioId,
  resumeSession,
}: Props) {
  const [channelId, setChannelId] = useState<string | null>(initialChannelId ?? null);
  const [scenarioId, setScenarioId] = useState<string | null>(initialScenarioId ?? null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<IntakeAnalyzeResult | null>(null);
  const [planInputText, setPlanInputText] = useState('');

  useEffect(() => {
    if (initialChannelId) setChannelId(initialChannelId);
    if (initialScenarioId) setScenarioId(initialScenarioId);
  }, [initialChannelId, initialScenarioId]);

  useEffect(() => {
    if (!resumeSession?.actionPlan?.steps?.length && !resumeSession?.recommendedTools?.length) {
      return;
    }
    setChannelId(resumeSession.channelId ?? null);
    setScenarioId(resumeSession.scenarioId ?? null);
    setAnswers(resumeSession.structuredAnswers ?? {});
    setResult(sessionToAnalyzeResult(resumeSession));

    let facts = resumeSession.caseFacts || resumeSession.inputText || resumeSession.summary || '';
    if (resumeSession.channelId && resumeSession.scenarioId && resumeSession.structuredAnswers) {
      const ch = getChannel(resumeSession.channelId);
      const scenario = ch?.scenarios?.find((s) => s.id === resumeSession.scenarioId);
      if (ch && scenario) {
        const rebuilt = renderStructuredCaseFacts(
          ch.title,
          scenario.title,
          resumeSession.structuredAnswers,
          getScenarioFormFields(resumeSession.channelId, resumeSession.scenarioId),
        );
        if (rebuilt.length > facts.length) facts = rebuilt;
      }
    }
    setPlanInputText(facts);
    if (facts.length > (resumeSession.caseFacts?.length || 0)) {
      resultToSession(sessionToAnalyzeResult(resumeSession), facts);
    }
  }, [resumeSession]);

  const channel = channelId ? getChannel(channelId) : undefined;
  const scenarios = channel ? listIntakeScenarios(channel) : [];
  const scenario = scenarios.find((s) => s.id === scenarioId);
  const fields = useMemo(
    () => (channelId && scenarioId ? getScenarioFormFields(channelId, scenarioId) : []),
    [channelId, scenarioId],
  );

  const handleFieldChange = (id: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [id]: value }));
  };

  const handleSubmit = async () => {
    if (!channelId || !scenarioId) return;
    const validationErrors = validateFormAnswers(fields, answers);
    if (validationErrors.length) {
      setError(validationErrors[0]);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await intakeApi.structured({
        channel_id: channelId,
        scenario_id: scenarioId,
        answers,
      });
      const facts = resolveStructuredCaseFacts(data, channelId, scenarioId, answers);
      setResult(data);
      setPlanInputText(facts);
      resultToSession(data, facts);
      const workRegion = data.structured_answers?.work_region;
      if (typeof workRegion === 'string') {
        saveReportProvinceFromWorkRegion(workRegion);
      }
    } catch (err: unknown) {
      const detail =
        err instanceof AxiosError ? err.response?.data?.detail || err.response?.data?.message : null;
      setError(typeof detail === 'string' ? detail : '提交失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setPlanInputText('');
    setAnswers({});
    setScenarioId(null);
    setError('');
  };

  if (result) {
    return (
      <IntakePlanResult
        result={result}
        inputText={planInputText || result.summary}
        onReset={handleReset}
        onBack={onBack}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
          返回选择
        </Button>
        {channel && <Badge tone="accent">{channel.title}</Badge>}
        {scenario && <Badge>{scenario.title}</Badge>}
      </div>

      {!channelId ? (
        <ChannelPicker
          onSelect={(id) => {
            setChannelId(id);
            setScenarioId(null);
            setAnswers({});
          }}
        />
      ) : !scenarioId ? (
        <ScenarioPicker
          channel={channel!}
          scenarios={scenarios}
          onSelect={(id) => {
            setScenarioId(id);
            setAnswers({});
          }}
          onBackChannel={() => {
            setChannelId(null);
            setScenarioId(null);
          }}
        />
      ) : (
        <Surface padding="lg" className="space-y-4">
          <div>
            <h3 className="font-display text-lg font-semibold">{scenario?.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{scenario?.summary}</p>
          </div>
          <DynamicForm fields={fields} values={answers} onChange={handleFieldChange} disabled={loading} />
          {(error || scenario?.path_hint) && (
            <p
              className={cn(
                'flex items-start gap-1.5 text-sm',
                error ? 'text-amber-800 dark:text-amber-200' : 'text-muted-foreground',
              )}
            >
              {error && <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />}
              {error || scenario?.path_hint}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => setScenarioId(null)}>
              重选情形
            </Button>
            <Button type="button" onClick={handleSubmit} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {loading ? '生成方案中…' : '生成维权安排'}
            </Button>
          </div>
        </Surface>
      )}
    </div>
  );
}

function ChannelPicker({ onSelect }: { onSelect: (id: string) => void }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {CHANNEL_IDS.map((id) => {
        const ch = getChannel(id);
        if (!ch) return null;
        const theme = CHANNEL_THEME[id];
        return (
          <button
            key={id}
            type="button"
            onClick={() => onSelect(id)}
            className={cn(
              'rounded-[var(--radius-md)] border border-border/70 border-l-[3px] bg-card p-4 text-left shadow-card transition-all hover:border-accent/40 hover:shadow-card-hover',
              theme?.border,
            )}
          >
            <p className="font-medium">{ch.title}</p>
            <p className="mt-1 text-xs text-muted-foreground">{ch.subtitle}</p>
            <span className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-accent">
              选择
              <ChevronRight className="h-3.5 w-3.5" />
            </span>
          </button>
        );
      })}
    </div>
  );
}

function ScenarioPicker({
  channel,
  scenarios,
  onSelect,
  onBackChannel,
}: {
  channel: ChannelConfig;
  scenarios: ReturnType<typeof listIntakeScenarios>;
  onSelect: (id: string) => void;
  onBackChannel: () => void;
}) {
  return (
    <div className="space-y-3">
      <Button type="button" variant="ghost" size="sm" onClick={onBackChannel}>
        ← 重选身份
      </Button>
      <div className="grid gap-3 sm:grid-cols-2">
        {scenarios.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onSelect(s.id)}
            className="rounded-[var(--radius-md)] border border-border/70 bg-card p-4 text-left shadow-card transition-all hover:border-accent/40 hover:shadow-card-hover"
          >
            <p className="font-medium">{s.title}</p>
            <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{s.summary}</p>
            <span className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-accent">
              填写信息
              <ChevronRight className="h-3.5 w-3.5" />
            </span>
          </button>
        ))}
      </div>
      {scenarios.length === 0 && (
        <p className="text-sm text-muted-foreground">该身份暂无可用场景，请返回选择其他身份或使用普通入口。</p>
      )}
    </div>
  );
}
