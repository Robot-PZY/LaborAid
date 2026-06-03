import { PageHeader } from '@/components/ui/primitives';
import { ChannelRow } from '@/components/guidance/GuidanceHubPanel';
import { listChannels, getChannelsDisclaimer } from '@/lib/channels';
import ServiceStrip from '@/components/service/ServiceStrip';

export default function ChannelHub() {
  const channels = listChannels();

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="维权指引"
        title="专项维权"
        description="按用工人群进入专属路径：分情形步骤、证据清单与官方办事入口。"
      />

      <div className="space-y-2">
        {channels.map((ch) => (
          <ChannelRow key={ch.id} channel={ch} />
        ))}
      </div>

      <p className="text-[11px] leading-relaxed text-muted-foreground">{getChannelsDisclaimer()}</p>

      <ServiceStrip />
    </div>
  );
}
