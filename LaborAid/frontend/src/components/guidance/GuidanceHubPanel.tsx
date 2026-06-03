import { useNavigate } from 'react-router-dom';
import { ArrowUpRight, Compass, HeartHandshake } from 'lucide-react';
import { listIntakeChannels } from '@/lib/intake-scenarios';
import { CAUSE_QUICK_ENTRIES } from '@/lib/guidance-labels';
import { Button, SectionTitle, Surface } from '@/components/ui/primitives';
import { cn } from '@/lib/utils';

export const CHANNEL_THEME: Record<
  string,
  { border: string; chip: string; dot: string }
> = {
  'migrant-worker': {
    border: 'border-l-amber-500',
    chip: 'bg-amber-500/12 text-amber-900 dark:text-amber-100',
    dot: 'bg-amber-500',
  },
  'intern-probation': {
    border: 'border-l-sky-500',
    chip: 'bg-sky-500/12 text-sky-900 dark:text-sky-100',
    dot: 'bg-sky-500',
  },
  'female-worker': {
    border: 'border-l-rose-500',
    chip: 'bg-rose-500/12 text-rose-900 dark:text-rose-100',
    dot: 'bg-rose-500',
  },
};

type GuidanceHubPanelProps = {
  showSectionTitle?: boolean;
  className?: string;
};

/** 首页快捷入口：开始维权 + 办事资源 */
export default function GuidanceHubPanel({
  showSectionTitle = true,
  className,
}: GuidanceHubPanelProps) {
  const navigate = useNavigate();
  const channels = listIntakeChannels();

  return (
    <section className={className}>
      {showSectionTitle && (
        <SectionTitle
          title="维权入口"
          description="首页选择专项或普通方式开始；官方申诉网站与电话见办事资源。"
        />
      )}

      <Surface padding="none" className="overflow-hidden">
        <div className="grid divide-y divide-border/60 lg:grid-cols-2 lg:divide-x lg:divide-y-0">
          <div className="p-5 sm:p-6">
            <div className="flex items-center gap-2 text-accent">
              <HeartHandshake className="h-4 w-4" />
              <h3 className="text-sm font-semibold text-foreground">开始维权</h3>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
              专项通道：农民工、实习生、女职工等按情形填表；普通入口自由描述。
            </p>
            <div className="mt-3 space-y-2">
              {channels.map((ch) => {
                const theme = CHANNEL_THEME[ch.id] ?? {
                  border: 'border-l-accent',
                  dot: 'bg-accent',
                };
                return (
                  <button
                    key={ch.id}
                    type="button"
                    onClick={() => navigate(`/?intake=special&channel=${ch.id}#intake-desk`)}
                    className={cn(
                      'group flex w-full cursor-pointer items-center gap-3 rounded-[var(--radius-md)] border border-border/60 border-l-[3px] bg-card/80 px-3 py-2.5 text-left transition-all hover:border-accent/30 hover:bg-muted/30',
                      theme.border,
                    )}
                  >
                    <span className={cn('h-2 w-2 shrink-0 rounded-full', theme.dot)} aria-hidden />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-foreground">{ch.title}</p>
                      <p className="line-clamp-1 text-xs text-muted-foreground">{ch.subtitle}</p>
                    </div>
                    <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-40 group-hover:text-accent group-hover:opacity-100" />
                  </button>
                );
              })}
            </div>
            <Button
              variant="secondary"
              size="sm"
              className="mt-3"
              onClick={() => navigate('/#intake-desk')}
            >
              选择维权方式
            </Button>
          </div>

          <div className="p-5 sm:p-6">
            <div className="flex items-center gap-2 text-accent">
              <Compass className="h-4 w-4" />
              <h3 className="text-sm font-semibold text-foreground">办事资源</h3>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
              监察、仲裁、12348、欠薪线索等全国与属地官方入口。
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {CAUSE_QUICK_ENTRIES.map((c) => (
                <span
                  key={c.key}
                  className="rounded-full border border-border/70 bg-background px-3 py-1 text-xs font-medium text-muted-foreground"
                >
                  {c.label}
                </span>
              ))}
            </div>
            <button
              type="button"
              onClick={() => navigate('/guidance')}
              className="mt-4 inline-flex cursor-pointer items-center gap-1 text-xs font-medium text-accent hover:underline"
            >
              查看办事资源
              <ArrowUpRight className="h-3 w-3" />
            </button>
          </div>
        </div>
      </Surface>
    </section>
  );
}
