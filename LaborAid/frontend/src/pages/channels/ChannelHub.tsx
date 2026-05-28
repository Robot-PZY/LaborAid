import { Link } from 'react-router-dom';
import { ArrowUpRight, HeartHandshake } from 'lucide-react';
import { listChannels, getChannelsHubIntro, getChannelsDisclaimer } from '@/lib/channels';
import { PageHeader, Surface, Badge } from '@/components/ui/primitives';
import ServiceStrip from '@/components/service/ServiceStrip';

const CHANNEL_ICONS: Record<string, string> = {
  'migrant-worker': '农',
  'intern-probation': '习',
  'female-worker': '职',
};

const CHANNEL_ACCENT: Record<string, string> = {
  'migrant-worker': 'border-l-amber-500',
  'intern-probation': 'border-l-sky-500',
  'female-worker': 'border-l-rose-500',
};

export default function ChannelHub() {
  const channels = listChannels();

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="社会关怀"
        title="维权专区"
        description={getChannelsHubIntro()}
      />

      <div className="flex items-start gap-3 rounded-[var(--radius-md)] border border-accent/25 bg-accent/5 px-4 py-3 text-sm">
        <HeartHandshake className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
        <p className="text-muted-foreground">
          针对不同用工群体提供专属路径与官方渠道，体现劳动者友好与公益导向，便于快速找到「找谁、怎么办」。
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {channels.map((ch) => (
          <Link key={ch.id} to={`/channels/${ch.id}`} className="group block">
            <Surface
              hover
              padding="lg"
              className={`h-full border-l-4 ${CHANNEL_ACCENT[ch.id] || 'border-l-accent'}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-[var(--radius-md)] bg-ink font-display text-lg font-semibold text-white">
                  {CHANNEL_ICONS[ch.id] || '维'}
                </div>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
              </div>
              <h2 className="mt-4 font-display text-lg font-semibold">{ch.title}</h2>
              <p className="mt-1 text-sm text-accent">{ch.subtitle}</p>
              <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">{ch.audience}</p>
              <p className="mt-4 text-xs text-muted-foreground">
                {ch.scenarios?.length ?? 0} 种常见情形 · 分步指引
              </p>
              <ul className="mt-3 space-y-1">
                {ch.highlights.slice(0, 2).map((h) => (
                  <li key={h} className="text-xs text-muted-foreground">
                    · {h}
                  </li>
                ))}
              </ul>
              {ch.enable_one_click_report && (
                <Badge tone="accent" className="mt-4">
                  支持一键举报
                </Badge>
              )}
            </Surface>
          </Link>
        ))}
      </div>

      <p className="text-[11px] leading-relaxed text-muted-foreground">{getChannelsDisclaimer()}</p>

      <ServiceStrip />
    </div>
  );
}
