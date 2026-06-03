import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowUpRight,
  Archive,
  BookOpen,
  Briefcase,
  Compass,
  FileText,
  HeartHandshake,
  Scale,
  ShieldCheck,
  Upload,
} from 'lucide-react';
import CaseJourneyPanel from '@/components/cases/CaseJourneyPanel';
import DashboardHeroBanner from '@/components/dashboard/DashboardHeroBanner';
import ServiceStrip from '@/components/service/ServiceStrip';
import { caseApi, userPortalApi, type CaseReadinessSummary } from '@/lib/api';
import { getActiveCaseId, subscribeActiveCase } from '@/lib/active-case';
import {
  getAgentsByIds,
  getHubAgents,
  getRecentAgentIds,
  recordAgentVisit,
  type AgentConfig,
} from '@/config/agents';
import CalculatorToolRow from '@/components/dashboard/CalculatorToolRow';
import GuidanceHubPanel from '@/components/guidance/GuidanceHubPanel';
import { formatBytes } from '@/lib/format';
import IntakeDesk from '@/components/intake/IntakeDesk';
import PageSkeleton from '@/components/ui/PageSkeleton';
import { Button, SectionTitle, Surface } from '@/components/ui/primitives';
import { CHART_COLORS, MiniBarCompare } from '@/components/charts/SimpleCharts';
import { cn } from '@/lib/utils';

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

const FLOW_STEPS = [
  {
    title: '判断维权路径',
    description: '输入案情后明确可走渠道，避免直接进入错误流程。',
    cta: '开始维权诊断',
    route: '/guidance',
    icon: Compass,
  },
  {
    title: '整理证据链',
    description: '上传聊天记录、工资流水、合同文本，系统自动提取关键信息。',
    cta: '去整理证据',
    route: '/evidence',
    icon: Upload,
  },
  {
    title: '形成行动文书',
    description: '根据已有材料生成仲裁申请、投诉书等可直接修改提交的文书。',
    cta: '去生成文书',
    route: '/documents',
    icon: FileText,
  },
  {
    title: '生成总结报告',
    description: '结合案件档案、证据与文书，输出可直接复盘与提交的案情总结报告。',
    cta: '去分析案情',
    route: '/research',
    icon: BookOpen,
  },
] as const;

const PRIMARY_TOOL_IDS = ['cases', 'research', 'docgen', 'evidence', 'contract'] as const;
const MORE_TOOL_IDS = ['search', 'enterprise'] as const;

const SHOWCASE_CARDS = [
  {
    title: '证据时间线',
    description: '证据按时间排序，自动补足时间、金额、主体等关键字段，便于提交与答辩。',
    route: '/evidence',
    icon: Upload,
  },
  {
    title: '文书质量感',
    description: '统一结构、术语和版式，输出更接近真实办案文书而非普通聊天回复。',
    route: '/documents',
    icon: Scale,
  },
  {
    title: '官方渠道闭环',
    description: '站内完成整理，站外直达 12348、人社与法规库，形成可执行闭环。',
    route: '/guidance',
    icon: HeartHandshake,
  },
] as const;

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
  const [activeFlowStep, setActiveFlowStep] = useState(0);
  const [activeCaseReadiness, setActiveCaseReadiness] = useState<CaseReadinessSummary | null>(null);
  const [readinessLoading, setReadinessLoading] = useState(false);

  const hubAgents = useMemo(() => getHubAgents(), []);
  const recentAgents = useMemo(() => {
    const ids = getRecentAgentIds();
    return ids.map((id) => hubAgents.find((a) => a.id === id)).filter(Boolean) as AgentConfig[];
  }, [hubAgents]);

  const primaryTools = useMemo(() => getAgentsByIds(PRIMARY_TOOL_IDS), []);
  const moreTools = useMemo(() => getAgentsByIds(MORE_TOOL_IDS), []);

  useEffect(() => {
    try {
      const userStr = localStorage.getItem('user');
      if (userStr) setUserName(JSON.parse(userStr).name || '');
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadReadiness = async () => {
      const activeCaseId = getActiveCaseId();
      if (!activeCaseId) {
        setActiveCaseReadiness(null);
        return;
      }
      setReadinessLoading(true);
      try {
        const readiness = await caseApi.getReadiness(activeCaseId);
        if (!cancelled) setActiveCaseReadiness(readiness);
      } catch {
        if (!cancelled) setActiveCaseReadiness(null);
      } finally {
        if (!cancelled) setReadinessLoading(false);
      }
    };

    void loadReadiness();
    const unsub = subscribeActiveCase(() => {
      void loadReadiness();
    });
    return () => {
      cancelled = true;
      unsub();
    };
  }, []);

  useEffect(() => {
    async function load() {
      setError('');
      try {
        const overview = await userPortalApi.getOverview();
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
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    const timer = window.setInterval(() => {
      setActiveFlowStep((prev) => (prev + 1) % FLOW_STEPS.length);
    }, 2600);
    return () => window.clearInterval(timer);
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
      <DashboardHeroBanner greeting={greeting} />

      <section>
        <SectionTitle
          title="维权流程"
          description="按需进入对应模块，完成从路径到报告的全流程。"
        />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {FLOW_STEPS.map((step, idx) => {
            const Icon = step.icon;
            const isActive = idx === activeFlowStep;
            return (
              <Surface
                key={step.title}
                padding="md"
                hover
                className={`relative overflow-hidden transition-all ${isActive ? 'ring-2 ring-accent/35' : ''}`}
              >
                <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-accent/10 blur-2xl" />
                <div className="mb-3 h-1.5 rounded-full bg-muted/80">
                  <div
                    className={`h-full rounded-full bg-accent transition-all duration-500 ${
                      isActive ? 'w-full' : 'w-0'
                    }`}
                  />
                </div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                  STEP 0{idx + 1}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <Icon className="h-4 w-4 text-accent" />
                  <h3 className="font-display text-lg font-semibold">{step.title}</h3>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
                <button
                  type="button"
                  onClick={() => navigate(step.route)}
                  className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
                >
                  {step.cta}
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </button>
              </Surface>
            );
          })}
        </div>
      </section>

      <IntakeDesk />

      {error && (
        <div className="flex items-center gap-2 rounded-[var(--radius-md)] border border-amber-200/80 bg-amber-50/80 px-4 py-3 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/40 dark:text-amber-100">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      <section className="grid gap-4 lg:grid-cols-[1fr_auto]">
        <CaseJourneyPanel />
        <div className="min-w-[260px] space-y-4">
          <div className="rounded-xl border border-border/70 bg-card p-5 shadow-card">
            <h2 className="text-sm font-semibold">当前案件 AI 完整度</h2>
            {readinessLoading ? (
              <p className="mt-2 text-xs text-muted-foreground">正在计算…</p>
            ) : !activeCaseReadiness ? (
              <p className="mt-2 text-xs text-muted-foreground">
                请选择一个案件作为当前案件，即可显示智能评估。
              </p>
            ) : (
              <>
                <div className="mt-3 h-2.5 rounded-full bg-muted">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all duration-300',
                      activeCaseReadiness.readiness_level === 'high'
                        ? 'bg-emerald-500'
                        : activeCaseReadiness.readiness_level === 'medium'
                          ? 'bg-amber-500'
                          : 'bg-rose-500',
                    )}
                    style={{ width: `${Math.max(0, Math.min(100, activeCaseReadiness.readiness_score))}%` }}
                  />
                </div>
                <p className="mt-2 text-xs font-medium">
                  完整度 {activeCaseReadiness.readiness_score}% · {activeCaseReadiness.summary}
                </p>
                {activeCaseReadiness.next_actions.length > 0 && (
                  <button
                    type="button"
                    onClick={() => navigate(activeCaseReadiness.next_actions[0].route)}
                    className="mt-3 inline-flex w-full items-center justify-center rounded-md border px-3 py-2 text-xs font-medium transition-colors hover:bg-accent"
                  >
                    {activeCaseReadiness.next_actions[0].label}
                  </button>
                )}
              </>
            )}
          </div>
          <div className="rounded-xl border border-border/70 bg-card p-5 shadow-card">
          <h2 className="text-sm font-semibold">材料与产出概况</h2>
          <p className="mt-1 text-xs text-muted-foreground">当前账号维权资产一览</p>
          <div className="mt-3">
            <MiniBarCompare items={activityBars} />
          </div>
          <button
            type="button"
            onClick={() => navigate('/vault')}
            className="mt-4 inline-flex w-full items-center justify-between rounded-lg border border-accent/35 bg-accent/10 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:bg-accent/20"
          >
            <span>材料库 {stats.vault_files} 份</span>
            <span className="text-muted-foreground">{formatBytes(stats.vault_bytes)}</span>
          </button>
        </div>
        </div>
      </section>

      <section>
        <SectionTitle title="工作台概览" description="关键数据入口，快速进入对应模块处理。" />
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
      </section>

      <section>
        <SectionTitle
          title="核心展示能力"
          description="不仅能用，更能把维权过程讲清楚、交付清楚。"
        />
        <div className="grid gap-4 md:grid-cols-3">
          {SHOWCASE_CARDS.map((card) => {
            const Icon = card.icon;
            return (
              <Surface key={card.title} padding="md" hover>
                <div className="inline-flex rounded-lg bg-accent/12 p-2 text-accent">
                  <Icon className="h-4 w-4" />
                </div>
                <h3 className="mt-3 font-display text-lg font-semibold">{card.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{card.description}</p>
                <button
                  type="button"
                  onClick={() => navigate(card.route)}
                  className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
                >
                  进入查看
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </button>
              </Surface>
            );
          })}
        </div>
      </section>

      <GuidanceHubPanel />

      <section className="grid gap-6 lg:grid-cols-2">
        <div>
          <SectionTitle title="常用工具" description="案件与分析优先，再处理文书与证据。" />
          <Surface padding="sm" className="divide-y divide-border/60">
            {primaryTools.map((agent) => (
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
          <SectionTitle title="更多工具" description="法规检索、计算器与企业查询等辅助工具。" />
          <Surface padding="sm" className="divide-y divide-border/60">
            {moreTools.map((agent) => (
              <ToolRow key={agent.id} agent={agent} onClick={() => handleTool(agent)} />
            ))}
            <CalculatorToolRow
              onOpen={(route) => {
                const id = route.includes('compensation') ? 'compensation_calc' : 'limitation_calc';
                recordAgentVisit(id);
                navigate(route);
              }}
            />
          </Surface>
        </div>
      </section>

      <ServiceStrip />

      <p className="border-t border-border/60 pt-6 text-[11px] leading-relaxed text-muted-foreground">
        AI 生成内容仅供参考，不构成法律意见。办事要求、时效与材料以当地仲裁委、人社部门及司法机关最新公布为准。
      </p>
    </div>
  );
}

export default React.memo(Dashboard);
