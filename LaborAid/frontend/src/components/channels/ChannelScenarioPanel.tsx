import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowUpRight,
  CheckCircle2,
  Circle,
  ExternalLink,
  FileText,
  Phone,
  Search,
  ShieldAlert,
} from 'lucide-react';
import type { ChannelConfig, ChannelScenario, PlatformCategoryId } from '@/lib/channels';
import { buildSearchLink, runScenarioStep, scenarioStepLabel } from '@/lib/channel-nav';
import {
  loadScenarioChecklist,
  saveScenarioChecklist,
} from '@/lib/channel-checklist';
import { Button, Surface, Badge } from '@/components/ui/primitives';

type Props = {
  channel: ChannelConfig;
  scenario: ChannelScenario;
  onBack: () => void;
  openReport: () => void;
  openPlatform?: (category: PlatformCategoryId) => void;
};

export default function ChannelScenarioPanel({ channel, scenario, onBack, openReport, openPlatform }: Props) {
  const navigate = useNavigate();
  const [checked, setChecked] = useState<Record<number, boolean>>(() =>
    loadScenarioChecklist(channel.id, scenario.id),
  );

  useEffect(() => {
    setChecked(loadScenarioChecklist(channel.id, scenario.id));
  }, [channel.id, scenario.id]);

  const ctx = useMemo(
    () => ({
      channelId: channel.id,
      scenarioId: scenario.id,
      navigate,
      openReport,
      openPlatform,
    }),
    [channel.id, scenario.id, navigate, openReport, openPlatform],
  );

  const toggleCheck = (idx: number) => {
    setChecked((prev) => {
      const next = { ...prev, [idx]: !prev[idx] };
      saveScenarioChecklist(channel.id, scenario.id, next);
      return next;
    });
  };

  const checklistDone = scenario.evidence_checklist?.filter((_, i) => checked[i]).length ?? 0;
  const checklistTotal = scenario.evidence_checklist?.length ?? 0;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          ← 选择其他情形
        </Button>
        <Badge tone="accent">{channel.title}</Badge>
      </div>

      <div>
        <h2 className="font-display text-xl font-semibold sm:text-2xl">{scenario.title}</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">{scenario.summary}</p>
        {scenario.path_hint && (
          <Surface className="mt-4 border-accent/25 bg-accent/5">
            <p className="text-sm font-medium">推荐路径</p>
            <p className="mt-1 text-sm text-muted-foreground">{scenario.path_hint}</p>
          </Surface>
        )}
        {scenario.who_to_sue && (
          <p className="mt-3 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">告谁：</span>
            {scenario.who_to_sue}
          </p>
        )}
      </div>

      {scenario.evidence_checklist && scenario.evidence_checklist.length > 0 && (
        <section>
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="font-medium">证据清单</h3>
            <span className="text-xs text-muted-foreground">
              已勾选 {checklistDone}/{checklistTotal}
            </span>
          </div>
          <Surface padding="none" className="divide-y divide-border/60">
            {scenario.evidence_checklist.map((item, idx) => (
              <button
                key={item}
                type="button"
                onClick={() => toggleCheck(idx)}
                className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/30"
              >
                {checked[idx] ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                ) : (
                  <Circle className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                )}
                <span className={`text-sm ${checked[idx] ? 'text-muted-foreground line-through' : ''}`}>
                  {item}
                </span>
              </button>
            ))}
          </Surface>
        </section>
      )}

      <section>
        <h3 className="mb-3 font-medium">分步指引</h3>
        <Surface padding="none" className="divide-y divide-border/60">
          {scenario.steps.map((step, idx) => (
            <div key={`${step.title}-${idx}`} className="flex gap-4 px-5 py-4">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border font-display text-sm font-semibold">
                {idx + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-medium">{step.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{step.detail}</p>
                {step.action !== 'phone' && (
                  <button
                    type="button"
                    onClick={() => runScenarioStep(step, ctx)}
                    className="mt-2 inline-flex items-center gap-1 text-sm font-medium hover:underline"
                  >
                    {step.action === 'docgen' && <FileText className="h-3.5 w-3.5" />}
                    {step.action === 'search' && <Search className="h-3.5 w-3.5" />}
                    {step.action === 'report' && <ShieldAlert className="h-3.5 w-3.5" />}
                    {(step.action === 'internal' || step.action === 'external') && (
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    )}
                    {scenarioStepLabel(step)} →
                  </button>
                )}
                {step.action === 'phone' && step.phones && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {step.phones.map((phone) => (
                      <a
                        key={phone}
                        href={`tel:${phone}`}
                        className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1 text-xs font-medium hover:bg-muted/50"
                      >
                        <Phone className="h-3 w-3" />
                        {phone}
                      </a>
                    ))}
                  </div>
                )}
                {step.action === 'external' && step.url && (
                  <a
                    href={step.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground hover:underline"
                  >
                    {step.url.replace(/^https?:\/\//, '').slice(0, 40)}…
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </Surface>
      </section>

      {(scenario.law_searches?.length ?? 0) > 0 && (
        <section>
          <h3 className="mb-3 font-medium">相关法条检索</h3>
          <div className="flex flex-wrap gap-2">
            {scenario.law_searches!.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => navigate(buildSearchLink(q))}
                className="rounded-full border border-border px-3 py-1.5 text-xs hover:bg-muted/50"
              >
                {q}
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
