import specialChannels from '@/config/labor/special-channels.json';
import officialPlatforms from '@/config/labor/official-platforms.json';

export type ChannelQuickAction = {
  id: string;
  title: string;
  description: string;
  action: 'internal' | 'external' | 'phone' | 'report';
  route?: string;
  url?: string;
  phones?: string[];
};

export type ScenarioActionType =
  | 'internal'
  | 'external'
  | 'report'
  | 'phone'
  | 'docgen'
  | 'search';

export type ChannelScenarioStep = {
  title: string;
  detail: string;
  action: ScenarioActionType;
  route?: string;
  url?: string;
  phones?: string[];
  doc_type?: string;
  prefill?: string;
  search_query?: string;
  link_label?: string;
  /** action 为 report 时可指定打开的办事类型 */
  platform_category?: PlatformCategoryId;
};

export type ChannelScenario = {
  id: string;
  title: string;
  summary: string;
  path_hint?: string;
  who_to_sue?: string;
  evidence_checklist?: string[];
  steps: ChannelScenarioStep[];
  law_searches?: string[];
};

export type ChannelStep = {
  title: string;
  detail: string;
  action: 'internal' | 'external' | 'report';
  route?: string;
  url?: string;
};

export type ChannelConfig = {
  id: string;
  title: string;
  subtitle: string;
  audience: string;
  highlights: string[];
  scenarios?: ChannelScenario[];
  rights_summary: string[];
  quick_actions: ChannelQuickAction[];
  steps: ChannelStep[];
  laws: { title: string; url?: string; search_query?: string }[];
  enable_one_click_report?: boolean;
  report_button_label?: string;
};

export type ReportLinkEntry = {
  label: string;
  url: string;
  phone?: string;
  hint?: string;
};

export type PlatformCategoryId =
  | 'wage_clue'
  | 'labor_inspection'
  | 'arbitration'
  | 'legal_aid'
  | 'women_federation'
  | 'union_hotline';

export type PlatformLink = ReportLinkEntry;

export type ProvincePlatformSet = {
  labor_inspection?: PlatformLink;
  arbitration?: PlatformLink;
  legal_aid?: PlatformLink;
  hrss_portal?: PlatformLink;
};

export type PlatformCategoryMeta = {
  id: PlatformCategoryId;
  label: string;
  description: string;
};

const platformsData = officialPlatforms as {
  categories: PlatformCategoryMeta[];
  national: Record<string, PlatformLink>;
  by_province: Record<string, ProvincePlatformSet>;
  province_order?: string[];
  fallback: Record<Exclude<PlatformCategoryId, 'wage_clue' | 'women_federation' | 'union_hotline'>, PlatformLink>;
};

export function listPlatformCategories(): PlatformCategoryMeta[] {
  return platformsData.categories;
}

/** 31 个省级行政区，按国家标准顺序 */
export function listOfficialPlatformProvinces(): string[] {
  const configured = Object.keys(platformsData.by_province || {});
  const order = platformsData.province_order || [];
  const sorted = order.filter((p) => configured.includes(p));
  const rest = configured.filter((p) => !order.includes(p)).sort();
  return [...sorted, ...rest];
}

export function hasProvincePlatformData(province: string): boolean {
  return Boolean(province && platformsData.by_province[province]);
}

export function getNationalPlatform(key: string): PlatformLink | undefined {
  return platformsData.national[key];
}

export function listNationalPlatforms(): { key: string; link: PlatformLink }[] {
  return Object.entries(platformsData.national).map(([key, link]) => ({ key, link }));
}

export function getProvincePlatform(
  province: string,
  category: Exclude<PlatformCategoryId, 'wage_clue' | 'women_federation' | 'union_hotline'>,
): PlatformLink {
  const set = platformsData.by_province[province];
  if (!set) {
    return platformsData.fallback[category];
  }
  if (set[category]) {
    return set[category]!;
  }
  if (category === 'labor_inspection' && set.hrss_portal) {
    return {
      ...set.hrss_portal,
      hint: set.hrss_portal.hint || `进入${province}人社厅官网，搜索「劳动保障监察」`,
    };
  }
  return platformsData.fallback[category];
}

export function getProvincePlatformSet(province: string): ProvincePlatformSet | undefined {
  return platformsData.by_province[province];
}

const NATIONAL_PLATFORM_IDS: PlatformCategoryId[] = [
  'wage_clue',
  'women_federation',
  'union_hotline',
];

export function isNationalPlatformCategory(category: PlatformCategoryId): boolean {
  return NATIONAL_PLATFORM_IDS.includes(category);
}

type ProvincialCategory = Exclude<PlatformCategoryId, 'wage_clue' | 'women_federation' | 'union_hotline'>;

export function resolvePlatformLink(
  category: PlatformCategoryId,
  province?: string,
): PlatformLink & { province?: string; usedFallback?: boolean } {
  if (isNationalPlatformCategory(category)) {
    return (
      platformsData.national[category] || {
        label: category,
        url: 'https://www.12348.gov.cn/',
      }
    );
  }
  const provincial = category as ProvincialCategory;
  if (province && hasProvincePlatformData(province)) {
    const link = getProvincePlatform(province, provincial);
    return { ...link, province };
  }
  if (province) {
    return { ...platformsData.fallback[provincial], province, usedFallback: true };
  }
  return platformsData.fallback[provincial];
}

/** 维权指引 global_links 中的 platform_key → 可点击链接 */
export function resolveGuidanceGlobalLink(link: {
  url?: string;
  platform_key?: string;
}): PlatformLink | null {
  if (link.url) {
    return { label: '', url: link.url };
  }
  if (link.platform_key && platformsData.national[link.platform_key]) {
    return platformsData.national[link.platform_key];
  }
  return null;
}

const data = specialChannels as {
  disclaimer: string;
  hub_intro: string;
  report_links: {
    default: ReportLinkEntry;
    by_province: Record<string, ReportLinkEntry>;
  };
  channels: Record<string, ChannelConfig>;
};

export function getChannelsHubIntro() {
  return data.hub_intro;
}

export function getChannelsDisclaimer() {
  return data.disclaimer;
}

export function listChannels(): ChannelConfig[] {
  return Object.values(data.channels);
}

export function getChannel(id: string): ChannelConfig | undefined {
  return data.channels[id];
}

export function getReportProvinces(): string[] {
  const fromPlatforms = listOfficialPlatformProvinces();
  if (fromPlatforms.length > 0) return fromPlatforms;
  return Object.keys(data.report_links.by_province || {});
}

export function getChannelScenario(
  channelId: string,
  scenarioId: string,
): ChannelScenario | undefined {
  return getChannel(channelId)?.scenarios?.find((s) => s.id === scenarioId);
}

export function getReportLink(province: string): ReportLinkEntry {
  if (province && platformsData.by_province[province]?.labor_inspection) {
    return platformsData.by_province[province].labor_inspection!;
  }
  return data.report_links.by_province?.[province] || data.report_links.default;
}
