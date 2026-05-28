import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Briefcase,
  CheckCircle2,
  ChevronDown,
  FileText,
  BookOpen,
  Loader2,
  Plus,
  RefreshCw,
  Upload,
  X,
} from 'lucide-react';
import { caseApi, documentApi, evidenceApi, researchApi } from '@/lib/api';
import type { Case, CaseCreate } from '@/lib/api';
import {
  getActiveCaseId,
  setActiveCaseId,
  subscribeActiveCase,
} from '@/lib/active-case';
import { withCaseTitleDatePrefix } from '@/lib/case-title';
import { loadIntakeSession } from '@/lib/intake-session';
import { CHART_COLORS, ProgressRing } from '@/components/charts/SimpleCharts';
import { Button } from '@/components/ui/primitives';

const JOURNEY_STEPS = [
  {
    key: 'case' as const,
    title: '选定案件',
    hint: '先创建或选择要维权的案件',
    route: '/cases',
    icon: Briefcase,
  },
  {
    key: 'evidence' as const,
    title: '整理证据',
    hint: '上传工资条、合同等材料',
    route: '/evidence',
    icon: Upload,
  },
  {
    key: 'documents' as const,
    title: '生成文书',
    hint: '仲裁申请、投诉书等',
    route: '/documents',
    icon: FileText,
  },
  {
    key: 'analysis' as const,
    title: '分析案情',
    hint: '汇总材料；结论达“可仲裁/可起诉”才算完成',
    route: '/research',
    icon: BookOpen,
  },
];

const statusLabel: Record<string, string> = {
  draft: '草稿',
  active: '进行中',
  closed: '已结案',
  archived: '已归档',
};

type CaseStats = {
  evidence: number;
  documents: number;
  reports: number;
  actionableReports: number;
  latestConclusion: string | null;
};

const ACTIONABLE_CONCLUSION_LEVELS = new Set([
  '可以准备劳动仲裁或监察投诉',
  '可以准备法院起诉',
]);

export default function CaseJourneyPanel() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<Case[]>([]);
  const [activeId, setActiveId] = useState<number | null>(() => getActiveCaseId());
  const [stats, setStats] = useState<CaseStats>({
    evidence: 0,
    documents: 0,
    reports: 0,
    actionableReports: 0,
    latestConclusion: null,
  });
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingStats, setLoadingStats] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [createForm, setCreateForm] = useState<CaseCreate>({
    title: '',
    case_type: 'administrative_labor',
    description: '',
  });

  const loadCases = useCallback(async () => {
    setLoadingCases(true);
    try {
      const list = await caseApi.list({ limit: 100 });
      setCases(list);

      let preferred = getActiveCaseId();
      const session = loadIntakeSession();
      if (!preferred && session?.createdCaseId) {
        preferred = session.createdCaseId;
      }
      if (preferred && list.some((c) => c.id === preferred)) {
        setActiveId(preferred);
        setActiveCaseId(preferred);
      } else if (!preferred && list.length === 1) {
        setActiveId(list[0].id);
        setActiveCaseId(list[0].id);
      } else if (preferred && !list.some((c) => c.id === preferred)) {
        setActiveId(null);
        setActiveCaseId(null);
      }
    } catch {
      setCases([]);
    } finally {
      setLoadingCases(false);
    }
  }, []);

  useEffect(() => {
    loadCases();
    return subscribeActiveCase(() => setActiveId(getActiveCaseId()));
  }, [loadCases]);

  useEffect(() => {
    if (!activeId) {
      setStats({
        evidence: 0,
        documents: 0,
        reports: 0,
        actionableReports: 0,
        latestConclusion: null,
      });
      return;
    }
    let cancelled = false;
    setLoadingStats(true);
    Promise.all([
      evidenceApi.list(activeId).catch(() => []),
      documentApi.list({ case_id: activeId, limit: 200 }).catch(() => []),
      researchApi.list({ case_id: activeId, limit: 20 }).catch(() => []),
    ])
      .then(([ev, docs, reports]) => {
        if (cancelled) return;
        setStats({
          evidence: ev.filter((e) => e.has_file).length,
          documents: docs.length,
          reports: reports.length,
          actionableReports: reports.filter((r) =>
            r.conclusion_level ? ACTIONABLE_CONCLUSION_LEVELS.has(r.conclusion_level) : false,
          ).length,
          latestConclusion: reports[0]?.conclusion_level || null,
        });
      })
      .finally(() => {
        if (!cancelled) setLoadingStats(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeId]);

  const activeCase = useMemo(
    () => cases.find((c) => c.id === activeId) ?? null,
    [cases, activeId],
  );

  const handleSelectCase = (id: number) => {
    setActiveId(id);
    setActiveCaseId(id);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.title.trim()) {
      setCreateError('请填写案件标题');
      return;
    }
    setCreating(true);
    setCreateError('');
    try {
      const created = await caseApi.create({
        ...createForm,
        title: withCaseTitleDatePrefix(createForm.title),
      });
      setShowCreate(false);
      setCreateForm({ title: '', case_type: 'administrative_labor', description: '' });
      await loadCases();
      handleSelectCase(created.id);
    } catch {
      setCreateError('创建失败，请重试');
    } finally {
      setCreating(false);
    }
  };

  const journeyScore = useMemo(() => {
    if (!activeCase) return 0;
    let done = 0;
    if (activeCase) done += 1;
    if (stats.evidence > 0) done += 1;
    if (stats.documents > 0) done += 1;
    if (stats.actionableReports > 0) done += 1;
    return done;
  }, [activeCase, stats]);

  const stepDone = (key: (typeof JOURNEY_STEPS)[number]['key']) => {
    if (key === 'case') return !!activeCase;
    if (key === 'evidence') return stats.evidence > 0;
    if (key === 'documents') return stats.documents > 0;
    if (key === 'analysis') return stats.actionableReports > 0;
    return false;
  };

  const goStep = (step: (typeof JOURNEY_STEPS)[number]) => {
    if (step.key === 'case') {
      navigate(activeCase ? `/cases?open=${activeCase.id}` : '/cases?worker=1');
      return;
    }
    if (!activeCase) {
      setShowCreate(true);
      return;
    }
    const q = `caseId=${activeCase.id}&worker=1`;
    navigate(`${step.route}?${q}`);
  };

  return (
    <div className="rounded-xl border border-border/70 bg-card p-5 shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-base font-semibold">我的维权足迹</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            先选定案件，再按步骤整理证据与文书
          </p>
        </div>
        <ProgressRing
          value={journeyScore}
          max={4}
          label="本案进度"
          color={CHART_COLORS.documents}
        />
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-2">
        <div className="min-w-[200px] flex-1">
          <label className="mb-1 block text-[11px] font-medium text-muted-foreground">
            当前案件
          </label>
          {loadingCases ? (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              加载案件…
            </p>
          ) : (
            <div className="relative">
              <select
                className="w-full appearance-none rounded-lg border border-border bg-background py-2 pl-3 pr-9 text-sm"
                value={activeId ?? ''}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v) handleSelectCase(Number(v));
                  else {
                    setActiveId(null);
                    setActiveCaseId(null);
                  }
                }}
              >
                <option value="">请选择案件…</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                    {statusLabel[c.status] ? `（${statusLabel[c.status]}）` : ''}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            </div>
          )}
        </div>

        <Button
          type="button"
          variant="secondary"
          className="shrink-0"
          onClick={() => setShowCreate((v) => !v)}
        >
          <Plus className="h-4 w-4" />
          新建案件
        </Button>
        <button
          type="button"
          onClick={() => loadCases()}
          className="inline-flex h-9 items-center gap-1 rounded-lg border border-border px-2.5 text-xs text-muted-foreground hover:bg-muted"
          title="刷新案件列表"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>

      {activeCase && (
        <p className="mt-2 text-xs text-muted-foreground">
          正在跟进：
          <span className="font-medium text-foreground">{activeCase.title}</span>
          {loadingStats ? (
            <span className="ml-2">统计加载中…</span>
          ) : (
            <span className="ml-2 tabular-nums">
              证据 {stats.evidence} 条 · 文书 {stats.documents} 份 · 分析
              {stats.actionableReports > 0 ? '已达标' : '待完善'}
            </span>
          )}
        </p>
      )}

      {!activeCase && !loadingCases && (
        <p className="mt-3 rounded-lg border border-dashed border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs text-amber-900 dark:text-amber-100">
          请先选择已有案件，或点击「新建案件」开始维权流程。
        </p>
      )}

      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="mt-3 space-y-3 rounded-lg border border-border/70 bg-muted/20 p-3"
        >
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">新建维权案件</p>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="rounded p-1 text-muted-foreground hover:bg-muted"
              aria-label="关闭"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <input
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            placeholder="案件标题，如：某某公司欠薪维权"
            value={createForm.title}
            onChange={(e) => setCreateForm((f) => ({ ...f, title: e.target.value }))}
            required
          />
          <textarea
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            placeholder="案情摘要（可选）"
            rows={2}
            value={createForm.description || ''}
            onChange={(e) => setCreateForm((f) => ({ ...f, description: e.target.value }))}
          />
          {createError && <p className="text-xs text-destructive">{createError}</p>}
          <div className="flex gap-2">
            <Button type="submit" disabled={creating}>
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : '创建并选中'}
            </Button>
            <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>
              取消
            </Button>
          </div>
        </form>
      )}

      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {JOURNEY_STEPS.map((step, i) => {
          const done = stepDone(step.key);
          const Icon = step.icon;
          const count =
            step.key === 'evidence'
              ? stats.evidence
              : step.key === 'documents'
                ? stats.documents
                : step.key === 'analysis'
                  ? stats.reports
                  : activeCase
                    ? 1
                    : 0;
          return (
            <button
              key={step.key}
              type="button"
              onClick={() => goStep(step)}
              className={`rounded-lg border p-3 text-left transition-all hover:shadow-sm ${
                done
                  ? 'border-emerald-500/30 bg-emerald-500/5'
                  : 'border-border/70 bg-muted/20'
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                    done ? 'bg-emerald-500 text-white' : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : i + 1}
                </span>
                <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-sm font-medium">{step.title}</span>
              </div>
              <p className="mt-1 pl-8 text-[11px] text-muted-foreground">{step.hint}</p>
              {activeCase && step.key !== 'case' && (
                <p className="mt-1 pl-8 text-xs tabular-nums text-muted-foreground">
                  {step.key === 'analysis'
                    ? `本案 ${stats.reports} 份报告${stats.latestConclusion ? ` · 最新结论：${stats.latestConclusion}` : ''}`
                    : `本案 ${count} 条`}
                </p>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
