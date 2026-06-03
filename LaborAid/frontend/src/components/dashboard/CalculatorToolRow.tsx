import { ArrowUpRight, Calculator } from 'lucide-react';

type Props = {
  onOpen: (route: string) => void;
};

/** 首页「更多工具」中的计算器入口（时效 + 赔偿） */
export default function CalculatorToolRow({ onOpen }: Props) {
  return (
    <div className="px-3 py-3">
      <div className="flex items-center gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-border/60 bg-gradient-to-br from-card to-muted/30 text-slate-700 shadow-sm dark:text-slate-300">
          <Calculator className="h-5 w-5" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-medium text-foreground">计算器</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            仲裁时效、经济补偿与赔偿金试算
          </p>
        </div>
      </div>
      <div className="mt-2.5 flex flex-wrap gap-2 pl-[3.75rem]">
        <button
          type="button"
          onClick={() => onOpen('/tools/limitation')}
          className="inline-flex cursor-pointer items-center gap-1 rounded-full border border-border/70 bg-background px-3 py-1 text-xs font-medium text-foreground transition-colors hover:border-accent/40 hover:bg-accent/10"
        >
          时效计算
          <ArrowUpRight className="h-3 w-3 text-accent" />
        </button>
        <button
          type="button"
          onClick={() => onOpen('/tools/compensation')}
          className="inline-flex cursor-pointer items-center gap-1 rounded-full border border-border/70 bg-background px-3 py-1 text-xs font-medium text-foreground transition-colors hover:border-accent/40 hover:bg-accent/10"
        >
          赔偿计算
          <ArrowUpRight className="h-3 w-3 text-accent" />
        </button>
      </div>
    </div>
  );
}
