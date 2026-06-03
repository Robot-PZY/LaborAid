import { Briefcase, GraduationCap, HeartHandshake } from 'lucide-react';
import samples from '@/config/labor/intake-samples.json';
import { cn } from '@/lib/utils';

export type IntakeSample = {
  id: string;
  title: string;
  text: string;
  causeLabel?: string;
};

const ICONS: Record<string, typeof Briefcase> = {
  'migrant-wage': Briefcase,
  'intern-fire': GraduationCap,
  'female-pregnancy': HeartHandshake,
};

const SAMPLE_LIST = samples as IntakeSample[];

interface IntakeSampleCardsProps {
  onPick: (text: string) => void;
  disabled?: boolean;
  className?: string;
}

export default function IntakeSampleCards({ onPick, disabled, className }: IntakeSampleCardsProps) {
  return (
    <div className={cn('space-y-2', className)}>
      <p className="text-xs font-medium text-muted-foreground">常见情形示例（点击填入）</p>
      <div className="grid gap-2 sm:grid-cols-3">
        {SAMPLE_LIST.map((s) => {
          const Icon = ICONS[s.id] || Briefcase;
          return (
            <button
              key={s.id}
              type="button"
              disabled={disabled}
              onClick={() => onPick(s.text)}
              className="group cursor-pointer rounded-lg border border-border/70 bg-background/80 p-3 text-left text-sm transition-all hover:border-accent/40 hover:bg-accent/5 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted/80 text-accent transition-colors group-hover:bg-accent/15">
                <Icon className="h-4 w-4" strokeWidth={1.75} />
              </span>
              <p className="mt-2 font-medium leading-snug">{s.title}</p>
              {s.causeLabel && (
                <p className="mt-0.5 text-[10px] text-muted-foreground">{s.causeLabel}</p>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
