import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  BookOpen,
  Loader2,
  Trash2,
  FileText,
  Download,
  AlertCircle,
  X,
  Copy,
  Check,
  Columns,
  PanelLeftClose,
  PanelLeft,
  Briefcase,
  Type,
} from 'lucide-react';
import { AxiosError } from 'axios';
import {
  researchApi,
  caseApi,
  type CaseMaterialsSummary,
  type CaseReadinessSummary,
  type ResearchReport as ReportType,
  type Case as CaseType,
} from '@/lib/api';
import { useToast } from '@/lib/toast';
import { cn } from '@/lib/utils';
import EvidenceCoveragePanel from '@/components/cases/EvidenceCoveragePanel';
import CaseReadinessHint from '@/components/cases/CaseReadinessHint';
import MarkdownRenderer from '@/lib/markdown';
import { announceToScreenReader } from '@/lib/accessibility';
import { addToolHistory } from '@/lib/tool-history';

/** Extract headings for table of contents */
function extractHeadings(text: string): { level: number; text: string; id: string }[] {
  const headings: { level: number; text: string; id: string }[] = [];
  const regex = /^(#{1,4})\s+(.+)$/gm;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const level = match[1].length;
    const text = match[2].trim();
    const id = `heading-${headings.length}`;
    headings.push({ level, text, id });
  }
  return headings;
}

/** Count words for Chinese + English text */
function countReportWords(text: string): number {
  const chineseChars = (text.match(/[一-鿿]/g) || []).length;
  const englishWords = text.replace(/[一-鿿]/g, ' ').trim().split(/\s+/).filter(Boolean).length;
  return chineseChars + englishWords;
}

/** Source quality indicators */
const SOURCE_QUALITY: Record<string, { label: string; color: string; icon: string }> = {
  vector_db: { label: '本地向量库', color: 'bg-blue-100 text-blue-700', icon: 'DB' },
  ai_knowledge: { label: 'AI法律知识', color: 'bg-purple-100 text-purple-700', icon: 'AI' },
  external_api: { label: '外部数据库', color: 'bg-amber-100 text-amber-700', icon: 'EX' },
  web_search: { label: '网络搜索', color: 'bg-gray-100 text-gray-700', icon: 'WEB' },
  knowledge_base: { label: '平台知识库', color: 'bg-green-100 text-green-700', icon: 'KB' },
};

const CONCLUSION_STYLES: Record<string, string> = {
  信息不足需补充: 'bg-amber-100 text-amber-900 border-amber-300',
  继续完善材料: 'bg-sky-100 text-sky-900 border-sky-300',
  可以准备劳动仲裁或监察投诉: 'bg-emerald-100 text-emerald-900 border-emerald-300',
  可以准备法院起诉: 'bg-violet-100 text-violet-900 border-violet-300',
};

export default function Research() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [caseId, setCaseId] = useState<number | null>(null);
  const [cases, setCases] = useState<CaseType[]>([]);
  const [materials, setMaterials] = useState<CaseMaterialsSummary | null>(null);
  const [readiness, setReadiness] = useState<CaseReadinessSummary | null>(null);
  const [materialsLoading, setMaterialsLoading] = useState(false);
  const [extraNotes, setExtraNotes] = useState('');
  const [generating, setGenerating] = useState(false);
  const [currentReport, setCurrentReport] = useState<ReportType | null>(null);
  const [history, setHistory] = useState<ReportType[]>([]);
  const [loading, setLoading] = useState(true);

  // 导出
  const [exportLoading, setExportLoading] = useState<string | null>(null);
  const [error, setError] = useState('');

  // Copy button state
  const [copied, setCopied] = useState(false);

  // Report comparison
  const [compareReportId, setCompareReportId] = useState<number | null>(null);
  const [compareReport, setCompareReport] = useState<ReportType | null>(null);
  const [showCompare, setShowCompare] = useState(false);

  // Show TOC sidebar
  const [showToc, setShowToc] = useState(true);

  // Mobile panel toggle
  const [showSidebar, setShowSidebar] = useState(true);

  // Confirmation dialog state (replaces browser confirm())
  const [confirmDialog, setConfirmDialog] = useState<{ message: string; onConfirm: () => void } | null>(null);

  useEffect(() => {
    caseApi.list({ limit: 100 }).then(setCases).catch(() => {});
    researchApi.list({ limit: 30 }).then(setHistory).catch(() => {}).finally(() => setLoading(false));

    const caseParam = searchParams.get('caseId');
    if (caseParam) {
      const id = Number(caseParam);
      if (Number.isFinite(id) && id > 0) setCaseId(id);
    }
    const reportParam = searchParams.get('reportId');
    if (reportParam) {
      const rid = Number(reportParam);
      if (Number.isFinite(rid) && rid > 0) {
        researchApi.get(rid).then((r) => {
          setCurrentReport(r);
          if (r.case_id) setCaseId(r.case_id);
        }).catch(() => {});
      }
    }
  }, [searchParams]);

  useEffect(() => {
    if (!caseId) {
      setMaterials(null);
      setReadiness(null);
      return;
    }
    setMaterialsLoading(true);
    Promise.all([caseApi.getMaterials(caseId), caseApi.getReadiness(caseId)])
      .then(([materialsSummary, readinessSummary]) => {
        setMaterials(materialsSummary);
        setReadiness(readinessSummary);
      })
      .catch(() => {
        setMaterials(null);
        setReadiness(null);
      })
      .finally(() => setMaterialsLoading(false));
  }, [caseId]);

  // Headings for TOC
  const tocHeadings = useMemo(() => {
    if (!currentReport) return [];
    return extractHeadings(currentReport.report);
  }, [currentReport]);

  // Rendered markdown (handled by MarkdownRenderer component)
  const reportContent = useMemo(() => currentReport?.report ?? '', [currentReport]);
  const compareReportContent = useMemo(() => compareReport?.report ?? '', [compareReport]);

  // Word count
  const wordCount = useMemo(() => {
    if (!currentReport) return 0;
    return countReportWords(currentReport.report);
  }, [currentReport]);

  const handleGenerateReport = useCallback(async () => {
    if (!caseId) return;
    if (materials && !materials.ready_for_analysis) {
      toast({
        type: 'error',
        title: '材料不足',
        description: '请至少填写案情描述，或上传证据/生成一份文书后再分析',
      });
      return;
    }
    setGenerating(true);
    setCurrentReport(null);
    try {
      const report = await caseApi.createCaseReport(caseId, {
        extra_notes: extraNotes.trim() || undefined,
      });
      setCurrentReport(report);
      setHistory((prev) => [report, ...prev.filter((r) => r.id !== report.id)]);
      const caseTitle = cases.find((c) => c.id === caseId)?.title || materials?.case_title || '案件';
      addToolHistory({
        kind: 'research',
        title: `案情分析：${caseTitle}`.slice(0, 60),
        route: '/research',
        query: String(report.id),
      });
      toast({
        type: 'success',
        title: '分析报告已生成',
        description: report.conclusion_level || '请查看维权阶段结论',
      });
      announceToScreenReader('案情分析报告生成完成');
      setShowSidebar(false);
    } catch (e: unknown) {
      const detail =
        e instanceof AxiosError
          ? (e.response?.data as { detail?: string })?.detail || e.message
          : e instanceof Error
            ? e.message
            : null;
      setError(String(detail || '生成失败'));
      toast({ type: 'error', title: '生成失败', description: detail || '未知错误' });
    } finally {
      setGenerating(false);
    }
  }, [caseId, materials, extraNotes, cases, toast]);

  const handleLoadReport = useCallback(async (id: number) => {
    try {
      const report = await researchApi.get(id);
      setCurrentReport(report);
      setShowSidebar(false);
    } catch {
      setError('加载报告失败');
    }
  }, []);

  const handleDelete = useCallback((id: number) => {
    setConfirmDialog({ message: '确定删除此报告？', onConfirm: async () => {
      try {
      await researchApi.delete(id);
      setHistory(prev => prev.filter(r => r.id !== id));
      if (currentReport?.id === id) setCurrentReport(null);
      toast({ type: 'success', title: '报告已删除' });
    } catch (e) {
      setError('删除失败，请重试');
      toast({ type: 'error', title: '删除失败' });
    }
    setConfirmDialog(null);
    }});
  }, [currentReport, toast]);

  const handleExportReport = useCallback(async (format: 'docx' | 'markdown') => {
    if (!currentReport) return;
    setExportLoading(format);
    try {
      const blob = format === 'docx'
        ? await researchApi.exportWord(currentReport.id)
        : await researchApi.exportMarkdown(currentReport.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `研究报告_${currentReport.query.slice(0, 20)}.${format === 'docx' ? 'docx' : 'md'}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast({ type: 'success', title: `已导出 ${format.toUpperCase()} 格式` });
    } catch {
      setError('导出失败，请重试');
      toast({ type: 'error', title: '导出失败' });
    } finally {
      setExportLoading(null);
    }
  }, [currentReport, toast]);

  const handleCopyReport = useCallback(async () => {
    if (!currentReport) return;
    try {
      await navigator.clipboard.writeText(currentReport.report);
      setCopied(true);
      toast({ type: 'success', title: '报告已复制到剪贴板' });
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = currentReport.report;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      toast({ type: 'success', title: '报告已复制到剪贴板' });
      setTimeout(() => setCopied(false), 2000);
    }
  }, [currentReport, toast]);

  const handleCompare = useCallback(async (id: number) => {
    try {
      const report = await researchApi.get(id);
      setCompareReport(report);
      setShowCompare(true);
    } catch {
      setError('加载报告失败');
    }
  }, []);

  return (
    <div className="flex flex-col lg:flex-row gap-4 lg:gap-6 h-auto lg:h-[calc(100vh-8rem)]">
      {/* Mobile header with toggle */}
      <div className="flex items-center justify-between lg:hidden">
        <div className="flex items-center gap-3">
          <BookOpen className="h-6 w-6 text-primary" />
          <h1 className="text-xl font-bold">分析案情</h1>
        </div>
        <button onClick={() => setShowSidebar(!showSidebar)} className="rounded-lg border p-2 hover:bg-accent">
          {showSidebar ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* 左侧面板：输入 + 历史 */}
      {showSidebar && (
        <div className="w-full lg:w-96 flex-shrink-0 flex flex-col gap-4 max-h-[60vh] lg:max-h-none overflow-y-auto">
          <div className="hidden lg:flex items-center gap-3">
            <BookOpen className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold">分析案情</h1>
          </div>
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert" aria-live="polite">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
              <button onClick={() => setError('')} className="ml-auto"><X className="h-4 w-4" /></button>
            </div>
          )}

          <p className="text-xs text-muted-foreground leading-relaxed">
            选择已创建的案件，系统将汇总案情描述、证据与文书等材料，生成维权阶段总结报告（可导出 Word/Markdown）。
          </p>

          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">选择案件</label>
              <select
                className="mt-1 w-full rounded-md border bg-transparent px-2 py-2 text-sm"
                value={caseId || ''}
                onChange={(e) => setCaseId(Number(e.target.value) || null)}
              >
                <option value="">请选择案件…</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
              {cases.length === 0 && (
                <p className="mt-1 text-[11px] text-amber-700">请先在「管理案件」中创建案件</p>
              )}
            </div>

            {caseId && (materialsLoading || readiness) && (
              <CaseReadinessHint
                readiness={readiness}
                loading={materialsLoading}
                variant="compact"
              />
            )}

            {caseId && readiness?.evidence_suggestions && readiness.evidence_suggestions.length > 0 && (
              <EvidenceCoveragePanel readiness={readiness} />
            )}

            {caseId && (
              <div className="rounded-lg border bg-muted/20 p-3 text-xs space-y-2">
                {materialsLoading ? (
                  <p className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    加载材料概况…
                  </p>
                ) : materials ? (
                  <>
                    <p className="font-medium flex items-center gap-1.5">
                      <Briefcase className="h-3.5 w-3.5" />
                      {materials.case_title}
                    </p>
                    <ul className="text-muted-foreground space-y-0.5">
                      <li>案情描述：{materials.has_description ? '已填写' : '未填写'}</li>
                      <li>关联文书：{materials.documents_count} 份</li>
                      <li>关联证据：{materials.evidence_count} 项</li>
                    </ul>
                    {readiness && (
                      <>
                        <div className="pt-1">
                          <div className="h-1.5 rounded-full bg-muted">
                            <div
                              className={cn(
                                'h-full rounded-full transition-all duration-300',
                                readiness.readiness_level === 'high'
                                  ? 'bg-emerald-500'
                                  : readiness.readiness_level === 'medium'
                                    ? 'bg-amber-500'
                                    : 'bg-rose-500',
                              )}
                              style={{ width: `${Math.max(0, Math.min(100, readiness.readiness_score))}%` }}
                            />
                          </div>
                          <p className="mt-1 text-[11px] font-medium">
                            AI 完整度 {readiness.readiness_score}%：{readiness.summary}
                          </p>
                        </div>
                        {readiness.missing_items.length > 0 && (
                          <ul className="space-y-0.5 text-[11px] text-amber-800">
                            {readiness.missing_items.slice(0, 2).map((item) => (
                              <li key={item}>- {item}</li>
                            ))}
                          </ul>
                        )}
                        {readiness.next_actions.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {readiness.next_actions.slice(0, 2).map((action) => (
                              <button
                                key={`${action.label}-${action.route}`}
                                type="button"
                                onClick={() => navigate(action.route)}
                                className="rounded-md border px-2 py-1 text-[11px] font-medium hover:bg-accent"
                                title={action.reason}
                              >
                                {action.label}
                              </button>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                    {!materials.ready_for_analysis && (
                      <p className="text-amber-800">请至少补充案情描述、证据或文书之一后再分析。</p>
                    )}
                  </>
                ) : null}
              </div>
            )}

            <div>
              <label className="text-xs font-medium text-muted-foreground">补充说明（可选）</label>
              <textarea
                className="mt-1 w-full rounded-lg border bg-transparent px-3 py-2 text-sm resize-none"
                rows={3}
                value={extraNotes}
                onChange={(e) => setExtraNotes(e.target.value)}
                placeholder="例如：尚未申请仲裁；用人单位已口头承诺补发工资…"
              />
            </div>

            <button
              type="button"
              onClick={handleGenerateReport}
              disabled={generating || !caseId || (materials !== null && !materials.ready_for_analysis)}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {generating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  正在分析…
                </>
              ) : (
                '生成案情分析报告'
              )}
            </button>
          </div>

          {/* 历史记录 */}
          <div className="flex-1 overflow-y-auto border-t pt-3">
            <h3 className="text-xs font-medium text-muted-foreground mb-2">历史报告</h3>
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : history.length === 0 ? (
              <p className="text-xs text-muted-foreground">暂无历史报告</p>
            ) : (
              <div className="space-y-1">
                {history.map(r => (
                  <div key={r.id} className="flex items-center gap-1 group">
                    <button
                      onClick={() => handleLoadReport(r.id)}
                      className={`flex-1 text-left text-xs px-2 py-1.5 rounded truncate hover:bg-accent ${currentReport?.id === r.id ? 'bg-accent font-medium' : ''}`}
                    >
                      {(r.query || '报告').replace(/^\[案情分析\]\s*/, '').slice(0, 36)}
                      {(r.query || '').length > 36 ? '…' : ''}
                    </button>
                    {/* Compare button */}
                    {currentReport && currentReport.id !== r.id && (
                      <button
                        onClick={() => handleCompare(r.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 text-muted-foreground hover:text-primary"
                        title="与此报告对比"
                      >
                        <Columns className="h-3 w-3" />
                      </button>
                    )}
                    <button onClick={() => handleDelete(r.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-destructive">
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 右侧面板：报告内容 */}
      <div className={cn('flex-1 flex overflow-hidden rounded-lg border bg-card min-h-[400px]', showCompare ? '' : '')}>
        {/* Mobile: show toggle when sidebar is open and no report */}
        {!showSidebar && (
          <button onClick={() => setShowSidebar(true)} className="lg:hidden absolute top-2 left-2 z-10 rounded-lg border bg-card p-1.5 hover:bg-accent">
            <PanelLeft className="h-4 w-4" />
          </button>
        )}
        {/* Report view (with optional TOC sidebar) */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {generating ? (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">正在汇总案件材料并生成分析报告…</p>
              <p className="text-xs text-muted-foreground">通常需要 30–90 秒</p>
            </div>
          ) : currentReport ? (
            <div className="max-w-none">
              {currentReport.conclusion_level && (
                <div
                  className={cn(
                    'mb-4 rounded-lg border px-4 py-3 text-sm font-semibold',
                    CONCLUSION_STYLES[currentReport.conclusion_level] ||
                      'bg-muted text-foreground border-border',
                  )}
                >
                  维权阶段结论：{currentReport.conclusion_level}
                </div>
              )}
              {/* Report header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-2">
                <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                  <FileText className="h-4 w-4" />
                  <span>{new Date(currentReport.created_at).toLocaleString()}</span>
                  <span>|</span>
                  <span className="flex items-center gap-1">
                    <Type className="h-3 w-3" />
                    {wordCount} 词
                  </span>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Source quality indicators */}
                  {currentReport.sources_used.map((source) => {
                    const quality = SOURCE_QUALITY[source];
                    const label =
                      source === 'case_profile'
                        ? '案件档案'
                        : source.startsWith('documents:')
                          ? `文书 ${source.split(':')[1]}`
                          : source.startsWith('evidence:')
                            ? `证据 ${source.split(':')[1]}`
                            : quality?.label || source;
                    return (
                      <span
                        key={source}
                        className={cn(
                          'text-xs px-2 py-0.5 rounded font-medium',
                          quality?.color || 'bg-muted text-muted-foreground',
                        )}
                      >
                        {label}
                      </span>
                    );
                  })}
                </div>
              </div>

              {/* Action buttons row */}
              <div className="flex items-center gap-2 mb-4 flex-wrap">
                <button
                  onClick={handleCopyReport}
                  className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent"
                >
                  {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                  {copied ? '已复制' : '复制报告'}
                </button>
                <button
                  onClick={() => handleExportReport('docx')}
                  disabled={exportLoading === 'docx'}
                  className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
                >
                  <Download className="h-3.5 w-3.5" />
                  {exportLoading === 'docx' ? '导出中...' : '导出 Word'}
                </button>
                <button
                  onClick={() => handleExportReport('markdown')}
                  disabled={exportLoading === 'markdown'}
                  className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
                >
                  <Download className="h-3.5 w-3.5" />
                  {exportLoading === 'markdown' ? '导出中...' : '导出 Markdown'}
                </button>
              </div>

              {/* Rendered Markdown report */}
              <div className="prose prose-sm max-w-none">
                <MarkdownRenderer content={reportContent} />
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground px-4">
              <BookOpen className="h-16 w-16 mb-4 opacity-20" />
              <h3 className="text-lg font-semibold mb-2">案情分析总结</h3>
              <p className="text-sm mb-4 max-w-md text-center leading-relaxed">
                请先在左侧选择案件。系统将根据该案已填写的案情、证据与文书，判断当前更适合「继续完善材料」还是「可以准备仲裁/起诉」等，并生成完整 Markdown 报告。
              </p>
            </div>
          )}
        </div>

        {/* TOC sidebar (only when report is loaded) - hidden on mobile */}
        {currentReport && !generating && tocHeadings.length > 0 && showToc && (
          <div className="hidden md:block w-56 flex-shrink-0 border-l overflow-y-auto p-4 bg-muted/20">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">目录</h4>
              <button onClick={() => setShowToc(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-3 w-3" />
              </button>
            </div>
            <div className="space-y-1">
              {tocHeadings.map((h, i) => (
                <button
                  key={i}
                  className={cn(
                    'block w-full text-left text-xs hover:text-primary hover:underline truncate transition-colors',
                    h.level === 1 ? 'font-semibold' : h.level === 2 ? 'font-medium pl-2' : 'pl-4',
                    h.level >= 3 && 'text-muted-foreground',
                  )}
                  title={h.text}
                >
                  {h.text}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Show TOC button when hidden */}
        {currentReport && !generating && tocHeadings.length > 0 && !showToc && (
          <button
            onClick={() => setShowToc(true)}
            className="hidden md:block absolute right-0 top-4 rounded-l-lg border border-r-0 bg-card px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            style={{ position: 'sticky', top: '1rem' }}
          >
            目录
          </button>
        )}
      </div>

      {/* Comparison Side Panel */}
      {showCompare && compareReport && (
        <div className="fixed inset-0 z-50 flex flex-col md:flex-row bg-black/50">
          <div className="flex-1 flex flex-col md:flex-row">
            {/* Left: current report */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6 border-b md:border-b-0 md:border-r bg-card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold">当前报告</h3>
                <span className="text-xs text-muted-foreground">{new Date(currentReport!.created_at).toLocaleString()}</span>
              </div>
              <div className="prose prose-sm max-w-none"><MarkdownRenderer content={reportContent} /></div>
            </div>
            {/* Right: compare report */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6 bg-muted/10">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold">对比报告</h3>
                <span className="text-xs text-muted-foreground">{new Date(compareReport.created_at).toLocaleString()}</span>
              </div>
              <div className="prose prose-sm max-w-none"><MarkdownRenderer content={compareReportContent} /></div>
            </div>
          </div>
          <button
            onClick={() => { setShowCompare(false); setCompareReport(null); }}
            className="fixed top-4 right-4 rounded-lg border bg-card p-2 hover:bg-accent"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Confirmation Dialog (replaces browser confirm()) */}
      {confirmDialog && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" onClick={() => setConfirmDialog(null)} role="dialog" aria-modal="true">
          <div className="bg-card rounded-xl shadow-lg p-6 w-full max-w-sm mx-4" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm font-medium mb-4">{confirmDialog.message}</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setConfirmDialog(null)} className="px-4 py-2 rounded-lg border text-sm hover:bg-accent">取消</button>
              <button onClick={() => confirmDialog.onConfirm()} className="px-4 py-2 rounded-lg bg-destructive text-destructive-foreground text-sm hover:bg-destructive/90">确定</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
