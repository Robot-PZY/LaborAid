import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ChevronDown,
  Loader2,
  Plus,
  RefreshCw,
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
import CaseAgentCoach from '@/components/cases/CaseAgentCoach';
import CaseWorkflowStepper from '@/components/cases/CaseWorkflowStepper';
import { useCaseAgentStep } from '@/hooks/useCaseAgentStep';
import { useCaseWorkflow } from '@/hooks/useCaseWorkflow';

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

  const {
    step: agentStep,
    loading: agentLoading,
    error: agentError,
    refresh: refreshAgent,
  } = useCaseAgentStep(activeId);

  const {
    workflow,
    loading: workflowLoading,
    error: workflowError,
    refresh: refreshWorkflow,
  } = useCaseWorkflow(activeId);

  const refreshAll = () => {
    refreshAgent();
    refreshWorkflow();
  };

  const journeyScore = workflow?.progress ?? 0;
  const journeyMax = workflow?.total_steps ?? 4;

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
          max={journeyMax}
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

      {activeId && (
        <div className="mt-4 space-y-4">
          <CaseWorkflowStepper
            workflow={workflow}
            loading={workflowLoading}
            error={workflowError}
          />
          <CaseAgentCoach
            step={agentStep}
            caseId={activeId}
            loading={agentLoading}
            error={agentError}
            onRefresh={refreshAll}
          />
        </div>
      )}

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
    </div>
  );
}
