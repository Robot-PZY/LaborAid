import { useNavigate } from 'react-router-dom';
import { ArrowUpRight, Compass, HeartHandshake } from 'lucide-react';
import { listChannels, type ChannelConfig } from '@/lib/channels';
import { CAUSE_QUICK_ENTRIES } from '@/lib/guidance-labels';
import { Button, SectionTitle, Surface } from '@/components/ui/primitives';
import { cn } from '@/lib/utils';

const CHANNEL_THEME: Record<
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

export function ChannelRow({ channel }: { channel: ChannelConfig }) {
  const navigate = useNavigate();
  const theme = CHANNEL_THEME[channel.id] ?? {
    border: 'border-l-accent',
    chip: 'bg-accent/10 text-accent',
    dot: 'bg-accent',
  };

  return (
    <button
      type="button"
      onClick={() => navigate(`/channels/${channel.id}`)}
      className={cn(
        'group flex w-full cursor-pointer items-center gap-3 rounded-[var(--radius-md)] border border-border/60 border-l-[3px] bg-card/80 px-3 py-2.5 text-left transition-all hover:border-accent/30 hover:bg-muted/30',
        theme.border,
      )}
    >
      <span className={cn('h-2 w-2 shrink-0 rounded-full', theme.dot)} aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground">{channel.title}</p>
        <p className="line-clamp-1 text-xs text-muted-foreground">{channel.subtitle}</p>
      </div>
      {channel.enable_one_click_report && (
        <span className={cn('hidden shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-medium sm:inline', theme.chip)}>
          可举报
        </span>
      )}
      <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-40 group-hover:text-accent group-hover:opacity-100" />
    </button>
  );
}

type GuidanceHubPanelProps = {
  /** 首页完整双栏；指引页仅展示专项；专区页由 ChannelHub 自行排版 */
  mode?: 'full' | 'channels-only';
  showSectionTitle?: boolean;
  className?: string;
};

/**
 * 维权指引 + 专项专区 — 统一入口面板，避免首页/指引页/专区页三套样式。
 */
export default function GuidanceHubPanel({
  mode = 'full',
  showSectionTitle = true,
  className,
}: GuidanceHubPanelProps) {
  const navigate = useNavigate();
  const channels = listChannels();

  if (mode === 'channels-only') {
    return (
      <section className={className}>
        {showSectionTitle && (
          <SectionTitle
            title="专项维权"
            description="按人群查看分情形指引、证据清单与官方办事入口。"
          />
        )}
        <Surface padding="sm" className="space-y-2">
          {channels.map((ch) => (
            <ChannelRow key={ch.id} channel={ch} />
          ))}
        </Surface>
      </section>
    );
  }

  return (
    <section className={className}>
      {showSectionTitle && (
        <SectionTitle
          title="维权指引"
          description="按案由查步骤；按人群进专项通道。官方办事链接在指引页内集中展示。"
        />
      )}

      <Surface padding="none" className="overflow-hidden">
        <div className="grid divide-y divide-border/60 lg:grid-cols-2 lg:divide-x lg:divide-y-0">
        <div className="p-5 sm:p-6">
          <div className="flex items-center gap-2 text-accent">
            <Compass className="h-4 w-4" />
            <h3 className="text-sm font-semibold text-foreground">按案由</h3>
          </div>
          <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
            选择最接近的情形，查看分步建议与对应本站工具。
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {CAUSE_QUICK_ENTRIES.map((c) => (
              <button
                key={c.key}
                type="button"
                onClick={() => navigate(`/guidance?cause=${c.key}`)}
                className="cursor-pointer rounded-full border border-border/70 bg-background px-3 py-1 text-xs font-medium text-foreground transition-colors hover:border-foreground/25 hover:bg-muted/50"
              >
                {c.label}
              </button>
            ))}
          </div>
          <Button variant="secondary" size="sm" className="mt-4" onClick={() => navigate('/guidance')}>
            进入维权指引
          </Button>
        </div>

        <div className="p-5 sm:p-6">
          <div className="flex items-center gap-2 text-accent">
            <HeartHandshake className="h-4 w-4" />
            <h3 className="text-sm font-semibold text-foreground">专项维权</h3>
          </div>
          <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
            农民工、实习生、女职工等群体的分情形指引与官方渠道。
          </p>
          <div className="mt-3 space-y-2">
            {channels.map((ch) => (
              <ChannelRow key={ch.id} channel={ch} />
            ))}
          </div>
          <button
            type="button"
            onClick={() => navigate('/channels')}
            className="mt-3 inline-flex cursor-pointer items-center gap-1 text-xs font-medium text-accent hover:underline"
          >
            查看专区说明
            <ArrowUpRight className="h-3 w-3" />
          </button>
        </div>
        </div>
      </Surface>
    </section>
  );
}
