import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Users,
  Briefcase,
  FileText,
  Upload,
  BookOpen,
  Cpu,
  Eye,
  Link2,
  ArrowRight,
  TrendingUp,
  Activity,
  AlertTriangle,
} from 'lucide-react';
import { adminApi, type AdminStatsOverview, type UsageTrendDay } from '@/lib/api/admin';
import { SectionTitle } from '@/components/ui/primitives';
import {
  CHART_COLORS,
  DonutChart,
  MiniBarCompare,
  Sparkline,
  StackedBarChart,
  type TrendRow,
} from '@/components/charts/SimpleCharts';

const STAT_STYLES = [
  { ring: 'bg-blue-500/10 text-blue-700 dark:text-blue-300', bar: CHART_COLORS.cases },
  { ring: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300', bar: CHART_COLORS.evidence },
  { ring: 'bg-amber-500/10 text-amber-800 dark:text-amber-300', bar: CHART_COLORS.documents },
  { ring: 'bg-violet-500/10 text-violet-700 dark:text-violet-300', bar: CHART_COLORS.research },
] as const;

function StatCard({
  label,
  value,
  icon: Icon,
  sub,
  sparkValues,
  accentClass,
  sparkColor,
  to,
}: {
  label: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  sub?: string;
  sparkValues?: number[];
  accentClass?: string;
  sparkColor?: string;
  to?: string;
}) {
  const card = (
    <div
      className={`rounded-xl border border-border/70 bg-card p-4 shadow-card transition-shadow hover:shadow-card-hover ${to ? 'cursor-pointer' : ''}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-1 font-display text-2xl font-semibold tabular-nums">{value}</p>
          {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
        </div>
        <div className={`shrink-0 rounded-xl p-2.5 ${accentClass || 'bg-accent/10 text-accent'}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      {sparkValues && sparkValues.length > 0 && (
        <div className="mt-3 border-t border-border/50 pt-2">
          <Sparkline values={sparkValues} color={sparkColor} width={140} height={36} />
        </div>
      )}
    </div>
  );

  if (to) {
    return <Link to={to} className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl">{card}</Link>;
  }
  return card;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStatsOverview | null>(null);
  const [trend, setTrend] = useState<UsageTrendDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([adminApi.getStats(), adminApi.getUsageTrend(7)])
      .then(([s, t]) => {
        setStats(s);
        setTrend(t);
      })
      .catch(() => setError('加载统计数据失败'))
      .finally(() => setLoading(false));
  }, []);

  const trendRows: TrendRow[] = useMemo(
    () =>
      trend.map((d) => ({
        label: d.date.slice(5),
        cases: d.cases,
        documents: d.documents,
        evidence: d.evidence,
        research: d.research,
      })),
    [trend],
  );

  const dailyTotals = useMemo(
    () => trend.map((d) => d.cases + d.documents + d.evidence + d.research),
    [trend],
  );

  const weekTotal = dailyTotals.reduce((a, b) => a + b, 0);

  const contentSegments = useMemo(() => {
    if (!stats) return [];
    return [
      { label: '案件', value: stats.cases_total, color: CHART_COLORS.cases },
      { label: '文书', value: stats.documents_total, color: CHART_COLORS.documents },
      { label: '证据', value: stats.evidence_total, color: CHART_COLORS.evidence },
      { label: '研究报告', value: stats.research_total, color: CHART_COLORS.research },
    ];
  }, [stats]);

  const materialSegments = useMemo(() => {
    if (!stats) return [];
    const ready = stats.cases_material_ready;
    const inProgress = Math.max(0, stats.cases_with_evidence - ready);
    const empty = Math.max(0, stats.cases_total - stats.cases_with_evidence);
    return [
      { label: '材料达标', value: ready, color: CHART_COLORS.evidence },
      { label: '进行中', value: inProgress, color: CHART_COLORS.documents },
      { label: '待补充', value: empty, color: 'hsl(0 65% 55%)' },
    ].filter((s) => s.value > 0);
  }, [stats]);

  const userSegments = useMemo(() => {
    if (!stats) return [];
    const inactive = Math.max(0, stats.users_total - stats.users_active);
    return [
      { label: '活跃', value: stats.users_active, color: CHART_COLORS.users },
      { label: '未启用', value: inactive, color: CHART_COLORS.inactive },
    ];
  }, [stats]);

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-28 rounded-2xl bg-muted" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 rounded-xl bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return <p className="text-red-600">{error || '无数据'}</p>;
  }

  const contentTotal =
    stats.cases_total + stats.documents_total + stats.evidence_total + stats.research_total;

  const alerts = [
    !stats.llm_configured && {
      message: '文本模型尚未配置，文书生成等功能可能不可用',
      to: '/admin/models',
    },
    !stats.vision_llm_configured && {
      message: '视觉 OCR 模型尚未配置，图片/PDF 识别可能不可用',
      to: '/admin/models',
    },
    weekTotal === 0 && {
      message: '近 7 日暂无新增记录，可检查用户端是否正常接入',
      to: '/admin/users',
    },
  ].filter(Boolean) as { message: string; to: string }[];

  return (
    <div className="space-y-8">
      <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-accent/8 p-6 shadow-card">
        <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-accent/15 blur-3xl dashboard-blob" />
        <div className="pointer-events-none absolute -bottom-16 left-1/4 h-40 w-40 rounded-full bg-blue-500/10 blur-3xl dashboard-blob-delayed" />
        <div className="relative z-10">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent">运营管理</p>
          <h1 className="mt-2 font-display text-2xl font-semibold">数据概览</h1>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">
            客户端使用与平台资源一览（全局统计，不含系统内部账号）
          </p>
          <div className="mt-5 flex flex-wrap gap-4">
            <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-background/60 px-3 py-2 text-sm backdrop-blur-sm">
              <TrendingUp className="h-4 w-4 text-accent" />
              <span>
                近 7 日新增 <strong className="tabular-nums">{weekTotal}</strong> 条记录
              </span>
            </div>
            <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-background/60 px-3 py-2 text-sm backdrop-blur-sm">
              <Activity className="h-4 w-4 text-emerald-600" />
              <span>
                平台内容总量 <strong className="tabular-nums">{contentTotal}</strong>
              </span>
            </div>
          </div>
        </div>
      </div>

      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert) => (
            <Link
              key={alert.message}
              to={alert.to}
              className="flex cursor-pointer items-center gap-3 rounded-lg border border-amber-200/80 bg-amber-50/80 px-4 py-3 text-sm text-amber-950 transition-colors hover:bg-amber-100/60 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100 dark:hover:bg-amber-950/50"
            >
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span className="flex-1">{alert.message}</span>
              <ArrowRight className="h-4 w-4 shrink-0 opacity-60" />
            </Link>
          ))}
        </div>
      )}

      <section>
        <SectionTitle title="用户" description="注册与活跃情况" className="mb-3" />
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard
            label="注册用户"
            value={stats.users_total}
            icon={Users}
            sub={`近7日新增 ${stats.users_new_7d}`}
            accentClass={STAT_STYLES[0].ring}
            to="/admin/users"
          />
          <StatCard
            label="活跃账号"
            value={stats.users_active}
            icon={Users}
            sub={`活跃率 ${stats.users_total ? Math.round((stats.users_active / stats.users_total) * 100) : 0}%`}
            accentClass={STAT_STYLES[0].ring}
            to="/admin/users"
          />
        </div>
      </section>

      <section>
        <SectionTitle title="平台内容" description="案件、文书、证据与研究报告" className="mb-3" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="案件"
            value={stats.cases_total}
            icon={Briefcase}
            sparkValues={trend.map((d) => d.cases)}
            accentClass={STAT_STYLES[0].ring}
            sparkColor={CHART_COLORS.cases}
          />
          <StatCard
            label="文书"
            value={stats.documents_total}
            icon={FileText}
            sparkValues={trend.map((d) => d.documents)}
            accentClass={STAT_STYLES[2].ring}
            sparkColor={CHART_COLORS.documents}
          />
          <StatCard
            label="证据"
            value={stats.evidence_total}
            icon={Upload}
            sparkValues={trend.map((d) => d.evidence)}
            accentClass={STAT_STYLES[1].ring}
            sparkColor={CHART_COLORS.evidence}
          />
          <StatCard
            label="研究报告"
            value={stats.research_total}
            icon={BookOpen}
            sparkValues={trend.map((d) => d.research)}
            accentClass={STAT_STYLES[3].ring}
            sparkColor={CHART_COLORS.research}
          />
        </div>
      </section>

      <section>
        <SectionTitle title="AI 材料与完整度" description="用户端案情、证据 OCR 与报告产出健康度" className="mb-3" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="材料达标案件"
            value={`${stats.material_ready_rate_pct}%`}
            icon={Activity}
            sub={`${stats.cases_material_ready} / ${stats.cases_total} 案（有描述且含证据或文书）`}
            accentClass="bg-violet-500/10 text-violet-700 dark:text-violet-300"
          />
          <StatCard
            label="证据 OCR 覆盖"
            value={`${stats.evidence_ocr_rate_pct}%`}
            icon={Eye}
            sub={`${stats.evidence_with_ocr} / ${stats.evidence_total} 份证据已识别`}
            accentClass="bg-sky-500/10 text-sky-800 dark:text-sky-300"
          />
          <StatCard
            label="近7日案情报告"
            value={stats.research_reports_7d}
            icon={BookOpen}
            sub={`累计研究报告 ${stats.research_total}`}
            accentClass={STAT_STYLES[3].ring}
          />
          <StatCard
            label="已关联证据案件"
            value={stats.cases_with_evidence}
            icon={Upload}
            sub={`${stats.cases_with_description} 案已填写描述`}
            accentClass={STAT_STYLES[1].ring}
          />
        </div>
        {materialSegments.length > 0 && (
          <div className="mt-4 rounded-xl border border-border/70 bg-muted/20 p-5">
            <h3 className="text-sm font-semibold">案件材料完整度分布（估算）</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              达标：有案情描述且含证据或文书 · 进行中：已有证据但未达标 · 待补充：尚无证据
            </p>
            <div className="mt-4 flex flex-col items-center gap-4 sm:flex-row sm:items-start">
              <DonutChart
                segments={materialSegments}
                size={150}
                stroke={18}
                centerLabel={`${stats.material_ready_rate_pct}%`}
                centerSub="达标率"
              />
              <MiniBarCompare
                items={materialSegments.map((s) => ({
                  label: s.label,
                  value: s.value,
                  color: s.color,
                }))}
              />
            </div>
          </div>
        )}
      </section>

      <section>
        <SectionTitle title="系统状态" description="模型与 OCR 配置" className="mb-3" />
        <div className="grid gap-4 sm:grid-cols-2">
          <StatCard
            label="文本模型"
            value={stats.llm_configured ? '已配置' : '未配置'}
            icon={Cpu}
            sub="点击前往模型配置"
            to="/admin/models"
            accentClass={
              stats.llm_configured
                ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                : 'bg-amber-500/10 text-amber-800 dark:text-amber-300'
            }
          />
          <StatCard
            label="视觉 OCR"
            value={stats.vision_llm_configured ? '已配置' : '未配置'}
            icon={Eye}
            sub="点击前往模型配置"
            to="/admin/models"
            accentClass={
              stats.vision_llm_configured
                ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                : 'bg-amber-500/10 text-amber-800 dark:text-amber-300'
            }
          />
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-border/70 bg-card p-6 shadow-card">
          <h2 className="font-display text-lg font-semibold">内容结构分布</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">案件、文书、证据与研究报告占比</p>
          <div className="mt-6">
            <DonutChart
              segments={contentSegments}
              centerLabel={String(contentTotal)}
              centerSub="总条数"
              size={180}
            />
          </div>
        </div>

        <div className="rounded-xl border border-border/70 bg-card p-6 shadow-card">
          <h2 className="font-display text-lg font-semibold">用户活跃结构</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">启用与未启用账号对比</p>
          <div className="mt-6">
            <DonutChart
              segments={userSegments}
              centerLabel={String(stats.users_total)}
              centerSub="注册用户"
              size={180}
            />
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-border/70 bg-card p-6 shadow-card">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-semibold">近 7 日新增趋势</h2>
            <p className="mt-0.5 text-sm text-muted-foreground">按日堆叠：案件 / 文书 / 证据 / 研究</p>
          </div>
          {dailyTotals.length > 0 && (
            <Sparkline values={dailyTotals} color={CHART_COLORS.documents} width={120} height={40} />
          )}
        </div>
        {trendRows.length === 0 ? (
          <p className="mt-6 text-sm text-muted-foreground">暂无趋势数据</p>
        ) : (
          <div className="mt-6 flex justify-center">
            <StackedBarChart rows={trendRows} height={180} />
          </div>
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-border/70 bg-card p-6 shadow-card lg:col-span-1">
          <h2 className="text-sm font-semibold">模块存量对比</h2>
          <div className="mt-4">
            <MiniBarCompare items={contentSegments} />
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:col-span-2">
          {[
            { to: '/admin/models', label: '配置模型', desc: '文本与 OCR 模型', icon: Cpu },
            { to: '/admin/apis', label: '接口管理', desc: '外部法规/案例 API', icon: Link2 },
            { to: '/admin/users', label: '用户管理', desc: '查看与启用账号', icon: Users },
          ].map(({ to, label, desc, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="group flex items-center justify-between rounded-[var(--radius-md)] border border-border/70 bg-card p-4 shadow-card transition-all hover:border-accent/30 hover:shadow-card-hover"
            >
              <div>
                <div className="flex items-center gap-2 font-medium">
                  <Icon className="h-4 w-4 text-accent" />
                  {label}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{desc}</p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
