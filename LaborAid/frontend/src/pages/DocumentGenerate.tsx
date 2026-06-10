import React, { useState, useEffect, useCallback, useMemo, memo, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getChannel, getChannelScenario } from '@/lib/channels';
import {
  FileText,
  Sparkles,
  Download,
  Edit3,
  Eye,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ChevronDown,
  ChevronRight,
  Plus,
  X,
  RotateCcw,
  Shield,
  Upload,
  Save,
  Clock,
  RefreshCw,
  Search,
  Layers,
  History,
  Trash2,
  Bot,
} from 'lucide-react';
import axios, { AxiosError } from 'axios';
import {
  documentApi,
  caseApi,
  researchApi,
  templateApi,
  type CaseReadinessSummary,
  type DocPipelineProgressEvent,
} from '@/lib/api';
import CaseReadinessHint from '@/components/cases/CaseReadinessHint';
import { FillRateBanner } from '@/components/FillRateBanner';
import { useToast } from '@/lib/toast';
import type { Document, Case, CaseCreate, ResearchReport, Template } from '@/lib/api';
import { cn } from '@/lib/utils';
import { autoSave, loadAutoSave, clearAutoSave, STORAGE_KEYS } from '@/lib/storage';
import { withCaseTitleDatePrefix } from '@/lib/case-title';
import { loadIntakeSession } from '@/lib/intake-session';
import { getActiveCaseId } from '@/lib/active-case';
import { announceToScreenReader } from '@/lib/accessibility';
import { addToolHistory, removeToolHistoryForDocument } from '@/lib/tool-history';
import { downloadDocumentFile } from '@/lib/document-download';
import CourtDocumentPreview from '@/components/documents/CourtDocumentPreview';
import DocRecommendationPanel from '@/components/documents/DocRecommendationPanel';
import {
  buildLocalDocRecommendations,
  type DocRecommendationsResult,
} from '@/lib/doc-recommendations';
import {
  BUNDLE_PRESETS,
  DOC_TYPES,
  WORKER_DOC_TYPES,
  docTypeLabel,
  normalizeDocType,
} from '@/config/doc-types';

const MAX_CASE_FACT_CHARS = 4000;

const AGENT_PIPELINE_ORDER = ['prepare', 'research', 'generate', 'review', 'quality'] as const;

const AGENT_PIPELINE_LABELS: Record<string, string> = {
  prepare: '准备案情与材料',
  research: '检索法规与争点',
  generate: 'AI 生成文书',
  review: 'AI 审校润色',
  quality: '质量核查',
};

/** Count Chinese chars + alphanumeric tokens as "words". */
function countWords(text: string): { chars: number; words: number } {
  const chars = text.replace(/\s+/g, '').length;
  const tokens = text.match(/[一-鿿]|[A-Za-z0-9]+/g) || [];
  return { chars, words: tokens.length };
}

function trimToCharLimit(text: string, limit: number): string {
  if (!text) return '';
  let count = 0;
  for (let i = 0; i < text.length; i += 1) {
    if (!/\s/.test(text[i]!)) count += 1;
    if (count > limit) return text.slice(0, i).trimEnd();
  }
  return text;
}

interface Draft {
  id: string;
  docType: string;
  caseFacts: string;
  extraInstructions: string;
  selectedCaseId: string;
  selectedReportIds: number[];
  savedAt: string;
}

const DRAFTS_KEY = STORAGE_KEYS.docDrafts;

function loadDrafts(): Draft[] {
  try {
    return JSON.parse(localStorage.getItem(DRAFTS_KEY) || '[]');
  } catch { return []; }
}

function saveDrafts(drafts: Draft[]) {
  localStorage.setItem(DRAFTS_KEY, JSON.stringify(drafts));
}

/** Memoized document type selector component */
const DocumentTypeSelector = memo(function DocumentTypeSelector({
  value,
  onChange,
  disabled,
  selectedLabel,
  selectedDesc,
  types = DOC_TYPES,
}: {
  value: string;
  onChange: (val: string) => void;
  disabled: boolean;
  selectedLabel: string;
  selectedDesc: string;
  types?: typeof DOC_TYPES;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium">
        文书类型 <span className="text-red-500">*</span>
      </label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required
          disabled={disabled}
          className="w-full appearance-none rounded-lg border border-input bg-background px-3.5 py-2.5 pr-8 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:opacity-50"
        >
          <option value="">请选择文书类型</option>
          {types.map((dt) => (
            <option key={dt.value} value={dt.value}>
              {dt.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      </div>
      {selectedDesc && (
        <p className="mt-1.5 text-xs text-muted-foreground flex items-center gap-1">
          <FileText className="h-3 w-3" />
          {selectedDesc}
        </p>
      )}
    </div>
  );
});

export default function DocumentGenerate() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const workerMode =
    searchParams.get('worker') === '1' ||
    searchParams.get('from') === 'intake' ||
    searchParams.get('from') === 'guidance' ||
    !!searchParams.get('channel');
  const visibleDocTypes = useMemo(() => (workerMode ? WORKER_DOC_TYPES : DOC_TYPES), [workerMode]);

  const visibleBundlePresets = useMemo(
    () => BUNDLE_PRESETS.filter((p) => (workerMode ? p.workerOnly === true : !p.workerOnly)),
    [workerMode],
  );
  const { toast } = useToast();

  // Active mode: single or bundle
  const [mode, setMode] = useState<'single' | 'bundle'>('single');

  // Form state
  const [docType, setDocType] = useState('');
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | ''>('');
  const [templates, setTemplates] = useState<Template[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [caseFacts, setCaseFacts] = useState('');
  const [extraInstructions, setExtraInstructions] = useState('');

  // Data state
  const [cases, setCases] = useState<Case[]>([]);
  const [generatedDoc, setGeneratedDoc] = useState<Document | null>(null);
  const [reviewResult, setReviewResult] = useState<string | null>(null);

  // UI state
  const [loading, setLoading] = useState(false);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyResult, setVerifyResult] = useState<any[] | null>(null);
  const [exportLoading, setExportLoading] = useState<string | null>(null);
  const [previewLoadingId, setPreviewLoadingId] = useState<number | null>(null);
  const [recentDocuments, setRecentDocuments] = useState<Document[]>([]);
  const autoWordDownloadedRef = useRef<number | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [editedTitle, setEditedTitle] = useState('');
  const [error, setError] = useState('');
  const [showNewCase, setShowNewCase] = useState(false);
  const [newCase, setNewCase] = useState<CaseCreate>({
    title: '',
    case_type: 'civil',
    description: '',
  });
  const [creatingCase, setCreatingCase] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [extractingFile, setExtractingFile] = useState(false);

  // 研究报告选择
  const [researchReports, setResearchReports] = useState<ResearchReport[]>([]);
  const [selectedReportIds, setSelectedReportIds] = useState<number[]>([]);
  const [showReportPicker, setShowReportPicker] = useState(false);
  const [reportSearch, setReportSearch] = useState('');

  // Progress steps
  const [progressStep, setProgressStep] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const progressSteps = [
    '正在分析案情描述...',
    '正在检索相关法律条文...',
    '正在匹配文书模板...',
    '正在生成法律文书...',
    '正在校验文书格式...',
  ];

  // Drafts
  const [drafts, setDrafts] = useState<Draft[]>(loadDrafts());
  const [showDrafts, setShowDrafts] = useState(false);

  // Document version history
  const [docVersions, setDocVersions] = useState<{ version: number; updated_at: string; title: string }[]>([]);

  // Bundle generation state
  const [bundleDocTypes, setBundleDocTypes] = useState<string[]>([]);
  const [bundleGenerating, setBundleGenerating] = useState(false);
  const [bundleResults, setBundleResults] = useState<Document[]>([]);
  const [bundleProgress, setBundleProgress] = useState({ current: 0, total: 0, currentLabel: '' });
  const [deletingDocId, setDeletingDocId] = useState<number | null>(null);
  const [caseReadiness, setCaseReadiness] = useState<CaseReadinessSummary | null>(null);
  const [readinessLoading, setReadinessLoading] = useState(false);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineSteps, setPipelineSteps] = useState<
    Record<string, 'pending' | 'running' | 'done' | 'skipped'>
  >({});
  const [lastPipelineHint, setLastPipelineHint] = useState<string | null>(null);
  const pipelineAbortRef = useRef<AbortController | null>(null);
  const [docRecommendations, setDocRecommendations] = useState<DocRecommendationsResult | null>(null);
  const [recommendationsLoading, setRecommendationsLoading] = useState(false);
  const [generatingDocType, setGeneratingDocType] = useState<string | null>(null);

  // Character / word counter
  const caseFactCharCount = useMemo(
    () => caseFacts.replace(/\s+/g, '').length,
    [caseFacts],
  );

  // Estimated remaining time
  const estimatedRemaining = useMemo(() => {
    if (progressStep === 0) return '约30-60秒';
    const stepsLeft = progressSteps.length - progressStep;
    const avgPerStep = elapsedSeconds / (progressStep || 1);
    const remaining = Math.round(avgPerStep * stepsLeft);
    if (remaining < 10) return '即将完成';
    return `约${remaining}秒`;
  }, [progressStep, elapsedSeconds, progressSteps.length]);

  // Filtered reports for searchable dropdown
  const filteredReports = useMemo(() => {
    if (!reportSearch.trim()) return researchReports;
    const q = reportSearch.toLowerCase();
    return researchReports.filter(r => r.query.toLowerCase().includes(q));
  }, [researchReports, reportSearch]);

  useEffect(() => {
    const caseId = selectedCaseId ? Number(selectedCaseId) : null;
    if (!caseId || !Number.isFinite(caseId)) {
      setCaseReadiness(null);
      return;
    }
    setReadinessLoading(true);
    caseApi
      .getReadiness(caseId)
      .then(setCaseReadiness)
      .catch(() => setCaseReadiness(null))
      .finally(() => setReadinessLoading(false));
  }, [selectedCaseId]);

  // 关联案件后自动聚合案情（含证据分析），替换被截断的预填
  useEffect(() => {
    const caseId = selectedCaseId ? Number(selectedCaseId) : null;
    if (!caseId || !Number.isFinite(caseId)) return;

    let cancelled = false;
    caseApi
      .getDocFacts(caseId)
      .then(({ case_facts }) => {
        if (cancelled || !case_facts?.trim()) return;
        setCaseFacts((prev) => {
          const trimmed = prev.trim();
          if (!trimmed) return trimToCharLimit(case_facts, MAX_CASE_FACT_CHARS);
          if (
            (trimmed.endsWith('...') || trimmed.length < case_facts.length * 0.6) &&
            case_facts.length > trimmed.length
          ) {
            return trimToCharLimit(case_facts, MAX_CASE_FACT_CHARS);
          }
          return prev;
        });
      })
      .catch(() => {
        const c = cases.find((item) => item.id === caseId);
        if (!c || cancelled) return;
        setCaseFacts((prev) => {
          if (prev.trim()) return prev;
          const base = [c.description, c.plaintiff && c.defendant ? `当事人：${c.plaintiff} 诉 ${c.defendant}` : '']
            .filter(Boolean)
            .join('\n');
          return base ? trimToCharLimit(base, MAX_CASE_FACT_CHARS) : prev;
        });
      });
    return () => {
      cancelled = true;
    };
  }, [selectedCaseId, cases]);

  useEffect(() => {
    const caseId = selectedCaseId ? Number(selectedCaseId) : null;
    if (!caseId || !Number.isFinite(caseId)) {
      setLastPipelineHint(null);
      return;
    }
    caseApi
      .getAgentSnapshot(caseId)
      .then((snap) => {
        const runs = snap.snapshot?.doc_pipeline_runs;
        if (!runs?.length) {
          setLastPipelineHint(null);
          return;
        }
        const last = runs[runs.length - 1];
        if (last.error) {
          setLastPipelineHint('上次助手流水线未完成，可重试');
          return;
        }
        const score = last.quality_check?.quality_score;
        const when = last.completed_at
          ? new Date(last.completed_at).toLocaleString()
          : '';
        setLastPipelineHint(
          `上次流水线${when ? `（${when}）` : ''}已生成文书${score != null ? `，质检 ${score} 分` : ''}`,
        );
      })
      .catch(() => setLastPipelineHint(null));
  }, [selectedCaseId]);

  const refreshRecentDocuments = useCallback(() => {
    documentApi
      .list({ limit: 8 })
      .then(setRecentDocuments)
      .catch(() => setRecentDocuments([]));
  }, []);

  const refreshDocRecommendations = useCallback(() => {
    const caseId = selectedCaseId ? Number(selectedCaseId) : null;
    if (!caseId || !Number.isFinite(caseId)) {
      const session = loadIntakeSession();
      if (caseFacts.trim()) {
        setDocRecommendations(buildLocalDocRecommendations(caseFacts, session));
      } else {
        setDocRecommendations(null);
      }
      return;
    }
    setRecommendationsLoading(true);
    caseApi
      .getDocRecommendations(caseId)
      .then((data) => setDocRecommendations(data))
      .catch(() => {
        const session = loadIntakeSession();
        setDocRecommendations(buildLocalDocRecommendations(caseFacts, session));
      })
      .finally(() => setRecommendationsLoading(false));
  }, [selectedCaseId, caseFacts]);

  useEffect(() => {
    const t = window.setTimeout(refreshDocRecommendations, caseFacts.trim() ? 400 : 0);
    return () => window.clearTimeout(t);
  }, [refreshDocRecommendations, caseFacts]);

  useEffect(() => {
    if (docType || !docRecommendations?.recommendations.length) return;
    const next =
      docRecommendations.recommendations.find((r) => !r.generated)
      || docRecommendations.recommendations[0];
    if (next) setDocType(normalizeDocType(next.doc_type) || next.doc_type);
  }, [docRecommendations, docType]);

  const markRecommendationGenerated = useCallback((docTypeValue: string, documentId?: number) => {
    setDocRecommendations((prev) => {
      if (!prev) return prev;
      const key = normalizeDocType(docTypeValue) || docTypeValue;
      return {
        ...prev,
        recommendations: prev.recommendations.map((r) =>
          (normalizeDocType(r.doc_type) || r.doc_type) === key
            ? { ...r, generated: true, document_id: documentId ?? r.document_id }
            : r,
        ),
      };
    });
  }, []);

  const applyGeneratedDocument = useCallback(
    (doc: Document, typeForHistory: string, opts?: { pipelineHint?: string; vaultArchived?: boolean }) => {
      const docWithVault =
        opts?.vaultArchived || doc.vault_archived ? { ...doc, vault_archived: true } : doc;
      setGeneratedDoc(docWithVault);
      setEditedContent(doc.content);
      setEditedTitle(doc.title);
      setDocVersions([{ version: doc.version, updated_at: doc.updated_at, title: doc.title }]);
      refreshRecentDocuments();
      markRecommendationGenerated(typeForHistory, doc.id);
      addToolHistory({
        kind: 'docgen',
        title: doc.title || docTypeLabel(typeForHistory) || '法律文书',
        subtitle: docTypeLabel(typeForHistory),
        route: '/documents',
        query: String(doc.id),
      });
      const vaultHint = docWithVault.vault_archived ? 'Word 已同步到「材料库」' : '可在材料库查看导出文件';
      toast({
        type: 'success',
        title: '文书生成完成',
        description: opts?.pipelineHint || `正在下载 Word；${vaultHint}`,
      });
      announceToScreenReader('文书生成完成');
      clearAutoSave('doc_gen_caseFacts');
      clearAutoSave('doc_gen_extraInstructions');
      requestAnimationFrame(() => {
        document.getElementById('doc-preview-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    },
    [refreshRecentDocuments, markRecommendationGenerated, toast],
  );

  const initPipelineSteps = useCallback(() => {
    const initial: Record<string, 'pending' | 'running' | 'done' | 'skipped'> = {};
    AGENT_PIPELINE_ORDER.forEach((k) => {
      initial[k] = 'pending';
    });
    setPipelineSteps(initial);
    setPipelineLoading(true);
    setLoading(false);
  }, []);

  const openDocument = useCallback(async (doc: Document, opts?: { skipAutoDownload?: boolean }) => {
    if (opts?.skipAutoDownload) autoWordDownloadedRef.current = doc.id;
    let fullDoc = doc;
    if (doc.id) {
      setPreviewLoadingId(doc.id);
      try {
        fullDoc = await documentApi.get(doc.id);
      } catch {
        toast({ type: 'error', title: '无法加载完整文书', description: '将显示摘要内容' });
      } finally {
        setPreviewLoadingId(null);
      }
    }
    setGeneratedDoc(fullDoc);
    setEditedContent(fullDoc.content);
    setEditedTitle(fullDoc.title);
    setDocType(fullDoc.type);
    setDocVersions([{ version: fullDoc.version, updated_at: fullDoc.updated_at, title: fullDoc.title }]);
    setEditMode(false);
    requestAnimationFrame(() => {
      document.getElementById('doc-preview-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }, [toast]);

  const handleDeleteDocument = useCallback(
    async (doc: Document) => {
      if (
        !window.confirm(
          `确定删除文书「${doc.title}」？\n\n将删除账户中的生成记录、结构化字段与已导出的 Word/PDF 等文件，不可恢复。`,
        )
      ) {
        return;
      }
      setDeletingDocId(doc.id);
      try {
        await documentApi.delete(doc.id);
        removeToolHistoryForDocument(doc.id);
        setRecentDocuments((prev) => prev.filter((d) => d.id !== doc.id));
        setBundleResults((prev) => prev.filter((d) => d.id !== doc.id));
        if (generatedDoc?.id === doc.id) {
          setGeneratedDoc(null);
          setEditedContent('');
          setEditedTitle('');
          setEditMode(false);
          setDocVersions([]);
        }
        toast({ type: 'success', title: '文书已删除' });
        announceToScreenReader('文书已删除');
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
    [generatedDoc?.id, toast],
  );

  useEffect(() => {
    caseApi.list({ limit: 100 }).then((data) => setCases(data)).catch(() => {}).finally(() => setInitialLoading(false));
    researchApi.list().then(setResearchReports).catch(() => {});
    refreshRecentDocuments();

    const session = loadIntakeSession();
    if (session) {
      if (session.caseFacts) setCaseFacts(trimToCharLimit(session.caseFacts, MAX_CASE_FACT_CHARS));
      const docType =
        searchParams.get('docType') ||
        session.recommendedTools.find((t) => t.agent_id === 'docgen')?.prefill.docType;
      if (docType) setDocType(normalizeDocType(docType));
      const caseFromUrl = searchParams.get('caseId');
      const caseFromActive = getActiveCaseId();
      const caseFromSession = session.createdCaseId;
      const resolved =
        caseFromUrl || (caseFromActive ? String(caseFromActive) : '') || (caseFromSession ? String(caseFromSession) : '');
      if (resolved) setSelectedCaseId(resolved);
    }

    const typeParam = searchParams.get('type') || searchParams.get('docType');
    if (typeParam) setDocType(normalizeDocType(typeParam));
    const modeParam = searchParams.get('mode');
    if (modeParam === 'single' || modeParam === 'bundle') {
      setMode(modeParam);
    }
    const bundleParam = searchParams.get('bundle');
    if (bundleParam) {
      const parsed = bundleParam
        .split(',')
        .map((t) => normalizeDocType(t))
        .filter(Boolean);
      if (parsed.length > 0) {
        setBundleDocTypes(Array.from(new Set(parsed)));
      }
    }

    const prefillParam = searchParams.get('prefill');
    const channelId = searchParams.get('channel');
    const scenarioId = searchParams.get('scenario');

    // Load auto-saved form data
    const savedCaseFacts = loadAutoSave('doc_gen_caseFacts');
    if (savedCaseFacts?.value) setCaseFacts(trimToCharLimit(savedCaseFacts.value, MAX_CASE_FACT_CHARS));
    const savedExtra = loadAutoSave('doc_gen_extraInstructions');
    if (savedExtra?.value) setExtraInstructions(savedExtra.value);

    if (prefillParam) {
      try {
        const decoded = decodeURIComponent(prefillParam);
        setCaseFacts(trimToCharLimit(decoded, MAX_CASE_FACT_CHARS));
      } catch {
        setCaseFacts(trimToCharLimit(prefillParam, MAX_CASE_FACT_CHARS));
      }
    }

    if (channelId && scenarioId) {
      const ch = getChannel(channelId);
      const scenario = getChannelScenario(channelId, scenarioId);
      if (ch && scenario) {
        setExtraInstructions(
          `来自专项通道「${ch.title}」· ${scenario.title}。请按劳动者维权文书风格生成。`,
        );
      }
    }

    const docIdParam = searchParams.get('docId');
    if (docIdParam) {
      const id = Number(docIdParam);
      if (Number.isFinite(id) && id > 0) {
        documentApi
          .get(id)
          .then((doc) => openDocument(doc, { skipAutoDownload: true }))
          .catch(() => toast({ type: 'error', title: '无法加载该文书', description: '可能已被删除' }));
      }
    }
  }, []);

  useEffect(() => {
    if (!generatedDoc) return;
    if (autoWordDownloadedRef.current === generatedDoc.id) return;
    autoWordDownloadedRef.current = generatedDoc.id;

    const tryDownload = async () => {
      try {
        await downloadDocumentFile(generatedDoc, 'word');
        return true;
      } catch {
        await new Promise((r) => setTimeout(r, 800));
        try {
          await downloadDocumentFile(generatedDoc, 'word');
          return true;
        } catch {
          return false;
        }
      }
    };

    void tryDownload().then((ok) => {
      const vaultHint = generatedDoc.vault_archived
        ? 'Word 已同步到「材料库」'
        : '可在「材料库」查看导出文件（若已同步）';
      if (ok) {
        toast({
          type: 'success',
          title: '文书已保存',
          description: `Word 已开始下载；${vaultHint}；「我的记录」可再次打开`,
        });
      } else {
        toast({
          type: 'warning',
          title: '文书已生成',
          description: `自动下载未成功，请点击「下载 Word」；${vaultHint}`,
        });
      }
    });
  }, [generatedDoc, toast]);

  useEffect(() => {
    if (!docType) {
      setTemplates([]);
      setSelectedTemplateId('');
      return;
    }
    let cancelled = false;
    setTemplatesLoading(true);
    templateApi
      .list({ type: docType })
      .then((data) => {
        if (cancelled) return;
        setTemplates(data);
        if (data.length === 0) {
          setSelectedTemplateId('');
        } else if (data.length === 1) {
          setSelectedTemplateId(data[0].id);
        } else if (workerMode) {
          const preferred = data.find((t) => t.is_public) || data[0];
          setSelectedTemplateId(preferred.id);
        } else {
          setSelectedTemplateId('');
        }
      })
      .catch(() => {
        if (!cancelled) {
          setTemplates([]);
          setSelectedTemplateId('');
        }
      })
      .finally(() => {
        if (!cancelled) setTemplatesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [docType, workerMode]);

  // Auto-save caseFacts and extraInstructions every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (caseFacts.trim()) autoSave('doc_gen_caseFacts', caseFacts);
      if (extraInstructions.trim()) autoSave('doc_gen_extraInstructions', extraInstructions);
    }, 10000);
    return () => clearInterval(interval);
  }, [caseFacts, extraInstructions]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showNewCase) {
        setShowNewCase(false);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [showNewCase]);

  const runDirectGenerate = useCallback(
    async (type: string, caseId: number | null) => {
      const advanceStep = (key: string, status: 'running' | 'done' | 'skipped') => {
        setPipelineSteps((prev) => ({ ...prev, [key]: status }));
      };
      advanceStep('prepare', 'running');
      advanceStep('prepare', 'done');
      advanceStep('research', 'running');
      advanceStep('research', 'done');
      advanceStep('generate', 'running');

      const doc = await documentApi.generate({
        type,
        case_id: caseId ?? undefined,
        case_facts: caseFacts.trim(),
        extra_instructions: extraInstructions.trim() || undefined,
        research_report_ids: selectedReportIds.length > 0 ? selectedReportIds : undefined,
        template_id: selectedTemplateId ? Number(selectedTemplateId) : undefined,
      }, 'doc-generate');

      advanceStep('generate', 'done');
      advanceStep('review', 'done');
      advanceStep('quality', 'skipped');
      return doc;
    },
    [caseFacts, extraInstructions, selectedReportIds, selectedTemplateId],
  );

  const generateDocument = useCallback(
    async (targetDocType?: string, e?: React.FormEvent) => {
      e?.preventDefault();
      const type = normalizeDocType(targetDocType || docType);
      if (!type || !caseFacts.trim()) {
        toast({ type: 'warning', title: '请先填写案情描述' });
        return;
      }

      if (
        caseReadiness &&
        caseReadiness.docgen_recommendation === 'not_ready' &&
        (caseReadiness.docgen_blockers?.length ?? 0) > 0
      ) {
        toast({
          type: 'warning',
          title: '材料完整度不足',
          description: caseReadiness.docgen_blockers?.[0] || '建议先补充证据与案情描述',
        });
      }

      if (
        caseReadiness &&
        caseReadiness.docgen_recommendation === 'caution'
      ) {
        toast({
          type: 'info',
          title: '材料可能不够完整',
          description: `综合评分 ${caseReadiness.combined_score ?? caseReadiness.readiness_score} 分，生成后请仔细核对。`,
        });
      }

      setDocType(type);
      setGeneratingDocType(type);
      setError('');
      setGeneratedDoc(null);
      setReviewResult(null);
      setEditMode(false);
      initPipelineSteps();

      const caseId = selectedCaseId ? Number(selectedCaseId) : null;
      const hasCase = caseId != null && Number.isFinite(caseId);

      const finish = (doc: Document, hint?: string, vaultArchived?: boolean) => {
        applyGeneratedDocument(doc, type, { pipelineHint: hint, vaultArchived });
        refreshDocRecommendations();
      };

      try {
        // 统一走后端 generate API（已含法规检索、离线兜底、分阶段写库，避免 SSE 流水线锁库）
        const doc = await runDirectGenerate(type, hasCase ? caseId : null);
        const mode = (doc.ai_metadata as { generation_mode?: string } | undefined)?.generation_mode;
        const hint =
          mode === 'offline_fallback'
            ? '已根据案情与证据生成标准格式初稿，请核对 [待填写] 项后下载'
            : hasCase
              ? '已关联案件并写入材料库'
              : '文书已生成，请核对后下载 Word';
        finish(doc, hint, doc.vault_archived);
      } catch (err: unknown) {
        if (axios.isCancel(err)) {
          setError('生成已取消');
        } else {
          const msg =
            err instanceof AxiosError
              ? (err.response?.data?.detail || '文书生成失败，请重试')
              : '文书生成失败，请重试';
          setError(msg);
          toast({ type: 'error', title: '文书生成失败', description: msg });
        }
      } finally {
        setPipelineLoading(false);
        setGeneratingDocType(null);
      }
    },
    [
      docType,
      caseFacts,
      selectedCaseId,
      caseReadiness,
      initPipelineSteps,
      applyGeneratedDocument,
      runDirectGenerate,
      extraInstructions,
      selectedReportIds,
      refreshDocRecommendations,
      toast,
    ],
  );

  const handlePrimaryGenerate = useCallback(
    (e?: React.FormEvent) => {
      void generateDocument(undefined, e);
    },
    [generateDocument],
  );

  const handleRecommendationGenerate = useCallback(
    (type: string) => {
      void generateDocument(type);
    },
    [generateDocument],
  );

  const handleViewRecommendedDoc = useCallback(
    (type: string, documentId?: number | null) => {
      if (documentId) {
        documentApi
          .get(documentId)
          .then((doc) => {
            setDocType(normalizeDocType(type) || type);
            void openDocument(doc, { skipAutoDownload: true });
          })
          .catch(() => toast({ type: 'error', title: '无法加载文书' }));
        return;
      }
      const match = recentDocuments.find((d) => normalizeDocType(d.type) === normalizeDocType(type));
      if (match) {
        setDocType(normalizeDocType(type) || type);
        void openDocument(match, { skipAutoDownload: true });
      }
    },
    [openDocument, recentDocuments, toast],
  );

  const handleExport = useCallback(async (format: 'word' | 'markdown' | 'html' | 'pdf') => {
    if (!generatedDoc) return;
    setExportLoading(format);
    try {
      await downloadDocumentFile(generatedDoc, format);
      const ext = format === 'word' ? 'DOCX' : format === 'pdf' ? 'PDF' : format.toUpperCase();
      toast({ type: 'success', title: `已下载 ${ext} 文件` });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '导出失败，请重试';
      setError(msg);
      toast({ type: 'error', title: '导出失败', description: msg });
    } finally {
      setExportLoading(null);
    }
  }, [generatedDoc, toast]);

  const handleReview = useCallback(async () => {
    if (!generatedDoc) return;
    setReviewLoading(true);
    setReviewResult(null);
    try {
      const doc = await documentApi.review(generatedDoc.id) as Document & { review_result?: string };
      setReviewResult(doc.review_result || '审校完成，未发现问题。');
      if (doc.content !== generatedDoc.content) {
        setGeneratedDoc(doc);
        setEditedContent(doc.content);
        setDocVersions((prev) => [...prev, { version: doc.version, updated_at: doc.updated_at, title: doc.title }]);
      }
      toast({ type: 'success', title: 'AI审校完成' });
    } catch {
      setError('AI审校失败，请重试');
      toast({ type: 'error', title: 'AI审校失败' });
    } finally {
      setReviewLoading(false);
    }
  }, [generatedDoc, toast]);

  const handleVerifyLaws = useCallback(async () => {
    if (!generatedDoc) return;
    setVerifyLoading(true);
    setVerifyResult(null);
    try {
      const result = await documentApi.verifyLaws(generatedDoc.id);
      setVerifyResult(result.verification_results);
      const hasIssues = result.verification_results.some((v: any) => !v.overall_consistent);
      if (hasIssues) {
        toast({ type: 'warning', title: '法条引用待核实', description: `${result.verification_results.filter((v: any) => !v.overall_consistent).length}条引用需要核实` });
      } else {
        toast({ type: 'success', title: '法条核查通过', description: `共${result.verification_results.length}条引用均核实无误` });
      }
    } catch {
      setError('法条核查失败，请重试');
      toast({ type: 'error', title: '法条核查失败' });
    } finally {
      setVerifyLoading(false);
    }
  }, [generatedDoc, toast]);

  const handleSaveEdit = useCallback(async () => {
    if (!generatedDoc) return;
    try {
      const updated = await documentApi.update(generatedDoc.id, {
        title: editedTitle,
        content: editedContent,
      });
      setGeneratedDoc(updated);
      setEditMode(false);
      setDocVersions((prev) => [...prev, { version: updated.version, updated_at: updated.updated_at, title: updated.title }]);
      toast({ type: 'success', title: '修改已保存' });
    } catch {
      setError('保存失败，请重试');
      toast({ type: 'error', title: '保存失败' });
    }
  }, [generatedDoc, editedTitle, editedContent, toast]);

  const handleCreateCase = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingCase(true);
    try {
      const created = await caseApi.create({
        ...newCase,
        title: withCaseTitleDatePrefix(newCase.title),
      });
      setCases((prev) => [created, ...prev]);
      setSelectedCaseId(String(created.id));
      setShowNewCase(false);
      setNewCase({ title: '', case_type: 'civil', description: '' });
      toast({ type: 'success', title: '案件创建成功' });
    } catch {
      setError('创建案件失败');
      toast({ type: 'error', title: '创建案件失败' });
    } finally {
      setCreatingCase(false);
    }
  }, [newCase, toast]);

  const handleReset = useCallback(() => {
    setDocType('');
    setSelectedCaseId('');
    setCaseFacts('');
    setExtraInstructions('');
    setGeneratedDoc(null);
    setReviewResult(null);
    setEditMode(false);
    setError('');
    setSelectedReportIds([]);
    setShowReportPicker(false);
    setDocVersions([]);
    setBundleResults([]);
    setBundleDocTypes([]);
  }, []);

  const handleFileExtract = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setExtractingFile(true);
    try {
      const result = await documentApi.extractText(file);
      if (result.text && !result.text.startsWith('[')) {
        setCaseFacts((prev) => {
          const merged = prev ? `${prev}\n\n${result.text}` : result.text;
          const limited = trimToCharLimit(merged, MAX_CASE_FACT_CHARS);
          if (limited !== merged) {
            toast({ type: 'warning', title: `案情描述最多 ${MAX_CASE_FACT_CHARS} 字，已自动截断` });
          }
          return limited;
        });
        toast({ type: 'success', title: '文件文字提取成功' });
      } else {
        setError(result.text || '文件文字提取失败');
        toast({ type: 'error', title: '文件文字提取失败' });
      }
    } catch (err: unknown) {
      const msg = err instanceof AxiosError ? (err.response?.data?.detail || '文件上传失败') : '文件上传失败';
      setError(msg);
      toast({ type: 'error', title: '文件上传失败', description: msg });
    } finally {
      setExtractingFile(false);
      e.target.value = '';
    }
  }, [toast]);

  // Draft management
  const handleSaveDraft = useCallback(() => {
    if (!caseFacts.trim() && !docType) return;
    const draft: Draft = {
      id: Date.now().toString(),
      docType,
      caseFacts,
      extraInstructions,
      selectedCaseId,
      selectedReportIds,
      savedAt: new Date().toISOString(),
    };
    const updated = [draft, ...drafts.filter(d => !(d.docType === draft.docType && d.caseFacts === draft.caseFacts))];
    setDrafts(updated);
    saveDrafts(updated);
    toast({ type: 'success', title: '草稿已保存' });
  }, [caseFacts, docType, extraInstructions, selectedCaseId, selectedReportIds, drafts, toast]);

  const handleLoadDraft = useCallback((draft: Draft) => {
    setDocType(draft.docType);
    setCaseFacts(trimToCharLimit(draft.caseFacts, MAX_CASE_FACT_CHARS));
    setExtraInstructions(draft.extraInstructions);
    setSelectedCaseId(draft.selectedCaseId);
    setSelectedReportIds(draft.selectedReportIds);
    setShowDrafts(false);
  }, []);

  const handleDeleteDraft = useCallback((id: string) => {
    setDrafts(prev => {
      const updated = prev.filter(d => d.id !== id);
      saveDrafts(updated);
      return updated;
    });
  }, []);

  // Bundle generation
  const handleBundleGenerate = useCallback(async () => {
    if (!caseFacts.trim() || bundleDocTypes.length === 0) return;

    setBundleGenerating(true);
    setBundleResults([]);
    setBundleProgress({ current: 0, total: bundleDocTypes.length, currentLabel: '' });

    const results: Document[] = [];

    for (let i = 0; i < bundleDocTypes.length; i++) {
      const docType = bundleDocTypes[i];
      const docLabel = docTypeLabel(docType);
      setBundleProgress({ current: i + 1, total: bundleDocTypes.length, currentLabel: `正在生成 ${docLabel}...` });

      try {
        const doc = await documentApi.generate({
          type: docType,
          case_id: selectedCaseId ? Number(selectedCaseId) : undefined,
          case_facts: caseFacts.trim(),
          extra_instructions: extraInstructions.trim() || undefined,
          research_report_ids: selectedReportIds.length > 0 ? selectedReportIds : undefined,
        });
        results.push(doc);
      } catch (err: unknown) {
        const detail = err instanceof AxiosError ? (err.response?.data?.detail || '请重试') : '请重试';
        toast({ type: 'error', title: `${docLabel} 生成失败`, description: detail });
      }
    }

    setBundleResults(results);
    setBundleGenerating(false);
      if (results.length > 0) {
      refreshRecentDocuments();
      toast({
        type: 'success',
        title: '批量生成完成',
        description: `已保存 ${results.length} 份文书，可点击下方下载 Word`,
      });
    }
  }, [caseFacts, bundleDocTypes, selectedCaseId, extraInstructions, selectedReportIds, toast, refreshRecentDocuments]);

  const toggleBundleDocType = useCallback((type: string) => {
    setBundleDocTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    );
  }, []);

  const applyBundlePreset = useCallback((preset: typeof BUNDLE_PRESETS[0]) => {
    setBundleDocTypes(preset.types);
  }, []);

  const selectedDocMeta = DOC_TYPES.find((d) => d.value === docType);
  const selectedDocLabel = selectedDocMeta?.label || docTypeLabel(docType);
  const selectedDocDesc = selectedDocMeta?.desc || '';

  // Memoized template filtering for bundle mode
  const bundleTemplateOptions = useMemo(() => {
    return DOC_TYPES.filter(dt => !bundleDocTypes.includes(dt.value));
  }, [bundleDocTypes]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 sm:px-0">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">生成文书</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            AI 分析案情与证据后推荐文书清单，逐项生成、预览并自动归档材料库
          </p>
        </div>
        <div className="flex items-center gap-2">
          {drafts.length > 0 && (
            <button
              onClick={() => setShowDrafts(!showDrafts)}
              className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
            >
              <Save className="h-4 w-4" />
              草稿箱 ({drafts.length})
            </button>
          )}
          {generatedDoc && (
            <button
              onClick={handleReset}
              className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent"
            >
              <RotateCcw className="h-4 w-4" />
              重新生成
            </button>
          )}
        </div>
      </div>

      <DocRecommendationPanel
        data={docRecommendations}
        loading={recommendationsLoading}
        generatingType={generatingDocType}
        onGenerate={handleRecommendationGenerate}
        onViewGenerated={handleViewRecommendedDoc}
      />

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert" aria-live="polite">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{error}</p>
          <button onClick={() => setError('')} className="ml-auto shrink-0 hover:text-red-900">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Drafts Panel */}
      {showDrafts && drafts.length > 0 && (
        <div className="rounded-xl border bg-card p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold">已保存的草稿</h3>
            <button onClick={() => setShowDrafts(false)} className="text-xs text-muted-foreground hover:text-foreground">
              关闭
            </button>
          </div>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {drafts.map(d => (
              <div key={d.id} className="flex items-center gap-2 rounded-lg border p-2 hover:bg-accent">
                <button onClick={() => handleLoadDraft(d)} className="flex-1 text-left">
                  <p className="text-sm font-medium truncate">
                    {DOC_TYPES.find(t => t.value === d.docType)?.label || '未分类'} - {d.caseFacts.slice(0, 30)}...
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(d.savedAt).toLocaleString()} | {countWords(d.caseFacts).chars} 字
                  </p>
                </button>
                <button onClick={() => handleDeleteDraft(d.id)} className="p-1 text-muted-foreground hover:text-destructive">
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bundle Mode */}
      {mode === 'bundle' && (
        <div className="space-y-4">
          {/* Bundle presets */}
          <div className="rounded-xl border bg-card p-4 shadow-sm">
            <h3 className="text-sm font-semibold mb-3">快速模板</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {visibleBundlePresets.map(preset => (
                <button
                  key={preset.key}
                  onClick={() => applyBundlePreset(preset)}
                  className={cn(
                    'rounded-lg border p-3 text-left transition-all hover:shadow-sm',
                    bundleDocTypes.length === preset.types.length && bundleDocTypes.every(t => preset.types.includes(t))
                      ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                      : 'hover:border-primary/30'
                  )}
                >
                  <p className="font-medium text-sm">{preset.label}</p>
                  <p className="text-xs text-muted-foreground mt-1">{preset.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Custom multi-select */}
          <div className="rounded-xl border bg-card p-4 shadow-sm">
            <h3 className="text-sm font-semibold mb-3">自定义文书类型</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {visibleDocTypes.map(dt => (
                <label key={dt.value} className={cn(
                  'flex items-center gap-2 rounded-lg border p-2 cursor-pointer transition-all text-sm',
                  bundleDocTypes.includes(dt.value)
                    ? 'border-primary bg-primary/5'
                    : 'hover:border-primary/30'
                )}>
                  <input
                    type="checkbox"
                    checked={bundleDocTypes.includes(dt.value)}
                    onChange={() => toggleBundleDocType(dt.value)}
                    className="shrink-0"
                  />
                  <span className="truncate">{dt.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Bundle Progress */}
          {bundleGenerating && (
            <div className="rounded-xl border bg-card p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-4">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                <div>
                  <p className="font-semibold">批量生成中 ({bundleProgress.current}/{bundleProgress.total})</p>
                  <p className="text-xs text-muted-foreground">{bundleProgress.currentLabel}</p>
                </div>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{ width: `${(bundleProgress.current / bundleProgress.total) * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Bundle Results */}
          {bundleResults.length > 0 && !bundleGenerating && (
            <div className="rounded-xl border bg-card p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold">批量生成结果 ({bundleResults.length} 份文书)</h3>
                <button onClick={() => setBundleResults([])} className="text-xs text-muted-foreground hover:text-foreground">清空</button>
              </div>
              <div className="space-y-2">
                {bundleResults.map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between rounded-lg border p-3 hover:bg-accent/50">
                    <div className="flex items-center gap-3 min-w-0">
                      <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{doc.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {DOC_TYPES.find(d => d.value === doc.type)?.label || doc.type} | {countWords(doc.content).chars} 字
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        disabled={previewLoadingId === doc.id}
                        onClick={() => void openDocument(doc, { skipAutoDownload: true })}
                        className="rounded-md border px-2 py-1 text-xs hover:bg-accent disabled:opacity-50"
                      >
                        {previewLoadingId === doc.id ? '加载…' : '查看'}
                      </button>
                      <button
                        type="button"
                        onClick={() => downloadDocumentFile(doc, 'word').catch(() => toast({ type: 'error', title: '下载失败' }))}
                        className="rounded-md border px-2 py-1 text-xs hover:bg-accent"
                        title="下载 Word"
                      >
                        <Download className="h-3 w-3" />
                      </button>
                      <button
                        type="button"
                        disabled={deletingDocId === doc.id}
                        onClick={() => handleDeleteDocument(doc)}
                        className="rounded-md border px-2 py-1 text-xs text-destructive hover:bg-destructive/10 disabled:opacity-50"
                        title="删除"
                      >
                        {deletingDocId === doc.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Trash2 className="h-3 w-3" />
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bundle generate button */}
          <button
            onClick={handleBundleGenerate}
            disabled={bundleGenerating || !caseFacts.trim() || bundleDocTypes.length === 0}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            {bundleGenerating ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> 批量生成中...</>
            ) : (
              <><Layers className="h-4 w-4" /> 批量生成 ({bundleDocTypes.length} 份)</>
            )}
          </button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Form Panel */}
        <div className={cn('lg:col-span-2', generatedDoc && 'lg:col-span-2')}>
          <form onSubmit={mode === 'single' ? handlePrimaryGenerate : (e) => { e.preventDefault(); handleBundleGenerate(); }} className="space-y-5 rounded-xl border bg-card p-4 sm:p-6 shadow-sm">
            {/* Document Type - single mode only */}
            {mode === 'single' && (
              <DocumentTypeSelector
                types={visibleDocTypes}
                value={docType}
                onChange={setDocType}
                disabled={loading}
                selectedLabel={selectedDocLabel}
                selectedDesc={selectedDocDesc}
              />
            )}

            {mode === 'single' && docType && !templatesLoading && templates.length === 0 && (
              <div className="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2.5 text-sm text-amber-900 dark:text-amber-100">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <p>
                  当前类型「{selectedDocLabel}」尚无可用模板。请管理员在「文书模板」中
                  <strong>同步平台模板包</strong>后再生成，否则将提示未找到模板。
                </p>
              </div>
            )}

            {mode === 'single' && docType && (templatesLoading || templates.length > 0) && (
              <div>
                <label className="mb-1.5 block text-sm font-medium">
                  文书模板
                  <span className="ml-1 text-xs font-normal text-muted-foreground">（可选；未选时按类型自动匹配平台模板）</span>
                </label>
                {templatesLoading ? (
                  <p className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    加载模板…
                  </p>
                ) : (
                  <div className="space-y-2">
                    <button
                      type="button"
                      onClick={() => setSelectedTemplateId('')}
                      className={cn(
                        'w-full rounded-lg border px-3 py-2.5 text-left text-sm transition-colors',
                        selectedTemplateId === ''
                          ? 'border-accent bg-accent/5'
                          : 'border-border hover:bg-muted/30',
                      )}
                    >
                      不指定模板（由系统按文书类型自动匹配）
                    </button>
                    {templates.map((tmpl) => (
                      <button
                        key={tmpl.id}
                        type="button"
                        onClick={() => setSelectedTemplateId(tmpl.id)}
                        className={cn(
                          'w-full rounded-lg border px-3 py-2.5 text-left transition-colors',
                          selectedTemplateId === tmpl.id
                            ? 'border-accent bg-accent/5'
                            : 'border-border hover:bg-muted/30',
                        )}
                      >
                        <div className="flex flex-wrap items-center gap-1.5">
                          <p className="font-medium">{tmpl.name}</p>
                          {tmpl.supports_structured && (
                            <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-800 dark:text-emerald-200">
                              固定版式
                            </span>
                          )}
                          {tmpl.category && (
                            <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                              {tmpl.category}
                            </span>
                          )}
                        </div>
                        {tmpl.description && (
                          <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{tmpl.description}</p>
                        )}
                        {tmpl.sections_preview && tmpl.sections_preview.length > 0 && (
                          <p className="mt-1.5 line-clamp-2 text-[11px] text-muted-foreground">
                            章节：{tmpl.sections_preview.join(' · ')}
                          </p>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Case Selection */}
            <div>
              <label className="mb-1.5 block text-sm font-medium">关联案件</label>
              <div className="flex gap-2">
                <select
                  value={selectedCaseId}
                  onChange={(e) => setSelectedCaseId(e.target.value)}
                  disabled={loading}
                  className="flex-1 appearance-none rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:opacity-50"
                >
                  <option value="">不关联案件</option>
                  {cases.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.title}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setShowNewCase(true)}
                  disabled={loading}
                  className="flex items-center gap-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent disabled:opacity-50"
                >
                  <Plus className="h-4 w-4" />
                  新建
                </button>
              </div>
            </div>

            {selectedCaseId && (readinessLoading || caseReadiness) && (
              <CaseReadinessHint
                readiness={caseReadiness}
                loading={readinessLoading}
                variant="docgen"
                className="sticky top-2 z-10"
              />
            )}

            {lastPipelineHint && (
              <p className="rounded-lg border border-violet-500/25 bg-violet-500/8 px-3 py-2 text-xs text-muted-foreground">
                <Bot className="mr-1 inline h-3.5 w-3.5 text-violet-600" />
                {lastPipelineHint}
              </p>
            )}

            {/* Case Facts */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium">
                  案情描述 <span className="text-red-500">*</span>
                </label>
                <label className="flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium cursor-pointer hover:bg-accent transition-colors">
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.xls,.png,.jpg,.jpeg,.gif,.webp,.bmp,.tiff,.mp3,.wav,.m4a,.ogg,.flac,.aac,.wma"
                    className="hidden"
                    onChange={handleFileExtract}
                    disabled={extractingFile || loading}
                  />
                  {extractingFile ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
                  {extractingFile ? '提取中...' : '上传文件提取文字'}
                </label>
              </div>
              <textarea
                value={caseFacts}
                onChange={(e) => {
                  const next = e.target.value;
                  const limited = trimToCharLimit(next, MAX_CASE_FACT_CHARS);
                  setCaseFacts(limited);
                }}
                required
                disabled={loading}
                placeholder="请用自然语言详细描述案件事实，包括当事人信息、纠纷经过、争议焦点等。也可以点击右上角「上传文件提取文字」按钮，从文件中自动提取。&#10;&#10;例如：原告张三于2024年1月15日借给被告李四人民币10万元，约定还款日期为2024年6月30日，月利率为0.5%。到期后李四拒绝还款..."
                rows={8}
                className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm leading-relaxed placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:opacity-50"
              />
              <div className="mt-1 flex flex-wrap items-center justify-between gap-x-3 gap-y-0.5">
                <p className="min-w-0 text-xs text-muted-foreground">
                  描述越详细，生成的文书越准确
                </p>
                <span className="shrink-0 whitespace-nowrap text-xs tabular-nums text-muted-foreground">
                  {caseFactCharCount}/{MAX_CASE_FACT_CHARS} 字
                </span>
              </div>
            </div>

            {/* Research Report References */}
            {researchReports.length > 0 && (
              <div>
                <label className="mb-1.5 block text-sm font-medium">
                  研究报告依据
                  <span className="ml-1 text-xs text-muted-foreground">（可选）</span>
                </label>
                <div className="rounded-lg border p-2">
                  <button
                    type="button"
                    onClick={() => setShowReportPicker(!showReportPicker)}
                    className="flex items-center gap-1 text-xs font-medium w-full"
                  >
                    {showReportPicker ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                    选择研究报告 {selectedReportIds.length > 0 ? `（已选${selectedReportIds.length}篇）` : `（${researchReports.length}篇可用）`}
                  </button>
                  {showReportPicker && (
                    <div className="mt-2 space-y-2">
                      <div className="relative">
                        <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
                        <input
                          type="text"
                          value={reportSearch}
                          onChange={(e) => setReportSearch(e.target.value)}
                          placeholder="搜索研究报告..."
                          className="w-full rounded-md border bg-background pl-7 pr-3 py-1.5 text-xs placeholder:text-muted-foreground focus:border-primary focus:outline-none"
                        />
                      </div>
                      <div className="max-h-40 overflow-y-auto space-y-1">
                        {filteredReports.length === 0 ? (
                          <p className="text-xs text-muted-foreground py-2 text-center">未找到匹配的报告</p>
                        ) : (
                          filteredReports.map(r => (
                            <label key={r.id} className="flex items-start gap-2 text-xs p-1 rounded hover:bg-accent cursor-pointer">
                              <input
                                type="checkbox"
                                checked={selectedReportIds.includes(r.id)}
                                onChange={() => setSelectedReportIds(prev =>
                                  prev.includes(r.id) ? prev.filter(id => id !== r.id) : [...prev, r.id]
                                )}
                                className="mt-0.5"
                              />
                              <span className="truncate">{r.query.slice(0, 60)} ({new Date(r.created_at).toLocaleDateString()})</span>
                            </label>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Extra Instructions */}
            <div>
              <label className="mb-1.5 block text-sm font-medium">
                补充说明
                <span className="ml-1 text-xs text-muted-foreground">（可选）</span>
              </label>
              <textarea
                value={extraInstructions}
                onChange={(e) => setExtraInstructions(e.target.value)}
                disabled={loading || pipelineLoading}
                placeholder="例如：请侧重违约金计算部分、适用简易程序、增加某项诉讼请求等..."
                rows={3}
                className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:opacity-50"
              />
            </div>

            {/* Action buttons - single mode */}
            {mode === 'single' && (
              <div className="flex flex-col gap-2">
                <div className="flex flex-col gap-2 sm:flex-row">
                  <button
                    type="button"
                    onClick={handlePrimaryGenerate}
                    disabled={loading || pipelineLoading || !docType || !caseFacts.trim()}
                    className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {loading || pipelineLoading ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> {pipelineLoading ? '正在生成…' : '正在生成…'}</>
                    ) : (
                      <><Sparkles className="h-4 w-4" /> AI 生成文书</>
                    )}
                  </button>
                  {!loading && !pipelineLoading && caseFacts.trim() && (
                    <button
                      type="button"
                      onClick={handleSaveDraft}
                      className="flex items-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium transition-colors hover:bg-accent"
                      title="保存为草稿"
                    >
                      <Save className="h-4 w-4" />
                    </button>
                  )}
                </div>
                <p className="text-[11px] text-muted-foreground">
                  {selectedCaseId
                    ? '关联案件后将自动检索法规、审校质检，生成后下载 Word 并写入材料库'
                    : '建议关联案件以合并证据分析；也可直接根据案情生成'}
                </p>
                {lastPipelineHint && (
                  <p className="text-[11px] text-violet-800 dark:text-violet-200">{lastPipelineHint}</p>
                )}
              </div>
            )}
          </form>

          {mode === 'single' && recentDocuments.length > 0 && (
            <div className="mt-4 rounded-xl border bg-card p-4 shadow-sm">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold">最近生成的文书</h3>
                <button
                  type="button"
                  onClick={() => navigate('/records')}
                  className="text-xs text-accent hover:underline"
                >
                  全部记录
                </button>
              </div>
              <ul className="divide-y divide-border/60">
                {recentDocuments.map((doc) => (
                  <li key={doc.id} className="flex items-center gap-1">
                    <button
                      type="button"
                      disabled={previewLoadingId === doc.id}
                      onClick={() => void openDocument(doc, { skipAutoDownload: true })}
                      className="flex min-w-0 flex-1 items-center justify-between gap-2 py-2.5 text-left text-sm hover:bg-muted/30 disabled:opacity-50"
                    >
                      <span className="min-w-0 truncate font-medium">{doc.title}</span>
                      <span className="shrink-0 text-[11px] text-muted-foreground">
                        {docTypeLabel(doc.type)}
                      </span>
                    </button>
                    <button
                      type="button"
                      aria-label="删除文书"
                      disabled={deletingDocId === doc.id}
                      onClick={() => handleDeleteDocument(doc)}
                      className="shrink-0 rounded p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                    >
                      {deletingDocId === doc.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Right Panel - Loading / Result (single mode or after打开预览) */}
        {(mode === 'single' || generatedDoc) && (
          <div id="doc-preview-panel" className="lg:col-span-3 scroll-mt-20">
            {/* Loading State */}
            {(pipelineLoading || generatingDocType) && (
              <div className="rounded-xl border bg-card p-6 sm:p-8 shadow-sm">
                <div className="mb-6 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                    <Bot className="h-5 w-5 text-violet-600 animate-pulse" />
                  </div>
                  <div>
                    <p className="font-semibold">
                      正在生成 {docTypeLabel(generatingDocType || docType)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      准备材料 → 检索法规 → 生成 → 审校 → 质检
                    </p>
                  </div>
                </div>
                <div className="space-y-3">
                  {AGENT_PIPELINE_ORDER.map((key) => {
                    const status = pipelineSteps[key] || 'pending';
                    const label = AGENT_PIPELINE_LABELS[key] || key;
                    return (
                      <div
                        key={key}
                        className={cn(
                          'flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm transition-all duration-500',
                          status === 'done' || status === 'skipped'
                            ? 'bg-green-50 text-green-700'
                            : status === 'running'
                              ? 'bg-violet-500/10 text-violet-800 font-medium dark:text-violet-200'
                              : 'text-muted-foreground',
                        )}
                      >
                        {status === 'done' || status === 'skipped' ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : status === 'running' ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <div className="h-4 w-4 rounded-full border-2 border-muted" />
                        )}
                        {label}
                        {status === 'skipped' && (
                          <span className="text-[10px] text-muted-foreground">（跳过）</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Generated Document */}
            {generatedDoc && !pipelineLoading && !generatingDocType && (
              <div className="space-y-4">
                <div className="rounded-xl border border-emerald-500/35 bg-emerald-500/10 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex gap-3">
                      <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
                      <div>
                        <p className="text-sm font-semibold text-foreground">文书已保存到您的账户</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {(generatedDoc.ai_metadata as { generation_mode?: string })?.generation_mode === 'structured'
                            ? '已使用固定版式模板生成（与 Word 预览一致），请核对 [待填写] 项。'
                            : '下载 Word 后将保留分级标题与字段加粗；请用 Word 2016+ 打开。'}
                          <br />
                          编号 #{generatedDoc.id}
                          {selectedCaseId ? ` · 已关联案件` : ''}
                          {' · '}
                          {new Date(generatedDoc.updated_at || generatedDoc.created_at || Date.now()).toLocaleString('zh-CN')}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleExport('word')}
                        disabled={exportLoading === 'word'}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                      >
                        {exportLoading === 'word' ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Download className="h-3.5 w-3.5" />
                        )}
                        下载 Word
                      </button>
                      <button
                        type="button"
                        onClick={() => handleExport('pdf')}
                        disabled={exportLoading === 'pdf'}
                        className="inline-flex items-center gap-1.5 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted disabled:opacity-50"
                      >
                        PDF
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate('/records')}
                        className="inline-flex items-center gap-1.5 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
                      >
                        <History className="h-3.5 w-3.5" />
                        我的记录
                      </button>
                      <button
                        type="button"
                        disabled={deletingDocId === generatedDoc.id}
                        onClick={() => handleDeleteDocument(generatedDoc)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-destructive/40 bg-card px-3 py-2 text-xs font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50"
                      >
                        {deletingDocId === generatedDoc.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="h-3.5 w-3.5" />
                        )}
                        删除记录
                      </button>
                    </div>
                  </div>
                </div>

                {/* Toolbar */}
                <div className="flex flex-wrap items-center gap-2 rounded-xl border bg-card p-3 shadow-sm">
                  <div className="mr-auto flex items-center gap-2 min-w-0">
                    <FileText className="h-5 w-5 text-primary shrink-0" />
                    <span className="text-sm font-semibold truncate">{generatedDoc.title}</span>
                    <span className="rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground shrink-0">
                      {DOC_TYPES.find((d) => d.value === generatedDoc.type)?.label || generatedDoc.type}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handlePrimaryGenerate}
                    disabled={loading || pipelineLoading}
                    className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
                    title="基于相同参数重新生成"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    重新生成
                  </button>
                  <button
                    onClick={() => setEditMode(!editMode)}
                    className={cn(
                      'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                      editMode
                        ? 'bg-primary text-primary-foreground'
                        : 'border hover:bg-accent',
                    )}
                  >
                    {editMode ? <Eye className="h-3.5 w-3.5" /> : <Edit3 className="h-3.5 w-3.5" />}
                    {editMode ? '预览模式' : '编辑模式'}
                  </button>
                  <button
                    onClick={handleReview}
                    disabled={reviewLoading}
                    className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-violet-700 disabled:opacity-50"
                  >
                    {reviewLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                    {reviewLoading ? '审校中...' : 'AI审校'}
                  </button>
                  <button
                    onClick={handleVerifyLaws}
                    disabled={verifyLoading}
                    className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {verifyLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Shield className="h-3.5 w-3.5" />}
                    {verifyLoading ? '核查中...' : '法条核查'}
                  </button>
                  <button
                    onClick={() => handleExport('word')}
                    disabled={exportLoading === 'word'}
                    className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
                  >
                    {exportLoading === 'word' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                    Word
                  </button>
                  <button
                    onClick={() => handleExport('pdf')}
                    disabled={exportLoading === 'pdf'}
                    className="flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
                  >
                    {exportLoading === 'pdf' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                    PDF
                  </button>
                </div>

                {/* Review Result */}
                {reviewResult && (
                  <div className="rounded-xl border border-violet-200 bg-violet-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-violet-800">
                      <Sparkles className="h-4 w-4" />
                      AI 审校结果
                    </div>
                    <div className="whitespace-pre-wrap text-sm text-violet-900 leading-relaxed">
                      {reviewResult}
                    </div>
                  </div>
                )}

                {/* Law Verification Result */}
                {verifyResult && (
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                    <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-emerald-800">
                      <Shield className="h-4 w-4" />
                      法条核查结果（共{verifyResult.length}条引用）
                    </div>
                    <div className="space-y-2">
                      {verifyResult.map((v: any, i: number) => (
                        <div key={i} className={`rounded-lg p-3 text-sm ${v.overall_consistent ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                          <div className="flex items-center gap-2 font-medium">
                            {v.overall_consistent ? (
                              <CheckCircle2 className="h-4 w-4 text-green-600" />
                            ) : (
                              <AlertCircle className="h-4 w-4 text-red-600" />
                            )}
                            《{v.law_name}》{v.article_number}
                            <span className="text-xs text-muted-foreground ml-auto">
                              置信度: {(v.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">{v.recommendation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Document Version History */}
                {docVersions.length > 1 && (
                  <div className="rounded-lg border bg-muted/30 p-3">
                    <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground mb-2">
                      <Clock className="h-3 w-3" />
                      文档版本历史
                    </div>
                    <div className="space-y-1">
                      {docVersions.map((v, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <span className="font-medium">v{v.version}</span>
                          <span className="text-muted-foreground">{new Date(v.updated_at).toLocaleString()}</span>
                          <span className="text-muted-foreground truncate">{v.title}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Document Content */}
                <div className="rounded-xl border bg-card shadow-sm">
                  <div className="border-b px-4 sm:px-6 py-4">
                    <h2 className="text-lg font-bold">
                      {editMode ? (
                        <input
                          value={editedTitle}
                          onChange={(e) => setEditedTitle(e.target.value)}
                          className="w-full rounded border border-input px-2 py-1 text-lg font-bold focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
                        />
                      ) : (
                        generatedDoc.title
                      )}
                    </h2>
                  </div>

                  <div className="px-4 sm:px-6 py-5">
                    <FillRateBanner aiMetadata={generatedDoc.ai_metadata as any} />
                    {editMode ? (
                      <div className="space-y-4">
                        <textarea
                          value={editedContent}
                          onChange={(e) => setEditedContent(e.target.value)}
                          rows={18}
                          className="w-full resize-y rounded-lg border border-input bg-background p-4 font-mono text-sm leading-relaxed focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
                          placeholder="支持 # / ## / ### 标题与 **加粗**"
                        />
                        <div>
                          <p className="mb-2 text-xs font-medium text-muted-foreground">Word 版式实时预览</p>
                          <CourtDocumentPreview
                            content={editedContent}
                            title={editedContent.trim().startsWith('#') ? undefined : editedTitle}
                          />
                        </div>
                      </div>
                    ) : (
                      <CourtDocumentPreview
                        content={editedContent || generatedDoc.content}
                        title={
                          (editedContent || generatedDoc.content).trim().startsWith('#')
                            ? undefined
                            : generatedDoc.title
                        }
                      />
                    )}
                  </div>

                  {editMode && (
                    <div className="flex justify-end gap-3 border-t px-4 sm:px-6 py-4">
                      <button
                        onClick={() => {
                          setEditedContent(generatedDoc.content);
                          setEditedTitle(generatedDoc.title);
                          setEditMode(false);
                        }}
                        className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
                      >
                        取消
                      </button>
                      <button
                        onClick={handleSaveEdit}
                        className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                      >
                        保存修改
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Empty State */}
            {!generatedDoc && !loading && (
              <div className="flex flex-col items-center justify-center rounded-xl border bg-card py-20 shadow-sm">
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
                  <FileText className="h-8 w-8 text-primary/60" />
                </div>
                <h3 className="mb-2 text-lg font-semibold text-muted-foreground">文书预览区</h3>
                <p className="max-w-sm text-center text-sm text-muted-foreground">
                  选择文书类型并输入案情描述后，点击"生成文书"，AI 将在此处呈现生成的法律文书
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* New Case Modal - responsive */}
      {showNewCase && (
        <div className="fixed inset-0 z-50 flex items-start sm:items-center justify-center bg-black/50 p-4 overflow-y-auto">
          <div className="w-full max-w-md rounded-xl border bg-card p-4 sm:p-6 shadow-xl my-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">快速新建案件</h2>
              <button onClick={() => setShowNewCase(false)} aria-label="关闭" className="rounded p-1 hover:bg-accent">
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleCreateCase} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium">案件标题</label>
                <input
                  required
                  value={newCase.title}
                  onChange={(e) => setNewCase((p) => ({ ...p, title: e.target.value }))}
                  placeholder="例如：张三与李四民间借贷纠纷"
                  className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">案件类型</label>
                <select
                  value={newCase.case_type}
                  onChange={(e) => setNewCase((p) => ({ ...p, case_type: e.target.value }))}
                  className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
                >
                  <option value="civil">民事</option>
                  <option value="criminal">刑事</option>
                  <option value="administrative">行政</option>
                  <option value="labor">劳动</option>
                  <option value="contract">合同</option>
                  <option value="ip">知识产权</option>
                  <option value="other">其他</option>
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">案件描述</label>
                <textarea
                  value={newCase.description}
                  onChange={(e) => setNewCase((p) => ({ ...p, description: e.target.value }))}
                  placeholder="简要描述案件情况..."
                  rows={3}
                  className="w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewCase(false)}
                  className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={creatingCase}
                  className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                >
                  {creatingCase ? '创建中...' : '创建并关联'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
