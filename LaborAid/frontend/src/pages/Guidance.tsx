import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ExternalLink, ArrowUpRight, AlertCircle } from 'lucide-react';
import GuidanceHubPanel from '@/components/guidance/GuidanceHubPanel';
import { guidanceApi, type CauseGuidance, type GlobalLink, type GuidanceStep } from '@/lib/api/guidance';
import guidanceFallback from '@/config/labor/guidance.json';
import { AGENTS } from '@/config/agents';
import { PageHeader, Surface, SectionTitle } from '@/components/ui/primitives';
import ServiceStrip from '@/components/service/ServiceStrip';
import PageSkeleton from '@/components/ui/PageSkeleton';
import ReportDialog from '@/components/channels/ReportDialog';
import OfficialPlatformStrip from '@/components/channels/OfficialPlatformStrip';
import {
  resolveGuidanceGlobalLink,
  type PlatformCategoryId,
} from '@/lib/channels';

const CAUSE_LABELS: Record<string, string> = {
  wage_arrears: '拖欠工资',
  illegal_termination: '违法解除',
  overtime_pay: '加班费争议',
  no_written_contract: '未签书面合同',
};

const DOC_TYPE_BY_CAUSE: Record<string, string> = {
  wage_arrears: 'application',
  illegal_termination: 'application',
  overtime_pay: 'application',
  no_written_contract: 'application',
};

function resolveToolRoute(step: GuidanceStep, causeKey: string): string {
  if (step.tool_id === 'docgen') {
    const type = DOC_TYPE_BY_CAUSE[causeKey] || 'application';
    return `/documents?worker=1&type=${type}&from=guidance&cause=${causeKey}`;
  }
  if (step.tool_id) {
    const agent = AGENTS.find((a) => a.id === step.tool_id);
    if (agent) return agent.route;
  }
  return '/evidence';
}

export default function Guidance() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const causeParam = searchParams.get('cause');
  const [links, setLinks] = useState<GlobalLink[]>([]);
  const [causes, setCauses] = useState<Record<string, CauseGuidance>>({});
  const [disclaimer, setDisclaimer] = useState('');
  const [selected, setSelected] = useState(causeParam || 'wage_arrears');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [platformOpen, setPlatformOpen] = useState(false);
  const [platformCategory, setPlatformCategory] = useState<PlatformCategoryId>('labor_inspection');

  const openPlatform = (category: PlatformCategoryId) => {
    setPlatformCategory(category);
    setPlatformOpen(true);
  };

  useEffect(() => {
    if (causeParam && causeParam !== selected) setSelected(causeParam);
  }, [causeParam]);

  useEffect(() => {
    guidanceApi
      .get()
      .then((data) => {
        setLinks(data.global_links || []);
        setCauses(data.cause_guidance || {});
        setDisclaimer(data.disclaimer || '');
        const keys = Object.keys(data.cause_guidance || {});
        if (keys.length && !keys.includes(selected)) setSelected(keys[0]);
      })
      .catch(() => {
        const fb = guidanceFallback as {
          global_links: GlobalLink[];
          cause_guidance: Record<string, CauseGuidance>;
          disclaimer: string;
        };
        setLinks(fb.global_links || []);
        setCauses(fb.cause_guidance || {});
        setDisclaimer(fb.disclaimer || '');
        setError('已加载本地指引');
      })
      .finally(() => setLoading(false));
  }, []);

  const current = causes[selected];
  const causeKeys = Object.keys(causes);

  if (loading) {
    return <PageSkeleton />;
  }

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="维权服务"
        title="维权指引"
        description="按案由查看建议步骤；需要人工帮助时可跳转官方法律服务渠道"
      />

      {error && (
        <div className="flex items-center gap-2 text-sm text-amber-800 dark:text-amber-200">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      <GuidanceHubPanel mode="channels-only" showSectionTitle />

      <section>
        <SectionTitle title="常用全国入口" description="欠薪线索、12348、人社政务平台等" />
        <div className="grid gap-2 sm:grid-cols-2">
          {links.map((link) => {
            const resolved = resolveGuidanceGlobalLink(link);
            const href = resolved?.url || link.url;
            const onClick =
              link.platform_key === 'wage_clue'
                ? () => openPlatform('wage_clue')
                : undefined;

            if (onClick) {
              return (
                <button
                  key={link.id}
                  type="button"
                  onClick={onClick}
                  className="group flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-border/70 bg-card px-4 py-3.5 text-left shadow-card transition-all hover:shadow-card-hover"
                >
                  <div>
                    <p className="text-sm font-medium">{link.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{link.description}</p>
                  </div>
                  <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground group-hover:text-foreground" />
                </button>
              );
            }

            return (
              <a
                key={link.id}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center justify-between gap-3 rounded-[var(--radius-md)] border border-border/70 bg-card px-4 py-3.5 shadow-card transition-all hover:shadow-card-hover"
              >
                <div>
                  <p className="text-sm font-medium">{link.title}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{link.description}</p>
                </div>
                <ExternalLink className="h-4 w-4 shrink-0 text-muted-foreground group-hover:text-foreground" />
              </a>
            );
          })}
        </div>
      </section>

      <OfficialPlatformStrip onOpenPlatform={openPlatform} />

      <section>
        <SectionTitle title="按案由查看" description="选择与您情况最接近的类型" />
        <div className="flex flex-wrap gap-1.5">
          {causeKeys.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setSelected(key)}
              className={`rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
                selected === key
                  ? 'border-ink bg-ink text-white'
                  : 'border-border bg-card text-muted-foreground hover:border-foreground/20 hover:text-foreground'
              }`}
            >
              {CAUSE_LABELS[key] || key}
            </button>
          ))}
        </div>

        {current && (
          <Surface className="mt-4" padding="lg">
            <p className="text-sm leading-relaxed text-muted-foreground">{current.summary}</p>
            <ol className="mt-6 space-y-0 divide-y divide-border/60">
              {current.steps.map((step, idx) => (
                <li key={idx} className="flex gap-4 py-4 first:pt-0 last:pb-0">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border font-display text-sm font-semibold text-foreground">
                    {idx + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{step.title}</p>
                    {step.when && (
                      <p className="mt-0.5 text-xs text-muted-foreground">适用：{step.when}</p>
                    )}
                    {step.hint && (
                      <p className="mt-1.5 text-sm text-muted-foreground">{step.hint}</p>
                    )}
                    {step.note && (
                      <p className="mt-1 text-xs text-amber-800/90">{step.note}</p>
                    )}
                    <div className="mt-2">
                      {step.action === 'platform' && step.platform_category ? (
                        <button
                          type="button"
                          onClick={() => openPlatform(step.platform_category!)}
                          className="inline-flex items-center gap-1 text-sm font-medium text-accent underline-offset-4 hover:underline"
                        >
                          打开官方办事入口
                          <ExternalLink className="h-3.5 w-3.5" />
                        </button>
                      ) : step.action === 'external' && step.url ? (
                        <a
                          href={step.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-sm font-medium text-accent underline-offset-4 hover:underline"
                        >
                          前往官方渠道
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            const route = resolveToolRoute(step, selected);
                            navigate(route.includes('?') ? route : `${route}?from=guidance&worker=1&cause=${selected}`);
                          }}
                          className="inline-flex items-center gap-1 text-sm font-medium text-foreground underline-offset-4 hover:underline"
                        >
                          使用本站工具
                          <ArrowUpRight className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </Surface>
        )}
      </section>

      {disclaimer && (
        <p className="text-[11px] leading-relaxed text-muted-foreground">{disclaimer}</p>
      )}

      <ServiceStrip />

      <ReportDialog
        open={platformOpen}
        onClose={() => setPlatformOpen(false)}
        buttonLabel="官方办事入口"
        initialCategory={platformCategory}
      />
    </div>
  );
}
