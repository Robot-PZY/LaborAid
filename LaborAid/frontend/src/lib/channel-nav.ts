import type { ChannelScenarioStep, PlatformCategoryId } from '@/lib/channels';

type NavigateFn = (path: string) => void;

type RunStepContext = {
  channelId: string;
  scenarioId: string;
  navigate: NavigateFn;
  openReport: () => void;
  openPlatform?: (category: PlatformCategoryId) => void;
};

export function buildDocgenLink(
  channelId: string,
  scenarioId: string,
  docType: string,
  prefill?: string,
): string {
  const params = new URLSearchParams({
    worker: '1',
    type: docType,
    channel: channelId,
    scenario: scenarioId,
  });
  if (prefill?.trim()) params.set('prefill', prefill.trim());
  return `/documents?${params.toString()}`;
}

export function buildSearchLink(query: string): string {
  return `/search?q=${encodeURIComponent(query)}`;
}

export function runScenarioStep(step: ChannelScenarioStep, ctx: RunStepContext): void {
  switch (step.action) {
    case 'report':
      if (step.platform_category && ctx.openPlatform) {
        ctx.openPlatform(step.platform_category);
      } else {
        ctx.openReport();
      }
      return;
    case 'phone':
      if (step.phones?.[0]) window.location.href = `tel:${step.phones[0]}`;
      return;
    case 'docgen':
      if (step.doc_type) {
        ctx.navigate(buildDocgenLink(ctx.channelId, ctx.scenarioId, step.doc_type, step.prefill));
      }
      return;
    case 'search':
      if (step.search_query) ctx.navigate(buildSearchLink(step.search_query));
      return;
    case 'internal':
      if (step.route) ctx.navigate(step.route);
      return;
    case 'external':
      if (step.url) window.open(step.url, '_blank', 'noopener,noreferrer');
      return;
    default:
      return;
  }
}

export function scenarioStepLabel(step: ChannelScenarioStep): string {
  if (step.link_label) return step.link_label;
  switch (step.action) {
    case 'docgen':
      return '生成文书';
    case 'search':
      return '检索法规';
    case 'report':
      return '一键举报';
    case 'phone':
      return step.phones?.join(' / ') || '拨打电话';
    case 'internal':
      return '使用本站工具';
    case 'external':
      return '前往官方渠道';
    default:
      return '继续';
  }
}
