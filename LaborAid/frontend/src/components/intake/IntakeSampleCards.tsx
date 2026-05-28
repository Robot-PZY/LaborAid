import samples from '@/config/labor/intake-samples.json';

export type IntakeSample = {
  id: string;
  emoji: string;
  title: string;
  text: string;
};

const SAMPLE_LIST = samples as IntakeSample[];

interface IntakeSampleCardsProps {
  onPick: (text: string) => void;
  disabled?: boolean;
}

export default function IntakeSampleCards({ onPick, disabled }: IntakeSampleCardsProps) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground">常见情形示例</p>
      <div className="grid gap-2 sm:grid-cols-3">
        {SAMPLE_LIST.map((s) => (
          <button
            key={s.id}
            type="button"
            disabled={disabled}
            onClick={() => onPick(s.text)}
            className="rounded-lg border border-border/70 bg-background/80 p-3 text-left text-sm transition-all hover:border-accent/40 hover:bg-accent/5 disabled:opacity-50"
          >
            <span className="text-lg" aria-hidden>
              {s.emoji}
            </span>
            <p className="mt-1 font-medium">{s.title}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
