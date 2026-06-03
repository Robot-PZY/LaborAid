import { useNavigate } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { PageHeader } from '@/components/ui/primitives';
import { CHANNEL_THEME } from '@/components/guidance/GuidanceHubPanel';
import { listChannels, getChannelsDisclaimer, getChannelsHubIntro } from '@/lib/channels';
import OfficialEntryHint from '@/components/channels/OfficialEntryHint';
import ServiceStrip from '@/components/service/ServiceStrip';
import { cn } from '@/lib/utils';

function ChannelCard({ channel }: { channel: ReturnType<typeof listChannels>[number] }) {
  const navigate = useNavigate();
  const theme = CHANNEL_THEME[channel.id] ?? {
    border: 'border-l-accent',
    chip: 'bg-accent/10 text-accent',
    dot: 'bg-accent',
  };
  const scenarioCount = channel.scenarios?.length ?? 0;

  return (
    <button
      type="button"
      onClick={() => navigate(`/channels/${channel.id}`)}
      className={cn(
        'group w-full cursor-pointer rounded-[var(--radius-md)] border border-border/70 border-l-[3px] bg-card p-5 text-left shadow-card transition-all hover:border-accent/40 hover:shadow-card-hover',
        theme.border,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium">{channel.title}</p>
          <p className="mt-1 text-sm text-muted-foreground">{channel.subtitle}</p>
        </div>
        <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground opacity-40 group-hover:text-accent group-hover:opacity-100" />
      </div>
      <p className="mt-3 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{channel.audience}</p>
      {channel.highlights.length > 0 && (
        <ul className="mt-3 space-y-1">
          {channel.highlights.slice(0, 3).map((item) => (
            <li key={item} className="flex gap-2 text-xs text-muted-foreground">
              <span className={cn('mt-1.5 h-1 w-1 shrink-0 rounded-full', theme.dot)} />
              {item}
            </li>
          ))}
        </ul>
      )}
      <p className="mt-4 text-xs font-medium text-accent/90">
        {scenarioCount > 0 ? `${scenarioCount} 种常见情形` : '查看详情'}
        {channel.enable_one_click_report ? ' · 支持一键举报' : ''}
      </p>
    </button>
  );
}

export default function ChannelHub() {
  const channels = listChannels();
  const hubIntro = getChannelsHubIntro();

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="维权服务"
        title="专项维权"
        description={hubIntro || '按用工人群进入分情形步骤、证据清单与站内工具。'}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        {channels.map((ch) => (
          <ChannelCard key={ch.id} channel={ch} />
        ))}
      </div>

      <OfficialEntryHint />

      <p className="text-[11px] leading-relaxed text-muted-foreground">{getChannelsDisclaimer()}</p>

      <ServiceStrip />
    </div>
  );
}
