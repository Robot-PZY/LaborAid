import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Upload, FileText, Trash2, Download, Loader2, Sparkles, ChevronDown, ChevronRight, Link2, MessageSquare, AlertCircle, X, Plus, Image, Mic, Volume2, Scale, Camera, Monitor, FileSpreadsheet, Clock, Eye } from 'lucide-react';
import { AxiosError } from 'axios';
import {
  caseApi,
  evidenceApi,
  evidenceChainApi,
  type Case as CaseType,
  type CaseReadinessSummary,
  type EvidenceItem,
  type OcrStatus,
} from '@/lib/api';
import CaseReadinessHint from '@/components/cases/CaseReadinessHint';
import { useToast } from '@/lib/toast';
import OcrStatusBadge from '@/components/ocr/OcrStatusBadge';
import type { ChainAnalysisResult } from '@/lib/api';
import { loadIntakeSession } from '@/lib/intake-session';
import { getActiveCaseId, setActiveCaseId, subscribeActiveCase } from '@/lib/active-case';
import CredibilityBar from '@/components/ui/CredibilityBar';
import { addToolHistory } from '@/lib/tool-history';
import {
  clearChainAnalysis,
  loadChainAnalysis,
  saveChainAnalysis,
} from '@/lib/case-ai-cache';

const VALID_EVIDENCE_TYPES = [
  'documentary',
  'physical',
  'electronic',
  'testimony',
  'audio_visual',
  'expert',
] as const;

const TYPE_LABELS: Record<string, string> = {
  documentary: '书证',
  physical: '物证',
  electronic: '电子数据',
  testimony: '证人证言',
  audio_visual: '视听资料',
  expert: '鉴定意见',
};

const TYPE_COLORS: Record<string, string> = {
  documentary: 'bg-blue-100 text-blue-700',
  physical: 'bg-amber-100 text-amber-700',
  electronic: 'bg-green-100 text-green-700',
  testimony: 'bg-purple-100 text-purple-700',
  audio_visual: 'bg-pink-100 text-pink-700',
  expert: 'bg-red-100 text-red-700',
};

/** Evidence type icon mapping */
const TYPE_ICONS: Record<string, typeof FileText> = {
  documentary: FileText,
  physical: Camera,
  electronic: Monitor,
  testimony: MessageSquare,
  audio_visual: Volume2,
  expert: Scale,
};

function resolveCaseIdFromUrl(params: URLSearchParams): number | null {
  const raw = params.get('caseId') || params.get('open') || params.get('case_id');
  if (!raw) return null;
  const id = Number(raw);
  return Number.isFinite(id) && id > 0 ? id : null;
}

function inferEvidenceType(fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  if (['mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac', 'wma'].includes(ext)) return 'audio_visual';
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff'].includes(ext)) return 'electronic';
  return 'documentary';
}

function titleFromFileName(fileName: string): string {
  const base = fileName.replace(/\.[^.]+$/, '').trim();
  return base || fileName;
}

/** File type classification for preview */
function getFileCategory(fileName: string | null): 'image' | 'audio' | 'document' | 'unknown' {
  if (!fileName) return 'unknown';
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff'].includes(ext)) return 'image';
  if (['mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac', 'wma'].includes(ext)) return 'audio';
  if (['pdf', 'docx', 'doc', 'txt', 'md', 'xlsx', 'xls'].includes(ext)) return 'document';
  return 'unknown';
}

function FilePreviewIcon({ fileName }: { fileName: string | null }) {
  const cat = getFileCategory(fileName);
  switch (cat) {
    case 'image': return <Image className="h-5 w-5 text-green-600" />;
    case 'audio': return <Mic className="h-5 w-5 text-cyan-600" />;
    case 'document': return <FileSpreadsheet className="h-5 w-5 text-blue-600" />;
    default: return <FileText className="h-5 w-5 text-muted-foreground" />;
  }
}

/** Evidence timeline node component */
function TimelineNode({ ev, isActive, onClick, index }: {
  ev: EvidenceItem;
  isActive: boolean;
  onClick: () => void;
  index: number;
}) {
  const Icon = TYPE_ICONS[ev.type] || FileText;
  const colorClass = TYPE_COLORS[ev.type] || 'bg-gray-100 text-gray-700';
  return (
    <button
      onClick={onClick}
      className={`relative flex items-start gap-3 w-full text-left p-2 rounded-lg transition-colors ${isActive ? 'bg-primary/5 ring-1 ring-primary/20' : 'hover:bg-accent/50'}`}
    >
      {/* Timeline line */}
      <div className="flex flex-col items-center">
        <div className={`flex items-center justify-center h-8 w-8 rounded-full shrink-0 ${colorClass}`}>
          <Icon className="h-4 w-4" />
        </div>
        {index >= 0 && <div className="w-px h-4 bg-border mt-1" />}
      </div>
      <div className="flex-1 min-w-0 pt-1">
        <p className="text-sm font-medium truncate">{ev.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className={`rounded-full px-1.5 py-0.5 text-[10px] ${colorClass}`}>
            {TYPE_LABELS[ev.type] || ev.type}
          </span>
          <span className="text-[10px] text-muted-foreground flex items-center gap-1">
            <Clock className="h-2.5 w-2.5" />
            {new Date(ev.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>
    </button>
  );
}

/** Chain analysis visual connection diagram */
function ChainVisualization({ result, evidenceList }: { result: ChainAnalysisResult; evidenceList: EvidenceItem[] }) {
  const score = result.completeness_score ?? 0;
  let scoreColor = 'text-red-600';
  let scoreBg = 'bg-red-50';
  if (score >= 70) { scoreColor = 'text-green-600'; scoreBg = 'bg-green-50'; }
  else if (score >= 40) { scoreColor = 'text-amber-600'; scoreBg = 'bg-amber-50'; }

  return (
    <div className="space-y-4">
      {/* Score and status */}
      <div className={`rounded-lg border p-4 ${scoreBg}`}>
        <div className="flex flex-col sm:flex-row items-center gap-4">
          {/* Score circle */}
          <div className="relative h-20 w-20">
            <svg className="h-20 w-20 -rotate-90" viewBox="0 0 80 80">
              <circle cx="40" cy="40" r="35" fill="none" stroke="hsl(var(--muted))" strokeWidth="6" />
              <circle cx="40" cy="40" r="35" fill="none" stroke="currentColor" strokeWidth="6"
                strokeDasharray={`${(score / 100) * 220} 220`} strokeLinecap="round"
                className={score >= 70 ? 'text-green-500' : score >= 40 ? 'text-amber-500' : 'text-red-500'} />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={`text-lg font-bold ${scoreColor}`}>{score}</span>
            </div>
          </div>
          <div className="text-center sm:text-left flex-1">
            <h3 className="font-semibold text-sm">证据链完整度评分</h3>
            <p className="text-xs text-muted-foreground mt-1">
              {result.chain_status}
              {result.missing_evidence && result.missing_evidence.length > 0 &&
                ` - 缺失 ${result.missing_evidence.length} 项关键证据`}
            </p>
          </div>
        </div>
      </div>

      {/* Evidence connection map */}
      <div className="rounded-lg border p-4">
        <h4 className="text-sm font-semibold mb-3">证据关联图</h4>
        <div className="flex flex-wrap gap-2">
          {evidenceList.map((ev, i) => {
            const Icon = TYPE_ICONS[ev.type] || FileText;
            return (
              <div key={ev.id} className="flex items-center gap-1">
                <div className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs ${TYPE_COLORS[ev.type] || 'bg-gray-100'}`}>
                  <Icon className="h-3 w-3" />
                  <span className="max-w-[100px] truncate">{ev.title}</span>
                </div>
                {i < evidenceList.length - 1 && (
                  <div className="w-4 h-px bg-border" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Missing evidence suggestions */}
      {result.missing_evidence && result.missing_evidence.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <h4 className="text-sm font-semibold text-amber-800 mb-2">建议补充证据</h4>
          <div className="space-y-2">
            {result.missing_evidence.map((m, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className={`rounded px-1.5 py-0.5 font-medium shrink-0 ${
                  m.urgency === 'high' ? 'bg-red-100 text-red-700' :
                  m.urgency === 'medium' ? 'bg-amber-100 text-amber-700' :
                  'bg-blue-100 text-blue-700'
                }`}>
                  {m.urgency === 'high' ? '紧急' : m.urgency === 'medium' ? '重要' : '建议'}
                </span>
                <div>
                  <span className="font-medium text-amber-900">{m.type}</span>
                  <span className="text-amber-700 ml-1">- {m.purpose}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Full report */}
      {result.credibility && (
        <CredibilityBar
          score={result.credibility.score}
          needsHumanReview={result.credibility.needs_human_review}
          reason={result.credibility.reason}
        />
      )}

      {result.timeline && result.timeline.length > 0 && (
        <div className="rounded-lg border p-4">
          <h4 className="text-sm font-semibold mb-2">事件时间线</h4>
          <ol className="space-y-2 text-sm">
            {result.timeline.map((node, i) => (
              <li key={i} className="flex gap-2">
                <span className="shrink-0 font-medium text-muted-foreground">{node.date || '—'}</span>
                <span>{node.event}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {result.chain_report && (
        <div className="rounded-lg border p-4">
          <h4 className="text-sm font-semibold mb-2">详细分析报告</h4>
          <div className="text-sm whitespace-pre-wrap max-h-80 overflow-y-auto">{result.chain_report}</div>
        </div>
      )}
    </div>
  );
}

export default function Evidence() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const intakeSession = loadIntakeSession();
  const { toast } = useToast();
  const [cases, setCases] = useState<CaseType[]>([]);
  const [selectedCase, setSelectedCase] = useState<number | null>(null);
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [uploading, setUploading] = useState<number | null>(null);
  const [ocrLive, setOcrLive] = useState<Record<number, { status: OcrStatus; message?: string | null }>>({});
  const [analyzing, setAnalyzing] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const quickUploadInputRef = useRef<HTMLInputElement>(null);
  const [uploadTarget, setUploadTarget] = useState<number | null>(null);
  const [quickUploading, setQuickUploading] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number; failed: number } | null>(null);

  const MAX_BATCH_FILES = 20;
  const [chainResult, setChainResult] = useState<ChainAnalysisResult | null>(null);
  const [chainCachedAt, setChainCachedAt] = useState<string | null>(null);
  const [analyzingChain, setAnalyzingChain] = useState(false);
  const [crossExamId, setCrossExamId] = useState<number | null>(null);
  const [crossExamText, setCrossExamText] = useState<Record<number, string>>({});
  const [casesLoading, setCasesLoading] = useState(true);
  const [error, setError] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'timeline'>('list');
  const [readiness, setReadiness] = useState<CaseReadinessSummary | null>(null);
  const [readinessLoading, setReadinessLoading] = useState(false);

  // Drag-and-drop state for the upload zone
  const [isDragOver, setIsDragOver] = useState(false);
  const [dropTarget, setDropTarget] = useState<number | null>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const [form, setForm] = useState({ case_id: 0, type: 'documentary', title: '', tags: '' });

  // Confirmation dialog state (replaces browser confirm())
  const [confirmDialog, setConfirmDialog] = useState<{ message: string; onConfirm: () => void } | null>(null);

  // Memoized evidence filtering: sorted by date for timeline view
  const sortedByDate = useMemo(() =>
    [...evidenceList].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()),
    [evidenceList]
  );

  // Memoized evidence type summary counts
  const evidenceTypeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const ev of evidenceList) {
      counts[ev.type] = (counts[ev.type] || 0) + 1;
    }
    return counts;
  }, [evidenceList]);

  useEffect(() => {
    caseApi.list().then(setCases).catch(() => setError('加载案件列表失败')).finally(() => setCasesLoading(false));
  }, []);

  useEffect(() => {
    const fromUrl = resolveCaseIdFromUrl(searchParams);
    if (fromUrl && cases.some((c) => c.id === fromUrl)) {
      setSelectedCase(fromUrl);
    }
  }, [searchParams, cases]);

  useEffect(() => {
    if (casesLoading || selectedCase != null || cases.length === 0) return;
    const fromActive = getActiveCaseId();
    if (fromActive && cases.some((c) => c.id === fromActive)) {
      setSelectedCase(fromActive);
      return;
    }
    const fromIntake = intakeSession?.createdCaseId;
    if (fromIntake && cases.some((c) => c.id === fromIntake)) {
      setSelectedCase(fromIntake);
      return;
    }
    if (cases.length === 1) setSelectedCase(cases[0].id);
  }, [cases, casesLoading, selectedCase, intakeSession?.createdCaseId]);

  useEffect(() => {
    if (selectedCase) setActiveCaseId(selectedCase);
  }, [selectedCase]);

  useEffect(() => subscribeActiveCase(() => {
    const id = getActiveCaseId();
    if (id && cases.some((c) => c.id === id)) setSelectedCase(id);
  }), [cases]);

  const selectedCaseTitle = useMemo(
    () => cases.find((c) => c.id === selectedCase)?.title,
    [cases, selectedCase],
  );

  const handleCaseSelect = useCallback((value: string) => {
    const id = value ? Number(value) : null;
    setSelectedCase(Number.isFinite(id) && id! > 0 ? id : null);
    if (id) setActiveCaseId(id);
  }, []);

  const intakeChecklistFromUrl = searchParams.get('checklist')?.split('|').filter(Boolean);
  const intakeChecklist =
    intakeChecklistFromUrl?.length
      ? intakeChecklistFromUrl
      : intakeSession?.evidenceChecklist;

  useEffect(() => {
    if (selectedCase) loadEvidence();
  }, [selectedCase]);

  const loadReadiness = useCallback(async (chainScore?: number) => {
    if (!selectedCase) {
      setReadiness(null);
      return;
    }
    setReadinessLoading(true);
    try {
      const data = await caseApi.getReadiness(selectedCase, {
        chainScore: chainScore != null ? chainScore : undefined,
      });
      setReadiness(data);
    } catch {
      setReadiness(null);
    } finally {
      setReadinessLoading(false);
    }
  }, [selectedCase]);

  useEffect(() => {
    if (!selectedCase) {
      setReadiness(null);
      setChainResult(null);
      setChainCachedAt(null);
      return;
    }
    const cached = loadChainAnalysis(selectedCase);
    if (cached) {
      setChainResult(cached);
      setChainCachedAt(cached.savedAt);
    } else {
      setChainResult(null);
      setChainCachedAt(null);
    }
    const chainScore =
      typeof cached?.completeness_score === 'number' ? cached.completeness_score : undefined;
    void loadReadiness(chainScore);
  }, [selectedCase, loadReadiness]);

  useEffect(() => {
    if (!selectedCase) return;
    const onActive = () => {
      const id = getActiveCaseId();
      if (id === selectedCase) {
        const cached = loadChainAnalysis(selectedCase);
        const chainScore =
          typeof cached?.completeness_score === 'number' ? cached.completeness_score : undefined;
        void loadReadiness(chainScore);
      }
    };
    return subscribeActiveCase(onActive);
  }, [selectedCase, loadReadiness]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showCreate) {
        setShowCreate(false);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [showCreate]);

  const loadEvidence = useCallback(async () => {
    if (!selectedCase) return;
    setLoading(true);
    try {
      const data = await evidenceApi.list(selectedCase);
      setEvidenceList(data);
    } catch {
      setError('加载证据列表失败');
    } finally { setLoading(false); }
  }, [selectedCase]);

  const notifyUploadResult = useCallback((item: EvidenceItem, fileLabel: string) => {
    if (item.vault_archived === false) {
      toast({
        type: 'warning',
        title: '已上传证据',
        description: '材料库容量不足，未同步副本到材料库',
      });
    }
    if (item.ocr_status === 'success') {
      toast({ type: 'success', title: `${fileLabel}上传成功`, description: item.ocr_message ?? '文字识别完成' });
    } else if (item.ocr_status === 'failed') {
      toast({ type: 'error', title: '文字识别失败', description: '请上传更清晰的文件后重试' });
    } else {
      toast({ type: 'success', title: `${fileLabel}上传成功`, description: '已同步到本案材料库' });
    }
  }, [toast]);

  const uploadFileToEvidence = useCallback(async (evidenceId: number, file: File) => {
    setUploading(evidenceId);
    setOcrLive((prev) => ({ ...prev, [evidenceId]: { status: 'processing', message: '正在识别文字…' } }));
    try {
      const item = await evidenceApi.upload(evidenceId, file);
      setOcrLive((prev) => ({
        ...prev,
        [evidenceId]: { status: item.ocr_status ?? 'pending', message: item.ocr_message },
      }));
      await loadEvidence();
      void loadReadiness();
      notifyUploadResult(item, file.name);
    } catch (err: unknown) {
      const msg = err instanceof AxiosError ? String(err.response?.data?.detail || err.message) : (err instanceof Error ? err.message : '上传失败');
      setOcrLive((prev) => ({ ...prev, [evidenceId]: { status: 'failed', message: msg } }));
      setError(msg);
      toast({ type: 'error', title: '上传失败', description: msg });
    } finally {
      setUploading(null);
      setDropTarget(null);
    }
  }, [loadEvidence, loadReadiness, notifyUploadResult, toast]);

  const batchQuickUploadFiles = useCallback(async (fileList: FileList | File[]) => {
    if (!selectedCase) {
      toast({ type: 'warning', title: '请先选择要绑定的案件' });
      return;
    }
    const files = Array.from(fileList).slice(0, MAX_BATCH_FILES);
    if (files.length === 0) return;
    if (fileList.length > MAX_BATCH_FILES) {
      toast({
        type: 'warning',
        title: `单次最多上传 ${MAX_BATCH_FILES} 个文件`,
        description: '已自动截取前 20 个',
      });
    }

    setQuickUploading(true);
    setBatchProgress({ current: 0, total: files.length, failed: 0 });
    let failed = 0;
    let lastItem: EvidenceItem | null = null;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setBatchProgress({ current: i + 1, total: files.length, failed });
      try {
        lastItem = await evidenceApi.quickUpload(selectedCase, file, {
          title: titleFromFileName(file.name),
          evidence_type: inferEvidenceType(file.name),
        });
      } catch (err: unknown) {
        failed += 1;
        const msg = err instanceof AxiosError
          ? String(err.response?.data?.detail || err.message)
          : (err instanceof Error ? err.message : '上传失败');
        setError(`${file.name}: ${msg}`);
      }
    }

    await loadEvidence();
    void loadReadiness();
    const ok = files.length - failed;
    if (ok > 0) {
      if (failed === 0) {
        toast({
          type: 'success',
          title: `已添加 ${ok} 条证据`,
          description: '每个文件对应一条证据，已同步到本案材料库',
        });
      } else {
        toast({
          type: 'warning',
          title: `完成 ${ok}/${files.length} 个`,
          description: `${failed} 个文件上传失败，请检查格式或大小`,
        });
      }
      if (lastItem && ok === 1) notifyUploadResult(lastItem, files[files.length - 1].name);
    } else {
      toast({ type: 'error', title: '批量上传失败', description: '请检查文件格式与网络' });
    }

    setQuickUploading(false);
    setBatchProgress(null);
    if (quickUploadInputRef.current) quickUploadInputRef.current.value = '';
  }, [selectedCase, loadEvidence, loadReadiness, notifyUploadResult, toast]);

  const handleCreate = useCallback(async () => {
    if (!selectedCase) {
      toast({ type: 'warning', title: '请先选择案件' });
      return;
    }
    if (!VALID_EVIDENCE_TYPES.includes(form.type as (typeof VALID_EVIDENCE_TYPES)[number])) {
      toast({ type: 'error', title: '无效的证据类型' });
      return;
    }
    try {
      await evidenceApi.create({ ...form, case_id: selectedCase, tags: form.tags ? form.tags.split(',').map(t => t.trim()) : undefined });
      setShowCreate(false);
      setForm({ case_id: 0, type: 'documentary', title: '', tags: '' });
      loadEvidence();
      toast({ type: 'success', title: '证据已创建' });
    } catch (e) {
      setError('创建失败');
      toast({ type: 'error', title: '创建失败' });
    }
  }, [form, selectedCase, loadEvidence, toast]);

  const handleUpload = useCallback(async (evidenceId: number) => {
    fileInputRef.current?.click();
    setUploadTarget(evidenceId);
  }, []);

  const onFileSelected = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !uploadTarget) return;
    await uploadFileToEvidence(uploadTarget, file);
    setUploadTarget(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, [uploadTarget, uploadFileToEvidence]);

  const onQuickFileSelected = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
    await batchQuickUploadFiles(files);
  }, [batchQuickUploadFiles]);

  /** Handle drag-and-drop file onto a specific evidence item */
  const handleDropOnEvidence = useCallback(async (evidenceId: number, file: File) => {
    await uploadFileToEvidence(evidenceId, file);
  }, [uploadFileToEvidence]);

  const handleDragOverEvidence = useCallback((e: React.DragEvent, evidenceId: number) => {
    e.preventDefault();
    e.stopPropagation();
    setDropTarget(evidenceId);
  }, []);

  const handleDragLeaveEvidence = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDropTarget(null);
  }, []);

  const handleDropOnZone = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (!files?.length) return;
    if (!selectedCase) {
      toast({ type: 'warning', title: '请先选择要绑定的案件' });
      return;
    }
    if (uploadTarget && files.length === 1) {
      await handleDropOnEvidence(uploadTarget, files[0]);
      return;
    }
    await batchQuickUploadFiles(files);
  }, [selectedCase, uploadTarget, handleDropOnEvidence, batchQuickUploadFiles, toast]);

  const handleAnalyze = useCallback(async (id: number) => {
    setAnalyzing(id);
    try {
      await evidenceApi.analyze(id);
      loadEvidence();
      const item = evidenceList.find((e) => e.id === id);
      addToolHistory({
        kind: 'evidence',
        title: item?.title || `证据 #${id}`,
        route: '/evidence',
        query: String(id),
      });
      toast({ type: 'success', title: 'AI分析完成' });
    } catch (e) {
      setError('分析失败');
      toast({ type: 'error', title: 'AI分析失败' });
    }
    finally { setAnalyzing(null); }
  }, [loadEvidence, toast, evidenceList]);

  const handleDelete = useCallback((id: number) => {
    setConfirmDialog({ message: '确定删除此证据？', onConfirm: async () => {
      try {
        await evidenceApi.delete(id);
        loadEvidence();
        toast({ type: 'success', title: '证据已删除' });
      } catch (e) {
        setError('删除失败');
        toast({ type: 'error', title: '删除失败' });
      }
      setConfirmDialog(null);
    }});
  }, [loadEvidence, toast]);

  const handleChainAnalysis = useCallback(async () => {
    if (!selectedCase) return;
    setAnalyzingChain(true);
    try {
      const result = await evidenceChainApi.analyzeChain(selectedCase);
      setChainResult(result);
      saveChainAnalysis(selectedCase, result);
      setChainCachedAt(new Date().toISOString());
      const chainScore =
        typeof result.completeness_score === 'number' ? result.completeness_score : undefined;
      void loadReadiness(chainScore);
      toast({
        type: 'success',
        title: '证据链分析完成',
        description: `证据链 ${result.completeness_score ?? '-'} 分，已同步到材料完整度评估`,
      });
    } catch (e: unknown) {
      const msg = e instanceof AxiosError ? (e.response?.data?.detail || '证据链分析失败') : '证据链分析失败';
      setError(msg);
      toast({ type: 'error', title: '证据链分析失败', description: msg });
    } finally { setAnalyzingChain(false); }
  }, [selectedCase, loadReadiness, toast]);

  const handleCrossExamination = useCallback(async (id: number) => {
    setCrossExamId(id);
    try {
      const result = await evidenceChainApi.crossExamination(id);
      setCrossExamText(prev => ({ ...prev, [id]: result.cross_examination }));
      toast({ type: 'success', title: '质证意见已生成' });
    } catch (e: unknown) {
      const msg = e instanceof AxiosError ? (e.response?.data?.detail || '质证意见生成失败') : '质证意见生成失败';
      setError(msg);
      toast({ type: 'error', title: '质证意见生成失败' });
    } finally { setCrossExamId(null); }
  }, [toast]);

  /** Export evidence list as CSV */
  const handleExportEvidenceList = useCallback(() => {
    if (evidenceList.length === 0) return;
    const headers = ['编号', '名称', '类型', '标签', '已上传文件', '创建日期'];
    const rows = evidenceList.map((ev, i) => [
      i + 1,
      ev.title,
      TYPE_LABELS[ev.type] || ev.type,
      ev.tags?.join('; ') || '',
      ev.has_file ? '是' : '否',
      new Date(ev.created_at).toLocaleDateString(),
    ]);
    const csv = [headers, ...rows].map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
    const bom = '﻿';
    const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `证据清单_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast({ type: 'success', title: '证据清单已导出' });
  }, [evidenceList, toast]);

  const renderBatchUploadZone = (compact: boolean) => (
    <div
      ref={compact ? undefined : dropZoneRef}
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={(e) => { e.preventDefault(); setIsDragOver(false); }}
      onDrop={handleDropOnZone}
      className={`rounded-xl border-2 border-dashed text-center transition-all ${
        compact ? 'p-4 sm:p-5' : 'p-8 sm:p-12'
      } ${
        isDragOver ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-muted-foreground/25 hover:border-primary/50'
      }`}
    >
      <Upload className={`mx-auto mb-3 ${compact ? 'h-8 w-8' : 'h-12 w-12'} ${isDragOver ? 'text-primary' : 'text-muted-foreground/40'}`} />
      <h3 className={`font-semibold mb-1 ${compact ? 'text-sm' : 'text-lg'}`}>
        {isDragOver ? '松开以上传' : compact ? '继续添加证据文件' : '拖拽文件到此处上传'}
      </h3>
      <p className={`text-muted-foreground mb-3 ${compact ? 'text-xs' : 'text-sm'}`}>
        支持一次选择或拖入多个文件（最多 {MAX_BATCH_FILES} 个），每个文件生成一条证据并归入材料库
      </p>
      {batchProgress && (
        <p className="text-xs text-primary mb-2">
          正在上传 {batchProgress.current}/{batchProgress.total}
          {batchProgress.failed > 0 ? `（${batchProgress.failed} 个失败）` : ''}
        </p>
      )}
      <button
        type="button"
        disabled={quickUploading}
        onClick={(e) => { e.stopPropagation(); quickUploadInputRef.current?.click(); }}
        className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {quickUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
        {quickUploading ? '上传中…' : '选择文件（可多选）'}
      </button>
    </div>
  );

  return (
    <div className="max-w-5xl mx-auto space-y-6 px-4 sm:px-0">
      <input type="file" ref={fileInputRef} className="hidden" onChange={onFileSelected}
        accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.xls,.png,.jpg,.jpeg,.gif,.webp,.bmp,.tiff,.mp3,.wav,.m4a,.ogg,.flac,.aac,.wma" />
      <input type="file" ref={quickUploadInputRef} className="hidden" multiple onChange={onQuickFileSelected}
        accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.xls,.png,.jpg,.jpeg,.gif,.webp,.bmp,.tiff,.mp3,.wav,.m4a,.ogg,.flac,.aac,.wma" />

      {selectedCase ? (
        <CaseReadinessHint
          readiness={readiness}
          loading={readinessLoading}
          variant="evidence"
        />
      ) : intakeChecklist?.length ? (
        <div className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm">
          <p className="font-medium">建议收集的证据</p>
          <p className="mt-1 text-xs text-muted-foreground">{intakeChecklist.join(' · ')}</p>
        </div>
      ) : null}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Upload className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">整理证据</h1>
        </div>
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 max-w-md">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
            <button onClick={() => setError('')} className="ml-auto"><X className="h-4 w-4" /></button>
          </div>
        )}
        {selectedCase && (
          <div className="flex gap-2 flex-wrap">
            <button
              type="button"
              disabled={quickUploading}
              onClick={() => quickUploadInputRef.current?.click()}
              className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {quickUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              批量上传
            </button>
            <button onClick={() => { setForm({ case_id: selectedCase, type: 'documentary', title: '', tags: '' }); setShowCreate(true); }}
              className="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent">
              <Plus className="h-4 w-4" /> 手动添加
            </button>
            {evidenceList.length > 0 && (
              <>
                <button onClick={handleChainAnalysis} disabled={analyzingChain}
                  className="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50">
                  {analyzingChain ? <Loader2 className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4" />}
                  证据链分析
                </button>
                <button onClick={handleExportEvidenceList}
                  className="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent">
                  <Download className="h-4 w-4" /> 导出清单
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Case selector */}
      <div className="flex items-center gap-3 flex-wrap">
        <label className="text-sm font-medium shrink-0">绑定案件：</label>
        {casesLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : cases.length === 0 ? (
          <div className="flex items-center gap-2 flex-wrap text-sm">
            <span className="text-muted-foreground">暂无案件，请先创建</span>
            <button
              type="button"
              onClick={() => navigate('/cases?worker=1')}
              className="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-accent"
            >
              去创建案件
            </button>
          </div>
        ) : (
        <select
          className="min-w-[12rem] max-w-full rounded-md border bg-background px-3 py-2 text-sm"
          value={selectedCase ?? ''}
          onChange={(e) => handleCaseSelect(e.target.value)}
        >
          <option value="">请选择案件</option>
          {cases.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
        )}
        {selectedCaseTitle && (
          <span className="text-xs text-muted-foreground">
            当前：<span className="font-medium text-foreground">{selectedCaseTitle}</span>
            <span className="mx-1">·</span>
            <Link to={`/vault?caseId=${selectedCase}`} className="text-primary hover:underline">
              查看本案材料库
            </Link>
          </span>
        )}
        {selectedCase && evidenceList.length > 1 && (
          <div className="flex gap-1 border rounded-md p-0.5">
            <button onClick={() => setViewMode('list')}
              className={`px-3 py-1 text-xs rounded ${viewMode === 'list' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'}`}>
              列表
            </button>
            <button onClick={() => setViewMode('timeline')}
              className={`px-3 py-1 text-xs rounded ${viewMode === 'timeline' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'}`}>
              时间线
            </button>
          </div>
        )}
      </div>

      {!selectedCase ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          请先选择一个案件
        </div>
      ) : loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>
      ) : (
        <div className="space-y-4">
          {renderBatchUploadZone(evidenceList.length > 0)}
          {evidenceList.length > 0 && (
            <p className="text-xs text-muted-foreground">
              本案共 {evidenceList.length} 条证据 · 每条证据对应一个文件，可继续批量添加
            </p>
          )}
          {evidenceList.length === 0 ? (
            <p className="text-center text-sm text-muted-foreground">或点击「手动添加」先填写名称再上传</p>
          ) : viewMode === 'timeline' ? (
        /* Timeline view */
        <div className="rounded-lg border p-4">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-muted-foreground">证据时间线（按创建日期排序）</h3>
          </div>
          <div className="space-y-0">
            {sortedByDate.map((ev, i) => (
              <TimelineNode
                key={ev.id}
                ev={ev}
                index={i}
                isActive={expandedId === ev.id}
                onClick={() => setExpandedId(expandedId === ev.id ? null : ev.id)}
              />
            ))}
          </div>
          {/* Expanded detail for timeline */}
          {expandedId && (() => {
            const ev = evidenceList.find(e => e.id === expandedId);
            if (!ev) return null;
            return (
              <div className="border-t mt-4 p-4 space-y-3">
                {/* File preview */}
                {ev.has_file && (
                  <div className="flex items-center gap-2 text-sm">
                    <FilePreviewIcon fileName={ev.file_path} />
                    <span className="text-muted-foreground">{ev.file_path || '已上传文件'}</span>
                    <button onClick={() => evidenceApi.download(ev.id)} className="rounded-md border px-2 py-1 text-xs hover:bg-accent">
                      <Download className="h-3 w-3" />
                    </button>
                  </div>
                )}
                {ev.has_file && (
                  <OcrStatusBadge
                    status={ocrLive[ev.id]?.status ?? ev.ocr_status}
                    message={ocrLive[ev.id]?.message ?? ev.ocr_message}
                  />
                )}
                {ev.ocr_text && ev.ocr_status === 'success' && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">提取文字</h4>
                    <pre className="rounded-md bg-muted p-3 text-xs whitespace-pre-wrap max-h-60 overflow-y-auto">{ev.ocr_text}</pre>
                  </div>
                )}
                {ev.analysis && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">AI分析</h4>
                    <div className="rounded-md bg-blue-50 p-3 text-sm whitespace-pre-wrap max-h-80 overflow-y-auto">{ev.analysis}</div>
                  </div>
                )}
              </div>
            );
          })()}
        </div>
          ) : (
        /* List view with drag-drop per item */
        <div className="space-y-3">
          {evidenceList.map(ev => {
            const TypeIcon = TYPE_ICONS[ev.type] || FileText;
            const isDropTarget = dropTarget === ev.id;
            return (
              <div key={ev.id}
                className={`rounded-lg border bg-card transition-all ${isDropTarget ? 'ring-2 ring-primary bg-primary/5' : ''}`}
                onDragOver={(e) => handleDragOverEvidence(e, ev.id)}
                onDragLeave={handleDragLeaveEvidence}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDropTarget(null);
                  const file = e.dataTransfer.files?.[0];
                  if (file) handleDropOnEvidence(ev.id, file);
                }}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 cursor-pointer hover:bg-accent/50 gap-2"
                  onClick={() => setExpandedId(expandedId === ev.id ? null : ev.id)}>
                  <div className="flex items-center gap-3 min-w-0">
                    {expandedId === ev.id ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
                    {/* Type-specific icon */}
                    <TypeIcon className={`h-5 w-5 shrink-0 ${TYPE_COLORS[ev.type]?.split(' ')[1] || 'text-muted-foreground'}`} />
                    {/* File preview icon if file uploaded */}
                    {ev.has_file && <FilePreviewIcon fileName={ev.file_path} />}
                    <div className="min-w-0">
                      <span className="font-medium">{ev.title}</span>
                      <span className={`ml-2 rounded-full px-2 py-0.5 text-xs ${TYPE_COLORS[ev.type] || 'bg-gray-100'}`}>
                        {TYPE_LABELS[ev.type] || ev.type}
                      </span>
                      {ev.has_file && <span className="ml-2 text-xs text-green-600">已上传</span>}
                      {(ev.has_file || uploading === ev.id || ocrLive[ev.id]) && (
                        <span className="ml-2" onClick={(e) => e.stopPropagation()}>
                          <OcrStatusBadge
                            compact
                            status={
                              uploading === ev.id || ocrLive[ev.id]?.status === 'processing'
                                ? 'processing'
                                : (ocrLive[ev.id]?.status ?? ev.ocr_status ?? 'pending')
                            }
                            message={ocrLive[ev.id]?.message ?? ev.ocr_message}
                          />
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => handleUpload(ev.id)}
                      disabled={uploading === ev.id}
                      className="rounded-md border px-2 py-1 text-xs hover:bg-accent disabled:opacity-50"
                    >
                      {uploading === ev.id ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : ev.has_file ? (
                        '更换文件'
                      ) : (
                        '上传文件'
                      )}
                    </button>
                    {ev.has_file && (
                      <>
                        <button onClick={() => evidenceApi.download(ev.id)} className="rounded-md border px-2 py-1 text-xs hover:bg-accent">
                          <Download className="h-3 w-3" />
                        </button>
                        <button onClick={() => handleAnalyze(ev.id)} disabled={analyzing === ev.id}
                          className="rounded-md border px-2 py-1 text-xs hover:bg-accent disabled:opacity-50 flex items-center gap-1">
                          {analyzing === ev.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
                          AI分析
                        </button>
                      </>
                    )}
                    <button onClick={() => handleDelete(ev.id)} aria-label="删除证据" className="rounded-md border px-2 py-1 text-xs text-destructive hover:bg-destructive/10">
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>

                {/* Drop hint for items without files */}
                {!ev.has_file && isDropTarget && (
                  <div className="px-4 pb-2">
                    <div className="rounded-md border-2 border-dashed border-primary/40 bg-primary/5 p-3 text-center text-xs text-primary">
                      松开以上传文件到此证据
                    </div>
                  </div>
                )}

                {expandedId === ev.id && (
                  <div className="border-t p-4 space-y-3">
                    {/* File preview section */}
                    {ev.has_file && ev.file_path && (
                      <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/30">
                        <FilePreviewIcon fileName={ev.file_path} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{ev.file_path.split('/').pop()}</p>
                          <p className="text-xs text-muted-foreground">
                            {getFileCategory(ev.file_path) === 'image' ? '图片文件' :
                             getFileCategory(ev.file_path) === 'audio' ? '音频文件' : '文档文件'}
                          </p>
                        </div>
                        <button onClick={() => evidenceApi.download(ev.id)}
                          className="rounded-md border px-3 py-1.5 text-xs hover:bg-accent flex items-center gap-1">
                          <Download className="h-3 w-3" /> 下载
                        </button>
                      </div>
                    )}
                    {ev.has_file && (
                      <OcrStatusBadge
                        status={ocrLive[ev.id]?.status ?? ev.ocr_status}
                        message={ocrLive[ev.id]?.message ?? ev.ocr_message}
                      />
                    )}
                    {ev.ocr_text && (ev.ocr_status === 'success' || ocrLive[ev.id]?.status === 'success') && (
                      <div>
                        <h4 className="text-sm font-medium mb-1">提取文字</h4>
                        <pre className="rounded-md bg-muted p-3 text-xs whitespace-pre-wrap max-h-60 overflow-y-auto">{ev.ocr_text}</pre>
                      </div>
                    )}
                    {ev.analysis && (
                      <div>
                        <h4 className="text-sm font-medium mb-1">AI分析</h4>
                        <div className="rounded-md bg-blue-50 p-3 text-sm whitespace-pre-wrap max-h-80 overflow-y-auto">{ev.analysis}</div>
                      </div>
                    )}
                    {ev.ocr_text && ev.ocr_status === 'success' && (
                      <button onClick={() => handleCrossExamination(ev.id)} disabled={crossExamId === ev.id}
                        className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-xs hover:bg-accent disabled:opacity-50">
                        {crossExamId === ev.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <MessageSquare className="h-3 w-3" />}
                        生成质证意见
                      </button>
                    )}
                    {crossExamText[ev.id] && (
                      <div>
                        <h4 className="text-sm font-medium mb-1">质证意见</h4>
                        <div className="rounded-md bg-amber-50 p-3 text-sm whitespace-pre-wrap max-h-80 overflow-y-auto">{crossExamText[ev.id]}</div>
                      </div>
                    )}
                    {ev.tags && ev.tags.length > 0 && (
                      <div className="flex gap-1 flex-wrap">
                        {ev.tags.map((t, i) => <span key={i} className="rounded-full bg-muted px-2 py-0.5 text-xs">{t}</span>)}
                      </div>
                    )}
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      创建于 {new Date(ev.created_at).toLocaleString()}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
          )}
        </div>
      )}

      {/* Chain Analysis Result */}
      {chainResult && (
        <div className="rounded-lg border border-accent/25 bg-card p-4 space-y-3 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="font-semibold">证据链分析</h3>
              {chainCachedAt && (
                <p className="text-[11px] text-muted-foreground">
                  {analyzingChain
                    ? '正在重新分析…'
                    : `已恢复上次分析 · ${new Date(chainCachedAt).toLocaleString('zh-CN')}`}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => {
                setChainResult(null);
                setChainCachedAt(null);
                if (selectedCase) clearChainAnalysis(selectedCase);
              }}
              className="cursor-pointer text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              关闭并清除缓存
            </button>
          </div>
          <ChainVisualization result={chainResult} evidenceList={evidenceList} />
        </div>
      )}

      {/* Create Evidence Modal - responsive */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-start sm:items-center justify-center bg-black/50 p-4 overflow-y-auto" onClick={() => setShowCreate(false)}>
          <div className="w-full max-w-md rounded-lg bg-background p-4 sm:p-6 shadow-xl my-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">添加证据</h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">证据名称</label>
                <input className="mt-1 w-full rounded-md border bg-transparent px-3 py-2 text-sm"
                  value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="如：合同原件" />
              </div>
              <div>
                <label className="text-sm font-medium">证据类型</label>
                <select className="mt-1 w-full rounded-md border bg-transparent px-3 py-2 text-sm"
                  value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                  {VALID_EVIDENCE_TYPES.map((k) => {
                    const v = TYPE_LABELS[k];
                    return <option key={k} value={k}>{v}</option>;
                  })}
                </select>
                {/* Type icon preview */}
                <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                  {(() => { const Icon = TYPE_ICONS[form.type] || FileText; return <Icon className="h-4 w-4" />; })()}
                  <span>{TYPE_LABELS[form.type]}类型证据</span>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium">标签（逗号分隔）</label>
                <input className="mt-1 w-full rounded-md border bg-transparent px-3 py-2 text-sm"
                  value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="如：合同,原件,甲方" onKeyDown={(e) => e.key === 'Enter' && handleCreate()} />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => setShowCreate(false)} className="rounded-md border px-4 py-2 text-sm hover:bg-accent">取消</button>
              <button onClick={handleCreate} className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">创建</button>
            </div>
          </div>
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
