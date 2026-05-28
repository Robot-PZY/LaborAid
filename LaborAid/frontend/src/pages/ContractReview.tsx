import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Upload, FileText, Trash2, Download, Loader2, ShieldCheck, AlertTriangle, AlertCircle, Info, ChevronDown, ChevronRight, FileDown, PenLine, X, FileUp, CheckCircle2, Clock, Columns2, ArrowRightLeft, Sparkles, GitCompare, Eye } from 'lucide-react';
import { AxiosError } from 'axios';
import { contractApi, caseApi, type ContractItem, type ContractRiskItem, type Case as CaseType, type OcrStatus } from '@/lib/api';
import { useToast } from '@/lib/toast';
import OcrStatusBadge from '@/components/ocr/OcrStatusBadge';
import { cn } from '@/lib/utils';
import MarkdownRenderer from '@/lib/markdown';
import { announceToScreenReader } from '@/lib/accessibility';
import { addToolHistory } from '@/lib/tool-history';

const RISK_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-700 border-red-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  low: 'bg-blue-100 text-blue-700 border-blue-200',
};

const RISK_ICONS: Record<string, typeof AlertTriangle> = {
  high: AlertTriangle,
  medium: AlertCircle,
  low: Info,
};

/** Risk highlight color for inline clause text */
const RISK_INLINE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  high: { bg: 'bg-red-50', border: 'border-l-4 border-red-400', text: 'text-red-900' },
  medium: { bg: 'bg-amber-50', border: 'border-l-4 border-amber-400', text: 'text-amber-900' },
  low: { bg: 'bg-blue-50', border: 'border-l-4 border-blue-400', text: 'text-blue-900' },
};

const DIMENSION_LABELS: Record<string, string> = {
  legality: '合法性',
  completeness: '完备性',
  fairness: '公平性',
  clarity: '明确性',
  enforceability: '可执行性',
};

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: '待审查', color: 'bg-gray-100 text-gray-600' },
  parsing: { label: '解析中', color: 'bg-blue-100 text-blue-600' },
  reviewing: { label: '审查中', color: 'bg-amber-100 text-amber-600' },
  completed: { label: '已完成', color: 'bg-green-100 text-green-700' },
  failed: { label: '失败', color: 'bg-red-100 text-red-600' },
};

const REVIEW_STEPS = [
  { key: 'uploading', label: '上传文件' },
  { key: 'parsing', label: '解析合同' },
  { key: 'reviewing', label: 'AI审查中' },
  { key: 'completed', label: '审查完成' },
];

function getStepIndex(status: string): number {
  const map: Record<string, number> = { pending: 1, parsing: 1, reviewing: 2, completed: 3, failed: 0 };
  return map[status] ?? 0;
}

function RiskGauge({ score, size = 120 }: { score: number; size?: number }) {
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = Math.PI * radius;
  const progress = (score / 100) * circumference;
  const center = size / 2;

  let color = '#22c55e';
  if (score >= 30 && score < 60) color = '#f59e0b';
  if (score >= 60 && score < 80) color = '#f97316';
  if (score >= 80) color = '#ef4444';

  return (
    <div className="relative inline-flex flex-col items-center">
      <svg width={size} height={size / 2 + 20} viewBox={`0 0 ${size} ${size / 2 + 20}`}>
        <path d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none" stroke="hsl(var(--muted))" strokeWidth={strokeWidth} strokeLinecap="round" />
        <path d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round"
          strokeDasharray={`${progress} ${circumference}`} />
      </svg>
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 flex flex-col items-center">
        <span className="text-3xl font-bold" style={{ color }}>{score}</span>
        <span className="text-xs text-muted-foreground">/100</span>
      </div>
      <div className="flex justify-between w-full px-1 mt-1">
        <span className="text-[10px] text-green-600">安全</span>
        <span className="text-[10px] text-amber-600">中等</span>
        <span className="text-[10px] text-orange-600">高风险</span>
        <span className="text-[10px] text-red-600">危险</span>
      </div>
    </div>
  );
}

/** Simple bar chart for risk trend visualization */
function RiskTrendChart({ riskItems }: { riskItems: ContractRiskItem[] }) {
  const high = riskItems.filter(r => r.level === 'high').length;
  const medium = riskItems.filter(r => r.level === 'medium').length;
  const low = riskItems.filter(r => r.level === 'low').length;
  const total = high + medium + low;
  if (total === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">风险分布</h4>
      <div className="space-y-1.5">
        {[
          { label: '高风险', count: high, color: 'bg-red-500', textColor: 'text-red-600' },
          { label: '中风险', count: medium, color: 'bg-amber-500', textColor: 'text-amber-600' },
          { label: '低风险', count: low, color: 'bg-blue-500', textColor: 'text-blue-600' },
        ].map(item => (
          <div key={item.label} className="flex items-center gap-2">
            <span className="text-xs w-12 shrink-0 text-right">{item.label}</span>
            <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${item.color} transition-all`} style={{ width: `${(item.count / total) * 100}%` }} />
            </div>
            <span className={`text-xs font-medium w-6 ${item.textColor}`}>{item.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Clause-by-clause risk-highlighted text view */
function ClauseRiskHighlight({ clauses, riskItems, onSelectClause }: {
  clauses: { type: string; text: string; position: number }[];
  riskItems: ContractRiskItem[];
  onSelectClause: (idx: number) => void;
}) {
  // Map clause text to risk level
  const getRiskForClause = (clause: { type: string; text: string; position: number }) => {
    for (const risk of riskItems) {
      if (risk.clause && (clause.text.includes(risk.clause) || clause.type === risk.dimension)) {
        return risk.level;
      }
    }
    return null;
  };

  return (
    <div className="space-y-2 max-h-[500px] overflow-y-auto">
      {clauses.map((clause, i) => {
        const riskLevel = getRiskForClause(clause);
        const style = riskLevel ? RISK_INLINE_COLORS[riskLevel] : null;
        return (
          <div
            key={i}
            onClick={() => onSelectClause(i)}
            className={cn(
              'p-3 rounded-md text-sm cursor-pointer transition-all hover:shadow-sm',
              style ? `${style.bg} ${style.border} ${style.text}` : 'bg-muted/20',
            )}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium bg-primary/10 text-primary px-2 py-0.5 rounded shrink-0">
                {clause.type}
              </span>
              <span className="text-xs text-muted-foreground shrink-0">第{clause.position}条</span>
              {riskLevel && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                  riskLevel === 'high' ? 'bg-red-200 text-red-800' :
                  riskLevel === 'medium' ? 'bg-amber-200 text-amber-800' :
                  'bg-blue-200 text-blue-800'
                }`}>
                  {riskLevel === 'high' ? '高风险' : riskLevel === 'medium' ? '中风险' : '低风险'}
                </span>
              )}
            </div>
            <p className="whitespace-pre-wrap text-xs leading-relaxed">{clause.text}</p>
          </div>
        );
      })}
    </div>
  );
}

/** Side-by-side view for original text vs review notes */
function SideBySideView({ originalText, reviewReport }: { originalText: string; reviewReport: string }) {
  const [scrollSync, setScrollSync] = useState(true);
  const leftRef = useRef<HTMLDivElement>(null);
  const rightRef = useRef<HTMLDivElement>(null);

  const handleScroll = (source: 'left' | 'right') => {
    if (!scrollSync) return;
    const sourceEl = source === 'left' ? leftRef.current : rightRef.current;
    const targetEl = source === 'left' ? rightRef.current : leftRef.current;
    if (!sourceEl || !targetEl) return;
    targetEl.scrollTop = sourceEl.scrollTop;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 border rounded-lg overflow-hidden">
      <div className="border-r">
        <div className="p-2 bg-muted/30 border-b text-xs font-semibold text-muted-foreground text-center">原文内容</div>
        <div ref={leftRef} onScroll={() => handleScroll('left')} className="p-3 max-h-96 overflow-y-auto">
          <pre className="text-xs whitespace-pre-wrap break-words text-muted-foreground">{originalText}</pre>
        </div>
      </div>
      <div>
        <div className="p-2 bg-muted/30 border-b text-xs font-semibold text-muted-foreground text-center">审查意见</div>
        <div ref={rightRef} onScroll={() => handleScroll('right')} className="p-3 max-h-96 overflow-y-auto">
          <div className="prose prose-sm max-w-none">
            <MarkdownRenderer content={reviewReport} />
          </div>
        </div>
      </div>
    </div>
  );
}

/** Version comparison view */
function VersionCompare({ contracts }: { contracts: ContractItem[] }) {
  const [leftId, setLeftId] = useState<number | null>(null);
  const [rightId, setRightId] = useState<number | null>(null);

  const leftContract = contracts.find(c => c.id === leftId);
  const rightContract = contracts.find(c => c.id === rightId);

  const completedContracts = contracts.filter(c => c.status === 'completed' && c.risk_score !== null);

  if (completedContracts.length < 2) {
    return (
      <div className="text-center py-8 text-muted-foreground text-sm">
        至少需要两份已完成审查的合同才能进行比较
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs font-medium">合同 A</label>
          <select className="mt-1 w-full rounded-md border bg-transparent px-3 py-2 text-sm" value={leftId || ''}
            onChange={(e) => setLeftId(Number(e.target.value) || null)}>
            <option value="">选择合同</option>
            {completedContracts.map(c => <option key={c.id} value={c.id}>{c.title} ({c.risk_score}分)</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium">合同 B</label>
          <select className="mt-1 w-full rounded-md border bg-transparent px-3 py-2 text-sm" value={rightId || ''}
            onChange={(e) => setRightId(Number(e.target.value) || null)}>
            <option value="">选择合同</option>
            {completedContracts.map(c => <option key={c.id} value={c.id}>{c.title} ({c.risk_score}分)</option>)}
          </select>
        </div>
      </div>

      {leftContract && rightContract && (
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: '合同 A', c: leftContract },
            { label: '合同 B', c: rightContract },
          ].map(({ label, c }) => (
            <div key={label} className="rounded-lg border p-3 space-y-2">
              <h4 className="text-sm font-semibold">{label}: {c.title}</h4>
              <div className="flex items-center gap-2">
                <span className="text-xs">风险评分:</span>
                <span className={`text-lg font-bold ${c.risk_score! >= 60 ? 'text-red-600' : c.risk_score! >= 30 ? 'text-amber-600' : 'text-green-600'}`}>
                  {c.risk_score}
                </span>
              </div>
              {c.risk_items && (
                <div className="flex gap-2 text-xs">
                  <span className="text-red-600">高风险: {c.risk_items.filter(r => r.level === 'high').length}</span>
                  <span className="text-amber-600">中风险: {c.risk_items.filter(r => r.level === 'medium').length}</span>
                  <span className="text-blue-600">低风险: {c.risk_items.filter(r => r.level === 'low').length}</span>
                </div>
              )}
              <div className="text-xs text-muted-foreground">{new Date(c.created_at).toLocaleDateString()}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ContractReview() {
  const { toast } = useToast();
  const [contracts, setContracts] = useState<ContractItem[]>([]);
  const [cases, setCases] = useState<CaseType[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [parseLive, setParseLive] = useState<Record<number, { status: OcrStatus; message?: string | null }>>({});
  const [reviewing, setReviewing] = useState<number | null>(null);
  const [selectedContract, setSelectedContract] = useState<ContractItem | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [expandedClauses, setExpandedClauses] = useState<Set<number>>(new Set());

  // Detail view mode: 'overview' | 'sideBySide' | 'riskHighlight' | 'compare'
  const [detailMode, setDetailMode] = useState<'overview' | 'sideBySide' | 'riskHighlight' | 'compare'>('overview');

  const [form, setForm] = useState({ title: '', case_id: '' });
  const [showDraft, setShowDraft] = useState(false);
  const [draftForm, setDraftForm] = useState({ title: '', description: '', case_id: '' });
  const [draftFile, setDraftFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [drafting, setDrafting] = useState(false);
  const [suggestingFixes, setSuggestingFixes] = useState(false);
  const [suggestedFixes, setSuggestedFixes] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const draftFileRef = useRef<HTMLInputElement>(null);

  const [isDragOver, setIsDragOver] = useState(false);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  // Confirmation dialog state (replaces browser confirm())
  const [confirmDialog, setConfirmDialog] = useState<{ message: string; onConfirm: () => void } | null>(null);

  // Memoized risk level computation for the selected contract
  const riskSummary = useMemo(() => {
    if (!selectedContract?.risk_items) return { high: 0, medium: 0, low: 0, total: 0 };
    const high = selectedContract.risk_items.filter(r => r.level === 'high').length;
    const medium = selectedContract.risk_items.filter(r => r.level === 'medium').length;
    const low = selectedContract.risk_items.filter(r => r.level === 'low').length;
    return { high, medium, low, total: high + medium + low };
  }, [selectedContract?.risk_items]);

  // Memoized sorted risk items
  const sortedRiskItems = useMemo(() => {
    if (!selectedContract?.risk_items) return [];
    const order: Record<string, number> = { high: 0, medium: 1, low: 2 };
    return [...selectedContract.risk_items].sort((a, b) => (order[a.level] ?? 3) - (order[b.level] ?? 3));
  }, [selectedContract?.risk_items]);

  useEffect(() => {
    caseApi.list().then(setCases).catch(() => {});
    loadContracts();
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showUpload) setShowUpload(false);
        if (showDraft) setShowDraft(false);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [showUpload, showDraft]);

  const loadContracts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await contractApi.list();
      setContracts(data);
    } catch (e) { setError('加载合同列表失败'); } finally { setLoading(false); }
  }, []);

  const handleUpload = useCallback(async () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file || !form.title.trim()) return;
    setUploading(true);
    setParseLive((prev) => ({ ...prev, [-1]: { status: 'processing', message: '正在解析合同文字…' } }));
    try {
      const result = await contractApi.upload(file, form.title.trim(), form.case_id ? Number(form.case_id) : undefined);
      setParseLive((prev) => ({
        ...prev,
        [result.id]: { status: result.ocr_status ?? 'pending', message: result.ocr_message },
      }));
      setContracts((prev) => [result, ...prev]);
      setShowUpload(false);
      setForm({ title: '', case_id: '' });
      if (fileInputRef.current) fileInputRef.current.value = '';
      addToolHistory({
        kind: 'contract',
        title: result.title || file.name,
        route: '/contracts',
        query: String(result.id),
      });
      if (result.ocr_status === 'success') {
        toast({ type: 'success', title: '合同上传成功', description: result.ocr_message ?? undefined });
        announceToScreenReader('合同上传成功，文字解析完成');
      } else if (result.ocr_status === 'failed') {
        toast({ type: 'error', title: '合同文字解析失败', description: result.ocr_message ?? undefined });
        announceToScreenReader('合同文字解析失败');
      } else {
        toast({ type: 'success', title: '合同上传成功' });
        announceToScreenReader('合同上传成功');
      }
    } catch (e: unknown) {
      const msg = e instanceof AxiosError ? (e.response?.data?.detail || '上传失败') : '上传失败';
      setError(msg);
      toast({ type: 'error', title: '上传失败', description: msg });
    } finally {
      setUploading(false);
      setParseLive((prev) => {
        const next = { ...prev };
        delete next[-1];
        return next;
      });
    }
  }, [form.title, form.case_id, toast]);

  const handleReview = useCallback(async (id: number) => {
    setReviewing(id);
    try {
      const result = await contractApi.review(id);
      setContracts((prev) => prev.map((c) => (c.id === id ? result : c)));
      if (selectedContract?.id === id) setSelectedContract(result);
      toast({ type: 'success', title: '合同审查完成' }); announceToScreenReader('合同审查完成');
    } catch (e: unknown) {
      const msg = e instanceof AxiosError ? (e.response?.data?.detail || '审查失败') : '审查失败';
      setError(msg);
      toast({ type: 'error', title: '审查失败', description: msg });
      loadContracts();
    } finally { setReviewing(null); }
  }, [selectedContract, toast, loadContracts]);

  const handleDelete = useCallback(async (id: number) => {
    setConfirmDialog({ message: '确定删除此合同？', onConfirm: async () => {
      try {
        await contractApi.delete(id);
        setContracts((prev) => prev.filter((c) => c.id !== id));
        if (selectedContract?.id === id) setSelectedContract(null);
        toast({ type: 'success', title: '合同已删除' });
      } catch (e) {
        setError('删除失败');
        toast({ type: 'error', title: '删除失败' });
      }
      setConfirmDialog(null);
    }});
  }, [selectedContract, toast]);

  const handleDraft = useCallback(async () => {
    if (!draftForm.title.trim() || !draftForm.description.trim()) return;
    setDrafting(true);
    try {
      const result = await contractApi.draft({
        title: draftForm.title.trim(),
        description: draftForm.description.trim(),
        case_id: draftForm.case_id ? Number(draftForm.case_id) : undefined,
        file: draftFile || undefined,
      });
      setContracts((prev) => [result, ...prev]);
      setShowDraft(false);
      setDraftForm({ title: '', description: '', case_id: '' });
      setDraftFile(null);
      toast({ type: 'success', title: '合同起草完成' }); announceToScreenReader('合同起草完成');
    } catch (e: unknown) {
      const msg = e instanceof AxiosError ? (e.response?.data?.detail || '起草失败') : '起草失败';
      setError(msg);
      toast({ type: 'error', title: '起草失败', description: msg });
    } finally { setDrafting(false); }
  }, [draftForm, draftFile, toast]);

  const handleUploadRef = useRef(handleUpload);
  handleUploadRef.current = handleUpload;
  const handleDraftRef = useRef(handleDraft);
  handleDraftRef.current = handleDraft;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        if (showUpload) handleUploadRef.current();
        if (showDraft) handleDraftRef.current();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [showUpload, showDraft]);

  const handleExport = useCallback(async (id: number, format: string) => {
    try {
      const blob = await contractApi.exportReport(id, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `合同审查报告.${format === 'docx' ? 'docx' : 'md'}`;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
      toast({ type: 'success', title: `已导出 ${format.toUpperCase()} 格式` });
    } catch (e) {
      setError('导出失败');
      toast({ type: 'error', title: '导出失败' });
    }
  }, [toast]);

  /** Suggest fixes: generate proposed amendments based on risk items */
  const handleSuggestFixes = useCallback(async () => {
    if (!selectedContract) return;
    setSuggestingFixes(true);
    setSuggestedFixes(null);
    try {
      // Use the review endpoint to get suggested amendments
      // If the contract already has risk items with suggestions, compile them
      if (selectedContract.risk_items && selectedContract.risk_items.length > 0) {
        const fixes = selectedContract.risk_items
          .filter(r => r.suggestion)
          .map((r, i) => {
            const dimension = DIMENSION_LABELS[r.dimension] || r.dimension;
            const level = r.level === 'high' ? '高风险' : r.level === 'medium' ? '中风险' : '低风险';
            return `### 修改建议 ${i + 1} [${level}] ${dimension}\n\n**问题描述:** ${r.issue}\n\n**涉及条款:** ${r.clause || '未指定'}\n\n**建议修改为:**\n${r.suggestion}`;
          })
          .join('\n\n---\n\n');
        setSuggestedFixes(fixes || '暂无具体修改建议。');
      } else {
        setSuggestedFixes('暂无风险项，请先进行合同审查。');
      }
      toast({ type: 'success', title: '修改建议已生成' });
    } catch (e: unknown) {
      setError('生成修改建议失败');
      toast({ type: 'error', title: '生成修改建议失败' });
    } finally { setSuggestingFixes(false); }
  }, [selectedContract, toast]);

  const selectContract = useCallback(async (c: ContractItem) => {
    if (selectedContract?.id === c.id) {
      setSelectedContract(null);
      return;
    }
    try {
      const detail = await contractApi.get(c.id);
      setSelectedContract(detail);
      setExpandedClauses(new Set());
      setDetailMode('overview');
      setSuggestedFixes(null);
    } catch {
      setSelectedContract(c);
    }
  }, [selectedContract]);

  const toggleClause = useCallback((idx: number) => {
    setExpandedClauses(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    const title = file.name.replace(/\.[^/.]+$/, '');
    setUploading(true);
    try {
      const result = await contractApi.upload(file, title);
      setContracts((prev) => [result, ...prev]);
      toast({ type: 'success', title: '合同上传成功' }); announceToScreenReader('合同上传成功');
    } catch (e: unknown) {
      const msg = e instanceof AxiosError ? (e.response?.data?.detail || '上传失败') : '上传失败';
      setError(msg);
      toast({ type: 'error', title: '上传失败', description: msg });
    } finally { setUploading(false); }
  }, [toast]);

  const getScoreColor = (score: number | null) => {
    if (score === null) return 'text-gray-400';
    if (score < 30) return 'text-green-600';
    if (score < 60) return 'text-amber-600';
    return 'text-red-600';
  };

  const getScoreLabel = (score: number | null) => {
    if (score === null) return '未评估';
    if (score < 30) return '低风险';
    if (score < 60) return '中等风险';
    if (score < 80) return '高风险';
    return '极高风险';
  };

  const renderRiskBadge = (risk: ContractRiskItem) => {
    const Icon = RISK_ICONS[risk.level] || Info;
    return (
      <div key={`${risk.dimension}-${risk.clause}`} className={`rounded-lg border p-3 sm:p-4 ${RISK_COLORS[risk.level] || ''}`}>
        <div className="flex items-start gap-2">
          <Icon className="h-5 w-5 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="font-medium">{DIMENSION_LABELS[risk.dimension] || risk.dimension}</span>
              <span className="text-xs px-1.5 py-0.5 rounded bg-white/60">
                {risk.level === 'high' ? '高风险' : risk.level === 'medium' ? '中风险' : '低风险'}
              </span>
            </div>
            <p className="text-sm mb-2">{risk.issue}</p>
            {risk.clause && <p className="text-xs opacity-75 mb-2 italic truncate">相关条款: {risk.clause}</p>}
            {risk.suggestion && (
              <div className="text-sm bg-white/50 rounded p-2 mt-1">
                <span className="font-medium">修改建议:</span> {risk.suggestion}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Check if side-by-side view is available
  const canSideBySide = selectedContract?.parsed_text && selectedContract?.review_report;
  // Check if risk highlight is available
  const canRiskHighlight = selectedContract?.clauses && selectedContract?.clauses.length > 0 && selectedContract?.risk_items && selectedContract.risk_items.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">审查合同</h1>
          <p className="text-sm text-muted-foreground mt-1">上传合同文件，AI自动识别条款、标注风险、生成修改建议</p>
        </div>
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 max-w-md" role="alert" aria-live="polite">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
            <button onClick={() => setError('')} className="ml-auto"><X className="h-4 w-4" /></button>
          </div>
        )}
        <div className="flex gap-2">
          <button onClick={() => setShowDraft(true)}
            className="flex items-center gap-2 px-4 py-2.5 border border-primary text-primary rounded-lg hover:bg-primary/10 transition-colors text-sm">
            <PenLine className="h-4 w-4" /> 起草合同
          </button>
          <button onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm">
            <Upload className="h-4 w-4" /> 上传合同
          </button>
        </div>
      </div>

      {/* Drag-and-drop zone */}
      {contracts.length === 0 && !loading && (
        <div ref={dropZoneRef} onDragOver={handleDragEnter} onDragLeave={handleDragLeave} onDrop={handleDrop}
          className={cn(
            'rounded-xl border-2 border-dashed p-8 sm:p-12 text-center transition-all',
            isDragOver ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-muted-foreground/25 hover:border-primary/50',
            uploading && 'opacity-50 pointer-events-none',
          )}>
          {uploading ? (
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">上传并解析文字中…</p>
              <OcrStatusBadge status="processing" compact />
            </div>
          ) : (
            <>
              <FileUp className={cn('h-12 w-12 mx-auto mb-4', isDragOver ? 'text-primary' : 'text-muted-foreground/40')} />
              <h3 className="text-lg font-semibold mb-2">{isDragOver ? '松开以上传合同' : '拖拽合同文件到此处上传'}</h3>
              <p className="text-sm text-muted-foreground mb-4">支持 PDF、Word、TXT、图片格式</p>
            </>
          )}
        </div>
      )}

      {/* Draft Dialog */}
      {showDraft && (
        <div className="fixed inset-0 z-50 flex items-start sm:items-center justify-center bg-black/50 p-4 overflow-y-auto" onClick={() => setShowDraft(false)} role="dialog" aria-modal="true" aria-label="起草合同">
          <div className="bg-card rounded-xl shadow-lg p-4 sm:p-6 w-full max-w-lg my-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">AI 起草合同</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">合同标题 *</label>
                <input type="text" value={draftForm.title} onChange={(e) => setDraftForm((f) => ({ ...f, title: e.target.value }))}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm" placeholder="例: 软件开发服务合同" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">需求描述 *</label>
                <textarea value={draftForm.description} onChange={(e) => setDraftForm((f) => ({ ...f, description: e.target.value }))}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm min-h-[120px]"
                  placeholder="描述合同需求..." />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">参考文件（可选）</label>
                <input ref={draftFileRef} type="file" accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.xls"
                  className="w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
                  onChange={(e) => setDraftFile(e.target.files?.[0] || null)} />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">关联案件（可选）</label>
                <select value={draftForm.case_id} onChange={(e) => setDraftForm((f) => ({ ...f, case_id: e.target.value }))}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm">
                  <option value="">不关联案件</option>
                  {cases.map((c) => (<option key={c.id} value={c.id}>{c.title}</option>))}
                </select>
              </div>
              <div className="flex gap-3 justify-end">
                <button onClick={() => setShowDraft(false)} className="px-4 py-2 rounded-lg border hover:bg-accent text-sm">取消</button>
                <button onClick={handleDraft} disabled={drafting || !draftForm.title.trim() || !draftForm.description.trim()}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm disabled:opacity-50">
                  {drafting ? <Loader2 className="h-4 w-4 animate-spin" /> : '起草合同'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Dialog */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-start sm:items-center justify-center bg-black/50 p-4 overflow-y-auto" onClick={() => setShowUpload(false)} role="dialog" aria-modal="true" aria-label="上传合同">
          <div className="bg-card rounded-xl shadow-lg p-4 sm:p-6 w-full max-w-md my-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">上传合同文件</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">合同标题 *</label>
                <input type="text" value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm" placeholder="例: XX公司采购合同" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">关联案件（可选）</label>
                <select value={form.case_id} onChange={(e) => setForm((f) => ({ ...f, case_id: e.target.value }))}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm">
                  <option value="">不关联案件</option>
                  {cases.map((c) => (<option key={c.id} value={c.id}>{c.title}</option>))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">合同文件 *</label>
                <input ref={fileInputRef} type="file" accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.xls,.png,.jpg,.jpeg,.gif,.webp,.bmp,.tiff"
                  className="w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-primary/10 file:text-primary hover:file:bg-primary/20" />
              </div>
              <div className="flex gap-3 justify-end">
                <button onClick={() => setShowUpload(false)} className="px-4 py-2 rounded-lg border hover:bg-accent text-sm">取消</button>
                <button onClick={handleUpload} disabled={uploading || !form.title.trim()}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm disabled:opacity-50">
                  {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : '上传'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Contract List */}
        <div className="lg:col-span-1 space-y-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">合同列表 ({contracts.length})</h2>
          {loading ? (
            <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : contracts.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p>暂无合同</p>
            </div>
          ) : (
            <div className="space-y-2">
              {contracts.map((c) => {
                const st = STATUS_MAP[c.status] || STATUS_MAP.pending;
                const isSelected = selectedContract?.id === c.id;
                return (
                  <div key={c.id} onClick={() => selectContract(c)}
                    className={`rounded-lg border p-3 cursor-pointer transition-all hover:shadow-sm ${isSelected ? 'border-primary bg-primary/5 ring-1 ring-primary/20' : 'hover:border-primary/30'}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{c.title}</p>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <span className={`text-xs px-2 py-0.5 rounded ${st.color}`}>{st.label}</span>
                          {c.file_type && <span className="text-xs text-muted-foreground uppercase">{c.file_type}</span>}
                          {c.has_file && (
                            <OcrStatusBadge
                              compact
                              status={parseLive[c.id]?.status ?? c.ocr_status}
                              message={parseLive[c.id]?.message ?? c.ocr_message}
                            />
                          )}
                        </div>
                      </div>
                      {c.risk_score !== null && (
                        <div className={`text-lg font-bold ${getScoreColor(c.risk_score)}`}>{c.risk_score}</div>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{new Date(c.created_at).toLocaleDateString()}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Contract Detail */}
        <div className="lg:col-span-2">
          {!selectedContract ? (
            <div className="flex items-center justify-center h-64 lg:h-96 text-muted-foreground">
              <div className="text-center">
                <ShieldCheck className="h-16 w-16 mx-auto mb-3 opacity-20" />
                <p className="text-lg font-semibold mb-2">选择一份合同查看审查结果</p>
                <p className="text-sm max-w-sm mx-auto">从左侧列表选择合同，或上传新合同文件开始AI智能审查。</p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Header with view mode tabs */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-bold">{selectedContract.title}</h2>
                  <div className="flex items-center gap-3 mt-1 flex-wrap">
                    <span className={`text-xs px-2 py-0.5 rounded ${STATUS_MAP[selectedContract.status]?.color}`}>
                      {STATUS_MAP[selectedContract.status]?.label}
                    </span>
                    {selectedContract.has_file && (
                      <OcrStatusBadge
                        status={parseLive[selectedContract.id]?.status ?? selectedContract.ocr_status}
                        message={parseLive[selectedContract.id]?.message ?? selectedContract.ocr_message}
                      />
                    )}
                    {selectedContract.risk_score !== null && (
                      <span className={`font-medium ${getScoreColor(selectedContract.risk_score)}`}>
                        {getScoreLabel(selectedContract.risk_score)} ({selectedContract.risk_score}/100)
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {(selectedContract.status === 'pending' || selectedContract.status === 'failed') && (selectedContract.parsed_text || selectedContract.has_file) && (
                    <button onClick={() => handleReview(selectedContract.id)} disabled={reviewing === selectedContract.id}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-50">
                      {reviewing === selectedContract.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                      {reviewing === selectedContract.id ? '审查中...' : 'AI审查'}
                    </button>
                  )}
                  {selectedContract.review_report && (
                    <>
                      <button onClick={() => handleExport(selectedContract.id, 'markdown')}
                        className="flex items-center gap-1 px-3 py-2 rounded-lg border text-sm hover:bg-accent">
                        <FileDown className="h-4 w-4" /> MD
                      </button>
                      <button onClick={() => handleExport(selectedContract.id, 'docx')}
                        className="flex items-center gap-1 px-3 py-2 rounded-lg border text-sm hover:bg-accent">
                        <Download className="h-4 w-4" /> Word
                      </button>
                    </>
                  )}
                  <button onClick={() => handleDelete(selectedContract.id)} aria-label="删除合同"
                    className="p-2 rounded-lg text-red-500 hover:bg-red-50">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* View mode tabs */}
              {selectedContract.status === 'completed' && (
                <div className="flex gap-1 border-b overflow-x-auto">
                  {[
                    { key: 'overview' as const, label: '总览', icon: Eye },
                    { key: 'riskHighlight' as const, label: '条款风险标注', icon: AlertTriangle, disabled: !canRiskHighlight },
                    { key: 'sideBySide' as const, label: '对照视图', icon: Columns2, disabled: !canSideBySide },
                    { key: 'compare' as const, label: '版本比较', icon: GitCompare, disabled: contracts.filter(c => c.status === 'completed').length < 2 },
                  ].map(tab => (
                    <button key={tab.key} onClick={() => !tab.disabled && setDetailMode(tab.key)}
                      disabled={tab.disabled}
                      className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
                        detailMode === tab.key ? 'border-primary text-primary' :
                        tab.disabled ? 'border-transparent text-muted-foreground/40 cursor-not-allowed' :
                        'border-transparent text-muted-foreground hover:text-foreground'
                      }`}>
                      <tab.icon className="h-3 w-3" /> {tab.label}
                    </button>
                  ))}
                </div>
              )}

              {/* OVERVIEW MODE */}
              {detailMode === 'overview' && (<>
                {/* Review Progress Steps */}
                {selectedContract.status !== 'pending' && (
                  <div className="rounded-lg border p-3 sm:p-4">
                    <div className="flex items-center gap-1 flex-wrap">
                      {REVIEW_STEPS.map((step, idx) => {
                        const currentIdx = getStepIndex(selectedContract.status);
                        const isCompleted = idx < currentIdx;
                        const isCurrent = idx === currentIdx;
                        const isFailed = selectedContract.status === 'failed' && idx === currentIdx;
                        return (
                          <div key={step.key} className="flex items-center gap-1 flex-1 min-w-0">
                            <div className="flex items-center gap-1 sm:gap-2 flex-1 min-w-0">
                              <div className={cn(
                                'flex items-center justify-center h-6 w-6 sm:h-7 sm:w-7 rounded-full text-xs font-medium shrink-0',
                                isCompleted ? 'bg-green-100 text-green-700' :
                                isFailed ? 'bg-red-100 text-red-700' :
                                isCurrent ? 'bg-primary/10 text-primary ring-2 ring-primary/30' :
                                'bg-muted text-muted-foreground',
                              )}>
                                {isCompleted ? <CheckCircle2 className="h-3.5 w-3.5" /> :
                                 isCurrent && selectedContract.status === 'reviewing' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> :
                                 isFailed ? <AlertCircle className="h-3.5 w-3.5" /> :
                                 <span>{idx + 1}</span>}
                              </div>
                              <span className={cn(
                                'text-xs whitespace-nowrap truncate',
                                isCompleted ? 'text-green-700 font-medium' :
                                isCurrent ? 'text-primary font-medium' :
                                'text-muted-foreground',
                              )}>{step.label}</span>
                            </div>
                            {idx < REVIEW_STEPS.length - 1 && (
                              <div className={cn('h-px flex-1 mx-1 hidden sm:block', idx < currentIdx ? 'bg-green-300' : 'bg-border')} />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Risk Score Gauge + Risk Trend Chart */}
                {selectedContract.risk_score !== null && (
                  <div className="rounded-lg border p-4">
                    <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6">
                      <RiskGauge score={selectedContract.risk_score} size={140} />
                      <div className="flex-1 w-full text-center sm:text-left">
                        <h3 className="text-sm font-semibold mb-2">综合风险评分</h3>
                        <p className="text-sm text-muted-foreground mb-3">
                          {getScoreLabel(selectedContract.risk_score)} - 风险评分{selectedContract.risk_score >= 60 ? '较高' : selectedContract.risk_score >= 30 ? '中等' : '较低'}。
                        </p>
                        {selectedContract.risk_items && selectedContract.risk_items.length > 0 && (
                          <RiskTrendChart riskItems={selectedContract.risk_items} />
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Risk Items */}
                {selectedContract.risk_items && selectedContract.risk_items.length > 0 && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                        风险项 ({selectedContract.risk_items.length})
                      </h3>
                      <button onClick={handleSuggestFixes} disabled={suggestingFixes}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium hover:bg-accent disabled:opacity-50">
                        {suggestingFixes ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
                        生成修改建议
                      </button>
                    </div>
                    <div className="grid gap-3">
                      {sortedRiskItems
                        .map((risk, i) => (<div key={i}>{renderRiskBadge(risk)}</div>))}
                    </div>
                  </div>
                )}

                {/* Suggested Fixes Panel */}
                {suggestedFixes && (
                  <div className="rounded-lg border p-4 sm:p-5 bg-green-50/50">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold text-green-800 uppercase tracking-wider">合同修改建议</h3>
                      <button onClick={() => setSuggestedFixes(null)} className="text-xs text-muted-foreground hover:underline">关闭</button>
                    </div>
                    <div className="prose prose-sm max-w-none">
                      <MarkdownRenderer content={suggestedFixes} />
                    </div>
                  </div>
                )}

                {/* Clauses */}
                {selectedContract.clauses && selectedContract.clauses.length > 0 && (
                  <div className="rounded-lg border">
                    <div className="p-3 border-b">
                      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                        识别的条款 ({selectedContract.clauses.length})
                      </h3>
                    </div>
                    <div className="divide-y max-h-80 overflow-y-auto">
                      {selectedContract.clauses.map((clause, i) => {
                        const isExpanded = expandedClauses.has(i);
                        return (
                          <div key={i} className="px-3">
                            <button onClick={() => toggleClause(i)}
                              className="flex items-center gap-2 w-full py-2.5 text-left hover:bg-accent/50 transition-colors">
                              {isExpanded ? <ChevronDown className="h-3.5 w-3.5 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 shrink-0" />}
                              <span className="text-xs font-medium bg-primary/10 text-primary px-2 py-0.5 rounded shrink-0">{clause.type}</span>
                              <span className="text-xs text-muted-foreground shrink-0">第{clause.position}条</span>
                              <span className="text-sm truncate flex-1">{isExpanded ? '' : clause.text.slice(0, 60) + '...'}</span>
                            </button>
                            {isExpanded && (
                              <div className="pb-3 pl-8">
                                <p className="text-sm whitespace-pre-wrap rounded-lg bg-muted/30 p-3">{clause.text}</p>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Review Report */}
                {selectedContract.review_report && (
                  <div className="rounded-lg border p-4 sm:p-5 bg-muted/20">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">审查报告</h3>
                      <button onClick={() => handleExport(selectedContract.id, 'docx')}
                        className="flex items-center gap-1.5 text-xs font-medium text-primary hover:underline">
                        <Download className="h-3.5 w-3.5" /> 下载审查报告
                      </button>
                    </div>
                    <div className="prose prose-sm max-w-none">
                      <MarkdownRenderer content={selectedContract.review_report} />
                    </div>
                  </div>
                )}

                {/* Parsed Text (collapsible) */}
                {selectedContract.parsed_text && (
                  <details className="rounded-lg border">
                    <summary className="p-3 text-sm font-medium cursor-pointer hover:bg-accent rounded-t-lg">
                      原文内容 ({selectedContract.parsed_text.length} 字)
                    </summary>
                    <div className="p-3 pt-0 max-h-96 overflow-y-auto">
                      <pre className="text-xs whitespace-pre-wrap break-all text-muted-foreground">{selectedContract.parsed_text}</pre>
                    </div>
                  </details>
                )}
              </>)}

              {/* RISK HIGHLIGHT MODE */}
              {detailMode === 'riskHighlight' && selectedContract.clauses && selectedContract.risk_items && (
                <ClauseRiskHighlight
                  clauses={selectedContract.clauses}
                  riskItems={selectedContract.risk_items}
                  onSelectClause={(idx) => toggleClause(idx)}
                />
              )}

              {/* SIDE-BY-SIDE MODE */}
              {detailMode === 'sideBySide' && selectedContract.parsed_text && selectedContract.review_report && (
                <SideBySideView originalText={selectedContract.parsed_text} reviewReport={selectedContract.review_report} />
              )}

              {/* COMPARE MODE */}
              {detailMode === 'compare' && (
                <VersionCompare contracts={contracts} />
              )}
            </div>
          )}
        </div>
      </div>

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
