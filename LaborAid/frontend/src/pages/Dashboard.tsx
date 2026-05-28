import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowUpRight,
  AlertCircle,
  Compass,
  History,
  ExternalLink,
  Briefcase,
  FileText,
  Upload,
  BookOpen,
  ShieldCheck,
  HeartHandshake,
  Archive,
  Sparkles,
} from 'lucide-react';
import CaseJourneyPanel from '@/components/cases/CaseJourneyPanel';
import { listChannels, resolveGuidanceGlobalLink } from '@/lib/channels';
import { BRAND } from '@/config/brand';
import { guidanceApi, userPortalApi, type GlobalLink } from '@/lib/api';
import {
  getHubAgents,
  getRecentAgentIds,
  recordAgentVisit,
  type AgentConfig,
} from '@/config/agents';
import guidanceFallback from '@/config/labor/guidance.json';
import { formatBytes } from '@/lib/format';
import IntakeDesk from '@/components/intake/IntakeDesk';
import PageSkeleton from '@/components/ui/PageSkeleton';
import { Button, Surface, SectionTitle, Badge } from '@/components/ui/primitives';
import { CHART_COLORS, MiniBarCompare } from '@/components/charts/SimpleCharts';

const STAT_META = {
  cases: {
    label: '案件',
    route: '/cases',
    icon: Briefcase,
    ring: CHART_COLORS.cases,
    chip: 'bg-blue-500/10 text-blue-800 dark:text-blue-200',
  },
  documents: {
    label: '文书',
    route: '/documents',
    icon: FileText,
    ring: CHART_COLORS.documents,
    chip: 'bg-amber-500/10 text-amber-900 dark:text-amber-200',
  },
  evidence: {
    label: '证据',
    route: '/evidence',
    icon: Upload,
    ring: CHART_COLORS.evidence,
    chip: 'bg-emerald-500/10 text-emerald-800 dark:text-emerald-200',
  },
  research: {
    label: '案情分析',
    route: '/research',
    icon: BookOpen,
    ring: CHART_COLORS.research,
    chip: 'bg-violet-500/10 text-violet-800 dark:text-violet-200',
  },
  contracts: {
    label: '合同',
    route: '/contracts',
    icon: ShieldCheck,
    ring: 'hsl(199 70% 45%)',
    chip: 'bg-sky-500/10 text-sky-900 dark:text-sky-200',
  },
} as const;

const CHANNEL_ACCENTS: Record<string, { border: string; bg: string; emoji: string }> = {
  'migrant-worker': {
    border: 'border-l-amber-500',
    bg: 'from-amber-500/8 to-card',
    emoji: '🏗️',
  },
  'intern-probation': {
    border: 'border-l-sky-500',
    bg: 'from-sky-500/8 to-card',
    emoji: '🎓',
  },
  'female-worker': {
    border: 'border-l-rose-500',
    bg: 'from-rose-500/8 to-card',
    emoji: '💪',
  },
};

function ToolRow({ agent, onClick }: { agent: AgentConfig; onClick: () => void }) {
  const Icon = agent.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full items-center gap-4 rounded-[var(--radius-md)] border border-transparent px-3 py-3 text-left transition-all hover:border-border hover:bg-muted/40 hover:shadow-sm"
    >
      <div
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-border/60 bg-gradient-to-br from-card to-muted/30 shadow-sm ${agent.color}`}
      >
        <Icon className="h-[20px] w-[20px]" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-medium text-foreground">{agent.name}</p>
        <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{agent.description}</p>
      </div>
      <ArrowUpRight className="h-4 w-4 shrink-0 text-accent opacity-0 transition-all group-hover:translate-x-0.5 group-hover:opacity-100" />
    </button>
  );
}

function Dashboard() {
  const navigate = useNavigate();
  const [userName, setUserName] = useState('');
  const [links, setLinks] = useState<GlobalLink[]>([]);
  const [stats, setStats] = useState({
    cases: 0,
    documents: 0,
    evidence: 0,
    research: 0,
    contracts: 0,
    vault_files: 0,
    vault_bytes: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const hubAgents = useMemo(() => getHubAgents(), []);
  const recentAgents = useMemo(() => {
    const ids = getRecentAgentIds();
    return ids.map((id) => hubAgents.find((a) => a.id === id)).filter(Boolean) as AgentConfig[];
  }, [hubAgents]);

  const featuredTools = useMemo(
    () => hubAgents.filter((a) => ['docgen', 'evidence', 'search', 'contract'].includes(a.id)),
    [hubAgents],
  );

  useEffect(() => {
    try {
      const userStr = localStorage.getItem('user');
      if (userStr) setUserName(JSON.parse(userStr).name || '');
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    async function load() {
      setError('');
      try {
        const [guidance, overview] = await Promise.all([
          guidanceApi.get().catch(() => guidanceFallback as { global_links: GlobalLink[] }),
          userPortalApi.getOverview(),
        ]);
        setLinks(guidance.global_links?.slice(0, 4) || []);
        setStats({
          cases: overview.cases,
          documents: overview.documents,
          evidence: overview.evidence,
          research: overview.research,
          contracts: overview.contracts ?? 0,
          vault_files: overview.vault_files ?? 0,
          vault_bytes: overview.vault_bytes ?? 0,
        });
      } catch {
        setError('部分数据加载失败');
        const fb = guidanceFallback as { global_links: GlobalLink[] };
        setLinks(fb.global_links?.slice(0, 4) || []);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleTool = (agent: AgentConfig) => {
    recordAgentVisit(agent.id);
    navigate(agent.route);
  };

  const statEntries = [
    { key: 'cases' as const },
    { key: 'documents' as const },
    { key: 'evidence' as const },
    { key: 'research' as const },
    { key: 'contracts' as const },
  ];

  const totalRecords =
    stats.cases + stats.documents + stats.evidence + stats.research + stats.contracts;

  const activityBars = useMemo(
    () =>
      statEntries.map(({ key }) => ({
        label: STAT_META[key].label,
        value: stats[key],
        color: STAT_META[key].ring,
      })),
    [stats],
  );

  if (loading) {
    return <PageSkeleton />;
  }

  const greeting = userName ? `${userName}，您好` : '劳动者维权工作台';

  return (
    <div className="space-y-10">
      <Surface
        padding="lg"
        className="relative overflow-hidden border-ink/10 bg-gradient-to-br from-accent/12 via-card to-blue-500/5"
      >
        <div className="pointer-events-none absolute -right-12 -top-12 h-44 w-44 rounded-full bg-accent/20 blur-3xl dashboard-blob" />
        <div className="pointer-events-none absolute bottom-0 left-0 h-32 w-32 rounded-full bg-blue-400/15 blur-2xl dashboard-blob-delayed" />
        <div className="relative z-10">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="accent">{BRAND.name}</Badge>
            <span className="inline-flex items-center gap-1 rounded-full border border-accent/25 bg-background/70 px-2 py-0.5 text-[11px] text-muted-foreground backdrop-blur-sm">
              <Sparkles className="h-3 w-3 text-accent" />
              一步步把维权材料理清楚
            </span>
          </div>
          <h1 className="mt-4 font-display text-2xl font-semibold tracking-tight sm:text-[1.85rem]">
            {greeting}
          </h1>
          <p className="mt-2 max-w-lg text-sm leading-relaxed text-muted-foreground">
            先理清维权路径与官方渠道，再整理证据与文书——每一步都有指引，不必一个人硬扛。
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => navigate('/guidance')}>
              <Compass className="h-4 w-4" />
              维权指引
            </Button>
            <Button variant="outline" onClick={() => navigate('/records')}>
              <History className="h-4 w-4" />
              我的记录
              {totalRecords > 0 && (
                <span className="ml-1 rounded-full bg-accent/15 px-1.5 text-[10px] font-semibold text-accent">
                  {totalRecords}
                </span>
              )}
            </Button>
            <Button variant="outline" onClick={() => navigate('/channels')}>
              <HeartHandshake className="h-4 w-4" />
              维权专区
            </Button>
            <Button variant="outline" onClick={() => navigate('/vault')}>
              <Archive className="h-4 w-4" />
              材料库
            </Button>
          </div>
        </div>
      </Surface>

      <IntakeDesk />

      {error && (
        <div className="flex items-center gap-2 rounded-[var(--radius-md)] border border-amber-200/80 bg-amber-50/80 px-4 py-3 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/40 dark:text-amber-100">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      <section className="grid gap-4 lg:grid-cols-[1fr_auto]">
        <CaseJourneyPanel />
        <div className="min-w-[200px] rounded-xl border border-border/70 bg-card p-5 shadow-card">
          <h2 className="text-sm font-semibold">材料概况</h2>
          <div className="mt-3">
            <MiniBarCompare items={activityBars} />
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {statEntries.map(({ key }) => {
          const meta = STAT_META[key];
          const Icon = meta.icon;
          return (
            <button
              key={key}
              type="button"
              onClick={() => navigate(meta.route)}
              className="group rounded-[var(--radius-md)] border border-border/70 bg-card p-4 text-left shadow-card transition-all hover:-translate-y-0.5 hover:border-accent/25 hover:shadow-card-hover"
            >
              <div className={`mb-2 inline-flex rounded-lg p-2 ${meta.chip}`}>
                <Icon className="h-4 w-4" strokeWidth={1.75} />
              </div>
              <p className="font-display text-2xl font-semibold tabular-nums transition-colors group-hover:text-accent">
                {stats[key]}
              </p>
              <p className="text-[11px] text-muted-foreground">{meta.label}</p>
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => navigate('/vault')}
          className="group rounded-[var(--radius-md)] border border-accent/35 bg-gradient-to-br from-accent/15 to-card p-4 text-left shadow-card transition-all hover:-translate-y-0.5 hover:shadow-card-hover"
        >
          <div className="mb-2 inline-flex rounded-lg bg-accent/20 p-2 text-accent">
            <Archive className="h-4 w-4" strokeWidth={1.75} />
          </div>
          <p className="font-display text-2xl font-semibold tabular-nums">{stats.vault_files}</p>
          <p className="text-[11px] text-muted-foreground">
            材料库 · {formatBytes(stats.vault_bytes)}
          </p>
        </button>
      </div>

      <section>
        <SectionTitle
          title="维权专区"
          description="农民工、实习生、女职工等群体的专属维权路径与办事指引"
        />
        <div className="grid gap-3 sm:grid-cols-3">
          {listChannels().map((ch) => {
            const accent = CHANNEL_ACCENTS[ch.id] || {
              border: 'border-l-accent',
              bg: 'from-accent/8 to-card',
              emoji: '✨',
            };
            return (
              <button
                key={ch.id}
                type="button"
                onClick={() => navigate(`/channels/${ch.id}`)}
                className={`rounded-[var(--radius-md)] border border-border/70 border-l-4 bg-gradient-to-br ${accent.bg} p-4 text-left shadow-card transition-all hover:-translate-y-0.5 hover:shadow-card-hover ${accent.border}`}
              >
                <span className="text-xl" aria-hidden>
                  {accent.emoji}
                </span>
                <p className="mt-2 font-display font-semibold">{ch.title}</p>
                <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{ch.subtitle}</p>
                {ch.enable_one_click_report && (
                  <Badge tone="accent" className="mt-2">
                    一键举报
                  </Badge>
                )}
              </button>
            );
          })}
        </div>
      </section>

      <section>
        <SectionTitle
          title="专业法律服务"
          description="法律援助、人社服务、法律法规等官方入口"
        />
        <div className="grid gap-2 sm:grid-cols-2">
          {links.map((link, i) => {
            const resolved = resolveGuidanceGlobalLink(link);
            const href = resolved?.url || link.url;
            if (!href) return null;
            const hues = [
              'bg-blue-500/10 text-blue-800',
              'bg-amber-500/10 text-amber-900',
              'bg-emerald-500/10 text-emerald-800',
              'bg-violet-500/10 text-violet-800',
            ];
            return (
              <a
                key={link.id}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-start gap-4 rounded-[var(--radius-md)] border border-border/70 bg-card p-4 shadow-card transition-all hover:border-accent/30 hover:shadow-card-hover"
              >
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl font-display text-sm font-semibold ${hues[i % hues.length]}`}
                >
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-foreground">{link.title}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                    {link.description}
                  </p>
                </div>
                <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-accent opacity-50 transition-opacity group-hover:opacity-100" />
              </a>
            );
          })}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div>
          <SectionTitle title="常用工具" />
          <Surface padding="sm" className="divide-y divide-border/60">
            {featuredTools.map((agent) => (
              <ToolRow key={agent.id} agent={agent} onClick={() => handleTool(agent)} />
            ))}
          </Surface>
          {recentAgents.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              <span className="self-center text-[11px] text-muted-foreground">最近使用</span>
              {recentAgents.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => handleTool(a)}
                  className="rounded-full border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-accent/40 hover:text-foreground"
                >
                  {a.name}
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <SectionTitle title="更多工具" />
          <Surface padding="sm" className="divide-y divide-border/60">
            {hubAgents
              .filter((a) => !featuredTools.some((f) => f.id === a.id))
              .map((agent) => (
                <ToolRow key={agent.id} agent={agent} onClick={() => handleTool(agent)} />
              ))}
          </Surface>
        </div>
      </section>

      <p className="border-t border-border/60 pt-6 text-[11px] leading-relaxed text-muted-foreground">
        AI 生成内容仅供参考，不构成法律意见。办事要求、时效与材料以当地仲裁委、人社部门及司法机关最新公布为准。
      </p>
    </div>
  );
}

export default React.memo(Dashboard);
