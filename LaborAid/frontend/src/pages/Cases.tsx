import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Plus, Filter, Briefcase, Search, X, ChevronLeft, ChevronRight,
  ArrowLeft, Calendar, Users, FileText, Loader2, AlertCircle, CheckCircle2, Download, Trash2, } from 'lucide-react';
import CaseReadinessHint from '@/components/cases/CaseReadinessHint';
import CaseAgentCoach from '@/components/cases/CaseAgentCoach';
import CaseWorkflowStepper from '@/components/cases/CaseWorkflowStepper';
import { useCaseAgentStep } from '@/hooks/useCaseAgentStep';
import { useCaseWorkflow } from '@/hooks/useCaseWorkflow';
import EvidenceCoveragePanel from '@/components/cases/EvidenceCoveragePanel';
import { AxiosError } from 'axios';
import { caseApi, documentApi, intakeApi } from '@/lib/api';
import { useToast } from '@/lib/toast';
import { removeToolHistoryForDocument } from '@/lib/tool-history';
import { withCaseTitleDatePrefix } from '@/lib/case-title';
import { clearIntakeCreatedCaseId, loadIntakeSession } from '@/lib/intake-session';
import { clearActiveCaseIfMatches, setActiveCaseId } from '@/lib/active-case';
import { downloadBlob } from '@/lib/api/client';
import type { Case, CaseCreate, CaseReadinessSummary, Document } from '@/lib/api';
import { cn } from '@/lib/utils';

const CASE_TYPES = [
  { value: '', label: '全部类型' },
  { value: 'civil', label: '民事' },
  { value: 'criminal', label: '刑事' },
  { value: 'administrative', label: '行政' },
  { value: 'labor', label: '劳动' },
  { value: 'contract', label: '合同' },
  { value: 'ip', label: '知识产权' },
  { value: 'other', label: '其他' },
];

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'draft', label: '草稿' },
  { value: 'active', label: '进行中' },
  { value: 'closed', label: '已结案' },
  { value: 'archived', label: '已归档' },
];

const STATUS_TRANSITIONS: Record<string, { value: string; label: string }[]> = {
  draft: [{ value: 'active', label: '开始处理' }],
  active: [
    { value: 'closed', label: '结案' },
    { value: 'archived', label: '归档' },
  ],
  closed: [{ value: 'archived', label: '归档' }],
  archived: [{ value: 'active', label: '重新激活' }],
};

const statusLabel: Record<string, string> = {
  draft: '草稿',
  active: '进行中',
  closed: '已结案',
  archived: '已归档',
};

const caseTypeLabel: Record<string, string> = {
  civil: '民事',
  criminal: '刑事',
  administrative: '行政',
  labor: '劳动',
  administrative_labor: '劳动仲裁',
  contract: '合同',
  ip: '知识产权',
  other: '其他',
};

const statusColor: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  active: 'bg-blue-100 text-blue-700',
  closed: 'bg-green-100 text-green-700',
  archived: 'bg-yellow-100 text-yellow-700',
};

const PAGE_SIZE = 12;

const WORKER_CASE_TYPES = [
  { value: 'administrative_labor', label: '劳动仲裁 / 劳动争议' },
];

function Cases() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [searchParams] = useSearchParams();
  const workerMode = searchParams.get('worker') === '1' || searchParams.get('from') === 'intake';
  const [cases, setCases] = useState<Case[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Pagination
  const [page, setPage] = useState(1);

  // Case detail view
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);
  const [caseDocs, setCaseDocs] = useState<Document[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [deletingDocId, setDeletingDocId] = useState<number | null>(null);
  const [readiness, setReadiness] = useState<CaseReadinessSummary | null>(null);
  const [readinessLoading, setReadinessLoading] = useState(false);
  const {
    step: agentStep,
    loading: agentLoading,
    error: agentError,
    refresh: refreshAgent,
  } = useCaseAgentStep(selectedCase?.id ?? null);

  const {
    workflow,
    loading: workflowLoading,
    error: workflowError,
    refresh: refreshWorkflow,
  } = useCaseWorkflow(selectedCase?.id ?? null);

  const refreshCaseAi = () => {
    refreshAgent();
    refreshWorkflow();
  };

  // Create dialog state
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<CaseCreate>({
    title: '',
    case_type: 'administrative_labor',
    description: '',
  });
  const [exportingPack, setExportingPack] = useState(false);
  const [creating, setCreating] = useState(false);

  // Status update state
  const [updatingStatus, setUpdatingStatus] = useState<number | null>(null);

  useEffect(() => {
    const session = loadIntakeSession();
    if (!session || !workerMode) return;
    setCreateForm({
      title: session.recommendedTools.find((t) => t.agent_id === 'cases')?.prefill.title
        || `${session.causeLabel}维权`,
      case_type: 'administrative_labor',
      description: session.caseFacts || session.summary,
      plaintiff: session.parties.plaintiff || undefined,
      defendant: session.parties.defendant || undefined,
    });
    if (searchParams.get('from') === 'intake') setShowCreate(true);
  }, [workerMode, searchParams]);

  // Debounce search input
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleSearchInput = useCallback((value: string) => {
    setSearchQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(value);
    }, 300);
  }, []);

  const fetchCases = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const skip = (page - 1) * PAGE_SIZE;
      const data = await caseApi.list({
        status: statusFilter || undefined,
        case_type: typeFilter || undefined,
        skip,
        limit: PAGE_SIZE,
      });
      setCases(data);
      // If we got a full page, estimate there may be more
      setTotalCount(data.length < PAGE_SIZE ? skip + data.length : skip + PAGE_SIZE + 1);
    } catch {
      setError('获取案件列表失败，请重试');
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, typeFilter]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [statusFilter, typeFilter, debouncedSearch]);

  // Client-side filter the current page by search query
  const filteredCases = useMemo(() => {
    if (!debouncedSearch.trim()) return cases;
    const q = debouncedSearch.toLowerCase();
    return cases.filter((c) =>
      c.title.toLowerCase().includes(q) ||
      (c.description && c.description.toLowerCase().includes(q)) ||
      (c.case_number && c.case_number.toLowerCase().includes(q)),
    );
  }, [cases, debouncedSearch]);

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);

  const openCaseDetail = useCallback(async (c: Case) => {
    setActiveCaseId(c.id);
    setSelectedCase(c);
    setDetailLoading(true);
    setReadinessLoading(true);
    try {
      const [docs, readinessSummary] = await Promise.all([
        documentApi.list({ case_id: c.id, limit: 50 }),
        caseApi.getReadiness(c.id),
      ]);
      setCaseDocs(docs);
      setReadiness(readinessSummary);
    } catch {
      setCaseDocs([]);
      setReadiness(null);
    } finally {
      setDetailLoading(false);
      setReadinessLoading(false);
    }
  }, []);

  const handleDeleteCase = useCallback(
    async (c: Case) => {
      if (
        !window.confirm(
          `确定删除案件「${c.title}」？\n\n关联证据与材料库副本将删除；已生成的文书、案情分析仅解除关联。`,
        )
      ) {
        return;
      }
      try {
        await caseApi.delete(c.id);
        clearActiveCaseIfMatches(c.id);
        clearIntakeCreatedCaseId(c.id);
        if (selectedCase?.id === c.id) {
          setSelectedCase(null);
        }
        toast({ type: 'success', title: '案件已删除' });
        fetchCases();
      } catch (e: unknown) {
        const msg =
          e instanceof AxiosError
            ? (e.response?.data as { detail?: string })?.detail || '删除失败'
            : '删除失败';
        toast({ type: 'error', title: '删除失败', description: String(msg) });
      }
    },
    [fetchCases, selectedCase?.id, toast],
  );

  const handleDeleteCaseDocument = useCallback(
    async (doc: Document) => {
      if (!window.confirm(`确定删除文书「${doc.title}」？此操作不可恢复。`)) return;
      setDeletingDocId(doc.id);
      try {
        await documentApi.delete(doc.id);
        removeToolHistoryForDocument(doc.id);
        setCaseDocs((prev) => prev.filter((d) => d.id !== doc.id));
        toast({ type: 'success', title: '文书已删除' });
      } catch (e: unknown) {
        const msg =
          e instanceof AxiosError
            ? (e.response?.data as { detail?: string })?.detail || '删除失败'
            : '删除失败';
        toast({ type: 'error', title: '删除失败', description: String(msg) });
      } finally {
        setDeletingDocId(null);
      }
    },
    [toast],
  );

  useEffect(() => {
    const openId = searchParams.get('open');
    if (!openId || cases.length === 0) return;
    const c = cases.find((item) => item.id === Number(openId));
    if (c) openCaseDetail(c);
  }, [searchParams, cases, openCaseDetail]);

  const handleStatusUpdate = useCallback(async (caseId: number, newStatus: string) => {
    setUpdatingStatus(caseId);
    setError('');
    try {
      const updated = await caseApi.update(caseId, { status: newStatus });
      setCases((prev) => prev.map((c) => (c.id === caseId ? updated : c)));
      if (selectedCase?.id === caseId) {
        setSelectedCase(updated);
      }
    } catch {
      setError('更新案件状态失败，请重试');
    } finally {
      setUpdatingStatus(null);
    }
  }, [selectedCase]);

  const handleCreate = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    try {
      const created = await caseApi.create({
        ...createForm,
        title: withCaseTitleDatePrefix(createForm.title),
      });
      setActiveCaseId(created.id);
      setShowCreate(false);
      setCreateForm({ title: '', case_type: 'administrative_labor', description: '' });
      fetchCases();
      openCaseDetail(created);
    } catch {
      setError('创建案件失败，请重试');
    } finally {
      setCreating(false);
    }
  }, [createForm, fetchCases]);

  const formatDate = useCallback((dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
  }, []);

  // ── Case Detail View ─────────────────────────────────────────────
  if (selectedCase) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <button
          onClick={() => setSelectedCase(null)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          返回案件列表
        </button>

        <div className="rounded-xl border bg-card shadow-sm">
          <div className="border-b px-6 py-5">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-xl font-bold">{selectedCase.title}</h1>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Briefcase className="h-3.5 w-3.5" />
                    {caseTypeLabel[selectedCase.case_type] || selectedCase.case_type}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    创建于 {formatDate(selectedCase.created_at)}
                  </span>
                  {selectedCase.case_number && (
                    <span>案号：{selectedCase.case_number}</span>
                  )}
                </div>
              </div>
              <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium ${statusColor[selectedCase.status] || 'bg-gray-100 text-gray-700'}`}>
                {statusLabel[selectedCase.status] || selectedCase.status}
              </span>
              <button
                type="button"
                onClick={() => handleDeleteCase(selectedCase)}
                className="shrink-0 rounded-lg border border-destructive/40 px-3 py-1 text-xs text-destructive hover:bg-destructive/10"
              >
                删除案件
              </button>
              <button
                type="button"
                onClick={() => navigate(`/research?caseId=${selectedCase.id}`)}
                className="shrink-0 rounded-lg border px-3 py-1 text-xs hover:bg-muted"
              >
                分析案情
              </button>
              <button
                type="button"
                disabled={exportingPack}
                onClick={async () => {
                  setExportingPack(true);
                  try {
                    await downloadBlob(
                      () => intakeApi.exportCasePack(selectedCase.id),
                      `case_${selectedCase.id}_materials.zip`,
                    );
                  } catch {
                    setError('导出材料包失败');
                  } finally {
                    setExportingPack(false);
                  }
                }}
                className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-accent"
              >
                {exportingPack ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
                导出材料包
              </button>
            </div>
          </div>

          {/* Status transition actions */}
          {STATUS_TRANSITIONS[selectedCase.status] && (
            <div className="border-b px-6 py-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">操作：</span>
                {STATUS_TRANSITIONS[selectedCase.status].map((trans) => (
                  <button
                    key={trans.value}
                    onClick={() => handleStatusUpdate(selectedCase.id, trans.value)}
                    disabled={updatingStatus === selectedCase.id}
                    className="flex items-center gap-1 rounded-md bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/20 disabled:opacity-50"
                  >
                    {updatingStatus === selectedCase.id ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-3 w-3" />
                    )}
                    {trans.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Details */}
          <div className="space-y-4 px-6 py-5">
            {selectedCase.description && (
              <div>
                <h3 className="mb-1.5 text-sm font-semibold">案件描述</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{selectedCase.description}</p>
              </div>
            )}

            {(selectedCase.plaintiff || selectedCase.defendant) && (
              <div>
                <h3 className="mb-1.5 text-sm font-semibold">当事人</h3>
                <div className="flex items-center gap-4 text-sm">
                  {selectedCase.plaintiff && (
                    <span className="flex items-center gap-1">
                      <Users className="h-3.5 w-3.5 text-muted-foreground" />
                      原告：{selectedCase.plaintiff}
                    </span>
                  )}
                  {selectedCase.defendant && (
                    <span className="flex items-center gap-1">
                      <Users className="h-3.5 w-3.5 text-muted-foreground" />
                      被告：{selectedCase.defendant}
                    </span>
                  )}
                </div>
              </div>
            )}

            {selectedCase.court && (
              <div>
                <h3 className="mb-1.5 text-sm font-semibold">审理法院</h3>
                <p className="text-sm text-muted-foreground">{selectedCase.court}</p>
              </div>
            )}
          </div>
        </div>

        <CaseWorkflowStepper
          workflow={workflow}
          loading={workflowLoading}
          error={workflowError}
          className="mb-4"
        />
        <CaseAgentCoach
          step={agentStep}
          caseId={selectedCase.id}
          loading={agentLoading}
          error={agentError}
          onRefresh={refreshCaseAi}
        />
        <CaseReadinessHint
          readiness={readiness}
          loading={readinessLoading}
          variant="evidence"
        />
        {readiness?.evidence_suggestions && readiness.evidence_suggestions.length > 0 && (
          <EvidenceCoveragePanel readiness={readiness} />
        )}

        {/* Related Documents */}
        <div className="rounded-xl border bg-card shadow-sm">
          <div className="flex items-center justify-between border-b px-6 py-4">
            <h2 className="font-semibold">相关文书</h2>
            <span className="text-xs text-muted-foreground">{caseDocs.length} 份文书</span>
          </div>
          {detailLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
            </div>
          ) : caseDocs.length === 0 ? (
            <p className="px-6 py-8 text-center text-sm text-muted-foreground">暂无相关文书</p>
          ) : (
            <div className="divide-y">
              {caseDocs.map((doc) => (
                <div key={doc.id} className="flex items-center justify-between gap-2 px-6 py-3">
                  <button
                    type="button"
                    onClick={() => navigate(`/documents?docId=${doc.id}&worker=1`)}
                    className="min-w-0 flex-1 text-left hover:opacity-80"
                  >
                    <p className="truncate text-sm font-medium">{doc.title}</p>
                    <p className="text-xs text-muted-foreground">{formatDate(doc.created_at)}</p>
                  </button>
                  <span className="shrink-0 rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">
                    {statusLabel[doc.status] || doc.status}
                  </span>
                  <button
                    type="button"
                    aria-label="删除文书"
                    disabled={deletingDocId === doc.id}
                    onClick={() => handleDeleteCaseDocument(doc)}
                    className="shrink-0 rounded p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                  >
                    {deletingDocId === doc.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <p>{error}</p>
            <button onClick={() => setError('')} className="ml-auto shrink-0 hover:text-red-900">&times;</button>
          </div>
        )}
      </div>
    );
  }

  // ── Case List View ───────────────────────────────────────────────
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">管理案件</h1>
          <p className="mt-1 text-sm text-muted-foreground">共 {totalCount} 个案件</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          新建案件
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <p>{error}</p>
          <button onClick={() => setError('')} className="ml-auto shrink-0 hover:text-red-900">&times;</button>
        </div>
      )}

      {/* Search + Filters */}
      <div className="space-y-3">
        {/* Search bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={searchQuery}
            onChange={(e) => handleSearchInput(e.target.value)}
            placeholder="搜索案件标题、描述或案号..."
            className="w-full rounded-lg border border-input bg-background py-2.5 pl-10 pr-10 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Filter dropdowns */}
        <div className="flex items-center gap-3">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-lg border border-input bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
          >
            {CASE_TYPES.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Case List */}
      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : filteredCases.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border bg-card py-16">
          <Briefcase className="mb-3 h-12 w-12 text-muted-foreground/40" />
          {searchQuery ? (
            <>
              <p className="text-sm text-muted-foreground">未找到匹配 "{searchQuery}" 的案件</p>
              <button
                onClick={() => handleSearchInput('')}
                className="mt-2 text-sm text-primary hover:underline"
              >
                清除搜索
              </button>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">暂无案件，点击"新建案件"开始</p>
          )}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredCases.map((c) => (
              <div
                key={c.id}
                onClick={() => openCaseDetail(c)}
                className="group cursor-pointer rounded-xl border bg-card p-5 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="mb-3 flex items-start justify-between gap-2">
                  <h3 className="line-clamp-2 text-sm font-semibold leading-snug">{c.title}</h3>
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      type="button"
                      aria-label={`删除案件 ${c.title}`}
                      title="删除案件"
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDeleteCase(c);
                      }}
                      className="rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColor[c.status] || 'bg-gray-100 text-gray-700'}`}
                    >
                      {statusLabel[c.status] || c.status}
                    </span>
                  </div>
                </div>
                <div className="space-y-1 text-xs text-muted-foreground">
                  <p>
                    类型：
                    <span className="font-medium text-foreground">
                      {caseTypeLabel[c.case_type] || c.case_type}
                    </span>
                  </p>
                  <p>创建：{formatDate(c.created_at)}</p>
                  {c.description && (
                    <p className="line-clamp-2 pt-1">{c.description}</p>
                  )}
                </div>
                {/* Inline status update buttons */}
                {STATUS_TRANSITIONS[c.status] && (
                  <div className="mt-3 flex gap-1.5 border-t pt-3">
                    {STATUS_TRANSITIONS[c.status].map((trans) => (
                      <button
                        key={trans.value}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStatusUpdate(c.id, trans.value);
                        }}
                        disabled={updatingStatus === c.id}
                        className="flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/20 disabled:opacity-50"
                      >
                        {updatingStatus === c.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : null}
                        {trans.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <p className="text-xs text-muted-foreground">
                第 {safePage} / {totalPages} 页，共 {totalCount} 条
              </p>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={safePage <= 1}
                  className="rounded-md border p-2 transition-colors hover:bg-accent disabled:opacity-40"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((p) => p === 1 || p === totalPages || Math.abs(p - safePage) <= 1)
                  .map((p, idx, arr) => (
                    <span key={p} className="flex items-center">
                      {idx > 0 && arr[idx - 1] !== p - 1 && (
                        <span className="px-1 text-xs text-muted-foreground">...</span>
                      )}
                      <button
                        onClick={() => setPage(p)}
                        className={cn(
                          'min-w-[32px] rounded-md border px-2 py-1 text-xs font-medium transition-colors',
                          p === safePage
                            ? 'border-primary bg-primary text-primary-foreground'
                            : 'hover:bg-accent',
                        )}
                      >
                        {p}
                      </button>
                    </span>
                  ))}
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={safePage >= totalPages}
                  className="rounded-md border p-2 transition-colors hover:bg-accent disabled:opacity-40"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-xl border bg-card p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold">{workerMode ? '新建维权案件' : '新建案件'}</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium">案件标题</label>
                <input
                  required
                  value={createForm.title}
                  onChange={(e) => setCreateForm((p) => ({ ...p, title: e.target.value }))}
                  placeholder={workerMode ? '例如：拖欠工资维权' : '例如：张三与李四民间借贷纠纷'}
                  className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">案件类型</label>
                <select
                  value={createForm.case_type}
                  onChange={(e) => setCreateForm((p) => ({ ...p, case_type: e.target.value }))}
                  className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
                >
                  {(workerMode ? WORKER_CASE_TYPES : CASE_TYPES.filter((o) => o.value)).map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">案件描述</label>
                <textarea
                  value={createForm.description}
                  onChange={(e) => setCreateForm((p) => ({ ...p, description: e.target.value }))}
                  placeholder="简要描述案件情况..."
                  rows={3}
                  className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                >
                  {creating ? '创建中...' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default React.memo(Cases);
