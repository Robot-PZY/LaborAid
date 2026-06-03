import { useNavigate } from 'react-router-dom';
import { ArrowRight, Briefcase, FileWarning, Scale } from 'lucide-react';
import scenarios from '@/config/labor/demo-scenarios.json';
import { Surface, Badge } from '@/components/ui/primitives';

const ICONS: Record<string, typeof Scale> = {
  wage_arrears: Briefcase,
  illegal_termination: FileWarning,
  no_written_contract: Scale,
};

type DemoScenario = {
  id: string;
  title: string;
  causeLabel: string;
  route: string;
  intakeText: string;
};

const LIST = scenarios as DemoScenario[];

interface DemoScenarioStripProps {
  onPickText?: (text: string) => void;
}

export default function DemoScenarioStrip({ onPickText }: DemoScenarioStripProps) {
  const navigate = useNavigate();

  const handlePick = (s: DemoScenario) => {
    if (onPickText) {
      onPickText(s.intakeText);
      return;
    }
    navigate(`${s.route}?demo=${s.id}`);
  };

  return (
    <Surface padding="md" className="border-accent/20 bg-gradient-to-br from-accent/6 via-card to-card">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-accent">
            演示快捷入口
          </p>
          <p className="mt-0.5 text-sm text-muted-foreground">
            一键填入典型案情，直接体验 AI 诊断与四步维权流程
          </p>
        </div>
        <Badge tone="accent">比赛演示</Badge>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {LIST.map((s) => {
          const Icon = ICONS[s.id] || Scale;
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => handlePick(s)}
              className="group cursor-pointer rounded-xl border border-border/70 bg-background/80 p-4 text-left transition-all hover:border-accent/40 hover:bg-accent/5 hover:shadow-card"
            >
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/12 text-accent">
                  <Icon className="h-5 w-5" strokeWidth={1.75} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-foreground">{s.title}</p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">{s.causeLabel}</p>
                </div>
                <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-accent opacity-40 transition-all group-hover:translate-x-0.5 group-hover:opacity-100" />
              </div>
            </button>
          );
        })}
      </div>
    </Surface>
  );
}
