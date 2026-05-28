import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight, ChevronRight, ShieldAlert } from 'lucide-react';
import {
  getChannel,
  getChannelScenario,
  getChannelsDisclaimer,
} from '@/lib/channels';
import { buildSearchLink } from '@/lib/channel-nav';
import ReportDialog from '@/components/channels/ReportDialog';
import OfficialPlatformStrip from '@/components/channels/OfficialPlatformStrip';
import ChannelScenarioPanel from '@/components/channels/ChannelScenarioPanel';
import { Button, Surface, SectionTitle, Badge } from '@/components/ui/primitives';
import type { PlatformCategoryId } from '@/lib/channels';
import ServiceStrip from '@/components/service/ServiceStrip';

export default function ChannelDetail() {
  const { channelId } = useParams<{ channelId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [reportOpen, setReportOpen] = useState(false);
  const [platformCategory, setPlatformCategory] = useState<PlatformCategoryId>('labor_inspection');

  const openPlatform = (category: PlatformCategoryId) => {
    setPlatformCategory(category);
    setReportOpen(true);
  };

  const channel = channelId ? getChannel(channelId) : undefined;
  const scenarioParam = searchParams.get('scenario');
  const selectedScenario =
    channel && scenarioParam ? getChannelScenario(channel.id, scenarioParam) : undefined;

  useEffect(() => {
    if (scenarioParam && channel && !selectedScenario) {
      setSearchParams({}, { replace: true });
    }
  }, [scenarioParam, channel, selectedScenario, setSearchParams]);

  if (!channel) {
    return (
      <div className="text-center py-16">
        <p className="text-muted-foreground">未找到该专区</p>
        <Link to="/channels" className="mt-4 inline-block text-sm font-medium hover:underline">
          返回维权专区
        </Link>
      </div>
    );
  }

  const scenarios = channel.scenarios ?? [];

  const openScenario = (id: string) => {
    setSearchParams({ scenario: id }, { replace: true });
  };

  const closeScenario = () => {
    setSearchParams({}, { replace: true });
  };

  return (
    <div className="space-y-10">
      <Link
        to="/channels"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        维权专区
      </Link>

      <div>
        <Badge tone="accent">专项通道</Badge>
        <h1 className="mt-3 font-display text-2xl font-semibold sm:text-3xl">{channel.title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{channel.subtitle}</p>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">{channel.audience}</p>
      </div>

      {channel.enable_one_click_report && !selectedScenario && (
        <Surface className="flex flex-col gap-4 border-accent/30 bg-accent/5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 shrink-0 text-accent" />
            <div>
              <p className="font-medium">需要投诉用人单位？</p>
              <p className="text-sm text-muted-foreground">选择属地后跳转劳动监察 / 人社官方渠道</p>
            </div>
          </div>
          <Button variant="secondary" onClick={() => openPlatform('labor_inspection')}>
            {channel.report_button_label || '一键举报'}
          </Button>
        </Surface>
      )}

      {selectedScenario ? (
        <ChannelScenarioPanel
          channel={channel}
          scenario={selectedScenario}
          onBack={closeScenario}
          openReport={() => openPlatform('labor_inspection')}
          openPlatform={openPlatform}
        />
      ) : (
        <>
          <section>
            <SectionTitle
              title="选择你的情形"
              description={`共 ${scenarios.length} 种常见情形，按步骤完成维权准备`}
            />
            {scenarios.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {scenarios.map((scenario) => (
                  <button
                    key={scenario.id}
                    type="button"
                    onClick={() => openScenario(scenario.id)}
                    className="group rounded-[var(--radius-md)] border border-border/70 bg-card p-5 text-left shadow-card transition-all hover:border-accent/40 hover:shadow-card-hover"
                  >
                    <p className="font-medium">{scenario.title}</p>
                    <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{scenario.summary}</p>
                    {scenario.path_hint && (
                      <p className="mt-3 text-xs text-accent/90 line-clamp-1">{scenario.path_hint}</p>
                    )}
                    <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-foreground">
                      查看分步指引
                      <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">该专区场景配置更新中，请稍后再试。</p>
            )}
          </section>

          <section>
            <SectionTitle title="权利义务速览" />
            <ul className="space-y-2">
              {channel.rights_summary.map((r) => (
                <li key={r} className="flex gap-2 text-sm text-muted-foreground">
                  <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent" />
                  {r}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}

      {channel.laws.length > 0 && (
        <section>
          <SectionTitle title="相关法条" />
          <div className="flex flex-wrap gap-2">
            {channel.laws.map((law) => (
              <button
                key={law.title}
                type="button"
                onClick={() => {
                  if (law.search_query) navigate(buildSearchLink(law.search_query));
                  else if (law.url) window.open(law.url, '_blank', 'noopener,noreferrer');
                }}
                className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-xs hover:bg-muted/50"
              >
                {law.title}
                <ArrowUpRight className="h-3 w-3" />
              </button>
            ))}
          </div>
        </section>
      )}

      <OfficialPlatformStrip
        onOpenPlatform={openPlatform}
        emphasizeWomenResources={channel.id === 'female-worker'}
      />

      <p className="text-[11px] text-muted-foreground">{getChannelsDisclaimer()}</p>

      <ServiceStrip />

      <ReportDialog
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        buttonLabel={channel.report_button_label}
        initialCategory={platformCategory}
      />
    </div>
  );
}
