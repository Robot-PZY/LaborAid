import React, { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search as SearchIcon, Scale, BookOpen, FileText, Loader2, Clock, Copy, Check, Trash2, BookmarkPlus, ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from 'lucide-react';
import { searchApi } from '@/lib/api';
import type { SearchResults } from '@/lib/api';
import { cn } from '@/lib/utils';

type SearchSource = 'all' | 'laws' | 'cases';

const sourceTabs: { value: SearchSource; label: string; icon: React.ElementType }[] = [
  { value: 'all', label: '全部', icon: SearchIcon },
  { value: 'laws', label: '法规', icon: Scale },
  { value: 'cases', label: '案例', icon: BookOpen },
];

const sourceBadge: Record<string, { label: string; color: string }> = {
  law: { label: '法律法规', color: 'bg-blue-100 text-blue-700' },
  case: { label: '司法案例', color: 'bg-emerald-100 text-emerald-700' },
  regulation: { label: '行政法规', color: 'bg-violet-100 text-violet-700' },
  judicial_interpretation: { label: '司法解释', color: 'bg-orange-100 text-orange-700' },
};

import { STORAGE_KEYS } from '@/lib/storage-keys';
import { addToolHistory } from '@/lib/tool-history';

const HISTORY_KEY = STORAGE_KEYS.searchHistory;
const SAVED_KEY = STORAGE_KEYS.savedResults;
const MAX_HISTORY = 20;
const PAGE_SIZE = 5;

function getSearchHistory(): string[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
  } catch {
    return [];
  }
}

function addToHistory(query: string) {
  const history = getSearchHistory().filter((h) => h !== query);
  history.unshift(query);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
}

function clearHistory() {
  localStorage.removeItem(HISTORY_KEY);
}

interface SavedResult {
  id: string;
  title: string;
  content: string;
  source: string;
  savedAt: string;
}

/** 清理第三方搜索结果里携带的 HTML 高亮标签与常见实体 */
function sanitizeSearchText(input: unknown): string {
  if (input == null) return '';
  let text = String(input);
  // 先处理常见 HTML 实体
  text = text
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&amp;/gi, '&')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'");
  // 去掉标签（尤其是 <em>）
  text = text.replace(/<\/?[^>]+>/g, '');
  return text.trim();
}

function getSavedResults(): SavedResult[] {
  try {
    return JSON.parse(localStorage.getItem(SAVED_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveResult(result: { title: string; content: string; source: string }) {
  const saved = getSavedResults();
  const id = `${result.source}-${result.title}-${Date.now()}`;
  // Prevent duplicates by title
  if (saved.some((s) => s.title === result.title && s.source === result.source)) return false;
  saved.unshift({
    id,
    title: result.title,
    content: result.content,
    source: result.source,
    savedAt: new Date().toISOString(),
  });
  localStorage.setItem(SAVED_KEY, JSON.stringify(saved));
  return true;
}

function removeSavedResult(id: string) {
  const saved = getSavedResults().filter((s) => s.id !== id);
  localStorage.setItem(SAVED_KEY, JSON.stringify(saved));
}

/** 列表摘要：避免外部案例库返回整段判决书撑满卡片 */
function previewText(text: string, maxLen = 200): string {
  const normalized = sanitizeSearchText(text).replace(/\s+/g, ' ');
  if (normalized.length <= maxLen) return normalized;
  return `${normalized.slice(0, maxLen)}…`;
}

/** 将长正文按常见裁判文书小节分段展示 */
function splitLegalSections(text: string): { heading: string; body: string }[] {
  const clean = sanitizeSearchText(text);
  if (!clean) return [];
  const markers = ['当事人信息', '基本事实', '审理经过', '本院认为', '裁判结果', '诉讼请求', '裁判要旨'];
  const pattern = new RegExp(`(?=(${markers.join('|')}))`, 'g');
  const parts = clean.split(pattern).map((p) => p.trim()).filter(Boolean);
  if (parts.length <= 1) return [{ heading: '正文', body: clean }];
  return parts.map((part) => {
    const hit = markers.find((m) => part.startsWith(m));
    if (!hit) return { heading: '正文', body: part };
    return { heading: hit, body: part.slice(hit.length).trim() || part };
  });
}

function dataSourceLabel(item: { source?: string; _kind?: string }): string {
  const raw = sanitizeSearchText(item.source || '');
  if (raw && raw !== 'law' && raw !== 'case') return raw;
  return item._kind === 'case' ? '案例库' : '法规库';
}

/** Highlight occurrences of query terms in text */
function highlightText(text: string, query: string): React.ReactNode {
  if (!query.trim()) return text;
  const terms = query.trim().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return text;

  const pattern = terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
  const regex = new RegExp(`(${pattern})`, 'gi');
  const parts = text.split(regex);

  if (parts.length <= 1) return text;

  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <mark key={i} className="rounded-sm bg-yellow-200 px-0.5 text-inherit">{part}</mark>
    ) : (
      part
    ),
  );
}

/** Compute a simple relevance score heuristic */
function computeRelevance(result: any, query: string): number {
  if (!query.trim()) return 0;
  const terms = query.trim().split(/\s+/).filter(Boolean);
  const compactQuery = query.replace(/\s+/g, '').toLowerCase();
  const title = sanitizeSearchText(result.title || '').toLowerCase();
  const content = sanitizeSearchText(result.content || result.snippet || '').toLowerCase();
  const compactTitle = title.replace(/\s+/g, '');
  const compactContent = content.replace(/\s+/g, '');
  const bigrams: string[] = [];
  for (let i = 0; i < compactQuery.length - 1; i += 1) {
    bigrams.push(compactQuery.slice(i, i + 2));
  }

  let score = 12;
  const backendScore = Number(result.relevance_score ?? 0);
  if (Number.isFinite(backendScore) && backendScore > 0) {
    score += Math.min(18, Math.round(backendScore * 18));
  }

  for (const term of terms) {
    const termLower = term.toLowerCase();
    if (title.includes(termLower)) score += 12;
    if (content.includes(termLower)) score += 6;
    // Exact title match bonus
    if (title === termLower) score += 18;
  }

  // 中文短语匹配（按二元字组）
  if (bigrams.length > 0) {
    let titleHits = 0;
    let contentHits = 0;
    for (const bg of bigrams) {
      if (compactTitle.includes(bg)) titleHits += 1;
      else if (compactContent.includes(bg)) contentHits += 1;
    }
    score += Math.round((titleHits / bigrams.length) * 20);
    score += Math.round((contentHits / bigrams.length) * 12);
  }

  // 信息完整度加分（减少大量同分）
  const richnessFields = ['provision_ref', 'case_number', 'court', 'date', 'judgment_type'];
  const richness = richnessFields.reduce((n, f) => n + (result[f] ? 1 : 0), 0);
  score += richness * 3;

  // 文本聚焦度（过短/过长都降权）
  const len = content.length;
  if (len > 0) {
    const focus = Math.max(0, 10 - Math.abs(260 - len) / 60);
    score += Math.round(focus);
  }

  // 稳定微扰（按标题哈希），避免全部卡在几个数值
  const stable = ((result.title || '').split('').reduce((s: number, ch: string) => s + ch.charCodeAt(0), 0) % 9) - 4;
  score += stable;

  return Math.max(5, Math.min(98, score));
}

function RelevanceBar({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-yellow-500' : 'bg-gray-400';
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs text-muted-foreground">{score}%</span>
    </div>
  );
}

function Search() {
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [source, setSource] = useState<SearchSource>('laws');
  const [searchData, setSearchData] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [expandedSet, setExpandedSet] = useState<Set<string>>(new Set());
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<string[]>(getSearchHistory);
  const [currentPage, setCurrentPage] = useState(1);
  const [showSaved, setShowSaved] = useState(false);
  const [savedResults, setSavedResults] = useState<SavedResult[]>(getSavedResults);

  // Request cancellation ref
  const abortRef = useRef<AbortController | null>(null);
  // Debounce timer ref
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sourceEffectBoot = useRef(true);

  useEffect(() => {
    const q = searchParams.get('q');
    if (q) setQuery(q);
  }, [searchParams]);


  // Combine laws and cases into a flat result list
  const allResults = useMemo(() => searchData
    ? [
        ...(searchData.laws || []).map((item: any) => ({ ...item, _kind: 'law' as const })),
        ...(searchData.cases || []).map((item: any) => ({ ...item, _kind: 'case' as const })),
      ]
        .filter((item) => {
          if (source === 'laws') return item._kind === 'law';
          if (source === 'cases') return item._kind === 'case';
          return true;
        })
        .map((item) => ({
          ...item,
          title: sanitizeSearchText(item.title || ''),
          content: sanitizeSearchText(item.content || item.snippet || ''),
          uid: `${item._kind}::${item.document_id || item.case_id || item.id || item.title || ''}`,
          relevance: computeRelevance({ ...item, source: item._kind }, query),
        }))
        .sort((a, b) => b.relevance - a.relevance)
    : [], [searchData, source, query]);

  const totalPages = Math.ceil(allResults.length / PAGE_SIZE);
  const paginatedResults = allResults.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  );

  const isSavedResult = useCallback((result: { title: string; source: string }) => {
    return savedResults.some((s) => s.title === result.title && s.source === result.source);
  }, [savedResults]);

  const toggleExpanded = useCallback((uid: string) => {
    setExpandedSet((prev) => {
      const next = new Set(prev);
      if (next.has(uid)) next.delete(uid);
      else next.add(uid);
      return next;
    });
  }, []);

  const handleSearch = useCallback(async (searchQuery?: string) => {
    const q = searchQuery || query;
    if (!q.trim()) return;

    // Cancel any in-flight search
    if (abortRef.current) {
      abortRef.current.abort();
    }
    abortRef.current = new AbortController();

    if (searchQuery) setQuery(searchQuery);
    setLoading(true);
    setSearched(true);
    setError('');
    setShowHistory(false);
    setCurrentPage(1);
    setExpandedSet(new Set());
    try {
      const data = await searchApi.search({
        query: q.trim(),
        result_type: source === 'all' ? undefined : source,
        top_k: 20,
      });
      // Only update if this request wasn't superseded
      if (abortRef.current?.signal.aborted) return;
      setSearchData(data);
      addToHistory(q.trim());
      addToolHistory({
        kind: 'search',
        title: q.trim(),
        route: '/search',
        query: q.trim(),
      });
      setHistory(getSearchHistory());
    } catch {
      if (abortRef.current?.signal.aborted) return;
      setSearchData(null);
      setError('搜索失败，请重试');
    } finally {
      if (!abortRef.current?.signal.aborted) {
        setLoading(false);
      }
    }
  }, [query, source]);

  // 切换「法规 / 案例 / 全部」时，若已有查询则重新检索（跳过首次挂载）
  useEffect(() => {
    if (sourceEffectBoot.current) {
      sourceEffectBoot.current = false;
      return;
    }
    if (!searched || !query.trim()) return;
    void handleSearch(query);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 仅随 source 切换重搜
  }, [source]);

  useEffect(() => {
    const q = searchParams.get('q');
    if (searchParams.get('from') === 'intake' && q?.trim()) {
      void handleSearch(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intake 深链仅首次进入触发
  }, []);

  // Debounced search triggered on query change
  const handleDebouncedSearch = useCallback((value: string) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!value.trim()) return;
    debounceRef.current = setTimeout(() => {
      handleSearch(value);
    }, 400);
  }, [handleSearch]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || (e.key === 'Enter' && (e.ctrlKey || e.metaKey))) {
      handleSearch();
    }
  };

  const handleCopy = async (text: string, idx: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(null), 2000);
    } catch {
      // Fallback: do nothing
    }
  };

  const handleSaveToResearch = (result: any) => {
    const contentText = result.content || result.snippet || '';
    const kind = result._kind || result.source;
    const saved = getSavedResults();
    const existing = saved.find((s) => s.title === result.title && s.source === kind);
    if (existing) {
      removeSavedResult(existing.id);
      setSavedResults(getSavedResults());
      return;
    }
    const didSave = saveResult({
      title: result.title,
      content: contentText,
      source: kind,
    });
    if (didSave) setSavedResults(getSavedResults());
  };

  const handleRemoveSaved = (id: string) => {
    removeSavedResult(id);
    setSavedResults(getSavedResults());
  };

  const handleClearHistory = () => {
    clearHistory();
    setHistory([]);
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">检索法规</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            搜索法律法规、司法案例、司法解释等法律资源
          </p>
        </div>
        {savedResults.length > 0 && (
          <button
            onClick={() => setShowSaved(!showSaved)}
            className={cn(
              'flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium transition-colors',
              showSaved
                ? 'border-primary bg-primary/10 text-primary'
                : 'hover:bg-accent',
            )}
          >
            <BookmarkPlus className="h-4 w-4" />
            收藏 ({savedResults.length})
          </button>
        )}
      </div>

      {/* Saved Results Panel */}
      {showSaved && (
        <div className="rounded-xl border bg-card p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-sm">已收藏的研究资料</h2>
            <button onClick={() => setShowSaved(false)} className="text-xs text-muted-foreground hover:text-foreground">
              关闭
            </button>
          </div>
          {savedResults.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">暂无收藏</p>
          ) : (
            savedResults.map((item) => {
              const badge = sourceBadge[item.source] || { label: item.source, color: 'bg-gray-100 text-gray-700' };
              return (
                <div key={item.id} className="rounded-lg border p-3 flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', badge.color)}>
                        {badge.label}
                      </span>
                    </div>
                    <p className="text-sm font-medium truncate">{item.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{item.content.slice(0, 100)}</p>
                  </div>
                  <button
                    onClick={() => handleRemoveSaved(item.id)}
                    className="shrink-0 text-xs text-red-500 hover:text-red-700"
                  >
                    移除
                  </button>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Search Bar */}
      <div className="rounded-xl border bg-card p-4 shadow-sm">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => handleDebouncedSearch(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => { if (!searched && history.length > 0) setShowHistory(true); }}
              onBlur={() => { setTimeout(() => setShowHistory(false), 200); }}
              placeholder="输入关键词，如：民间借贷、劳动合同、知识产权..."
              aria-label="搜索关键词"
              className="w-full rounded-lg border border-input bg-background py-2.5 pl-10 pr-4 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/20"
            />
            {/* Search history dropdown */}
            {showHistory && history.length > 0 && (
              <div className="absolute left-0 right-0 top-full z-10 mt-1 rounded-lg border bg-card shadow-lg">
                <div className="flex items-center justify-between px-3 py-2 border-b">
                  <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    搜索历史
                  </span>
                  <button
                    onClick={handleClearHistory}
                    className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                  >
                    <Trash2 className="h-3 w-3" />
                    清除
                  </button>
                </div>
                {history.map((h) => (
                  <button
                    key={h}
                    onMouseDown={() => handleSearch(h)}
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm text-left hover:bg-accent"
                  >
                    <Clock className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">{h}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={() => handleSearch()}
            disabled={loading || !query.trim()}
            className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <SearchIcon className="h-4 w-4" />}
            搜索
          </button>
        </div>

        {/* Source Tabs */}
        <div className="mt-3 flex gap-1 rounded-lg bg-muted p-1">
          {sourceTabs.map((tab) => (
            <button
              key={tab.value}
              onClick={() => {
                setSource(tab.value);
                setCurrentPage(1);
              }}
              className={cn(
                'flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                source === tab.value
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <tab.icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert" aria-live="polite">
          <p>{error}</p>
          <button onClick={() => setError('')} className="ml-auto shrink-0 hover:text-red-900">&times;</button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-3">
          <div className="h-4 w-32 animate-pulse rounded bg-muted" />
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-xl border bg-card p-5">
              <div className="mb-3 h-5 w-20 animate-pulse rounded bg-muted" />
              <div className="mb-2 h-4 w-3/4 animate-pulse rounded bg-muted" />
              <div className="space-y-1.5">
                <div className="h-3 w-full animate-pulse rounded bg-muted" />
                <div className="h-3 w-5/6 animate-pulse rounded bg-muted" />
                <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty Results */}
      {!loading && searched && allResults.length === 0 && !error && (
        <div className="flex flex-col items-center justify-center rounded-xl border bg-card py-16">
          <FileText className="mb-3 h-12 w-12 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">未找到与 "{query}" 相关的结果</p>
          <p className="mt-1 text-xs text-muted-foreground">请尝试使用其他关键词或更宽泛的搜索条件</p>
        </div>
      )}

      {/* Results */}
      {!loading && allResults.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              共找到 <span className="font-medium text-foreground">{searchData?.total ?? allResults.length}</span> 条与 "<span className="font-medium">{query}</span>" 相关的结果
              {totalPages > 1 && (
                <span className="ml-2">
                  （第 {currentPage}/{totalPages} 页）
                </span>
              )}
            </p>
          </div>
          {paginatedResults.map((result: any, idx: number) => {
            const globalIdx = (currentPage - 1) * PAGE_SIZE + idx;
            const kind = result._kind as 'law' | 'case';
            const badge = sourceBadge[kind] || {
              label: kind === 'case' ? '司法案例' : '法律法规',
              color: 'bg-gray-100 text-gray-700',
            };
            const contentText = result.content || result.snippet || '';
            const preview = previewText(contentText);
            const sections = splitLegalSections(contentText);
            const isSaved = isSavedResult({ ...result, source: kind });
            const isExpanded = expandedSet.has(result.uid);
            return (
              <div
                key={globalIdx}
                className="rounded-xl border bg-card p-5 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-medium', badge.color)}>
                      {badge.label}
                    </span>
                    <RelevanceBar score={result.relevance} />
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleSaveToResearch(result)}
                      className={cn(
                        'flex items-center gap-1 rounded-md px-2 py-1 text-xs transition-colors',
                        isSaved
                          ? 'text-green-600 bg-green-50'
                          : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                      )}
                      title={isSaved ? '取消收藏' : '收藏到研究'}
                    >
                      <BookmarkPlus className="h-3.5 w-3.5" />
                      {isSaved ? '已收藏' : '收藏'}
                    </button>
                    <button
                      onClick={() => toggleExpanded(result.uid)}
                      className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                      title={isExpanded ? '收起详情' : '查看详情'}
                    >
                      {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      {isExpanded ? '收起' : '详情'}
                    </button>
                    <button
                      onClick={() => handleCopy(`${result.title}\n\n${contentText}`, globalIdx)}
                      className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                      title="复制结果"
                    >
                      {copiedIdx === globalIdx ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-green-500" />
                          <span className="text-green-600">已复制</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          复制
                        </>
                      )}
                    </button>
                  </div>
                </div>
                <h3 className={cn('mb-2 font-semibold leading-snug', isExpanded ? 'text-base' : 'text-sm line-clamp-2')}>
                  {highlightText(result.title, query)}
                </h3>
                {kind === 'law' && result.provision_ref && (
                  <p className="mb-2 text-xs font-medium text-primary">
                    {result.provision_ref}
                  </p>
                )}
                {!isExpanded && (
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {highlightText(preview, query)}
                  </p>
                )}
                {isExpanded && (
                  <div className="mt-4 space-y-3 border-t border-border/60 pt-4">
                    <div className="grid gap-2 rounded-lg border bg-muted/15 p-3 text-xs sm:grid-cols-2">
                      {result.provision_ref && (
                        <p className="sm:col-span-2">
                          <span className="font-medium text-foreground">条款：</span>
                          {result.provision_ref}
                        </p>
                      )}
                      {result.case_number && (
                        <p>
                          <span className="font-medium text-foreground">案号：</span>
                          {result.case_number}
                        </p>
                      )}
                      {result.court && (
                        <p>
                          <span className="font-medium text-foreground">法院：</span>
                          {result.court}
                        </p>
                      )}
                      {result.date && (
                        <p>
                          <span className="font-medium text-foreground">日期：</span>
                          {result.date}
                        </p>
                      )}
                      {result.judgment_type && (
                        <p>
                          <span className="font-medium text-foreground">文书类型：</span>
                          {result.judgment_type}
                        </p>
                      )}
                      <p className="sm:col-span-2">
                        <span className="font-medium text-foreground">数据来源：</span>
                        {dataSourceLabel(result)}
                      </p>
                    </div>
                    <div className="max-h-[min(420px,50vh)] overflow-y-auto rounded-lg border bg-background p-4 text-sm leading-relaxed">
                      {sections.map((sec, si) => (
                        <div key={si} className={si > 0 ? 'mt-4 border-t border-border/40 pt-4' : ''}>
                          {sec.heading !== '正文' && (
                            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-accent">
                              {sec.heading}
                            </p>
                          )}
                          <p className="whitespace-pre-wrap text-foreground/90">
                            {highlightText(sec.body, query)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="flex items-center gap-1 rounded-lg border px-3 py-2 text-sm transition-colors hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4" />
                上一页
              </button>
              <div className="flex items-center gap-1">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={cn(
                      'h-8 w-8 rounded-lg text-sm font-medium transition-colors',
                      currentPage === page
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-accent',
                    )}
                  >
                    {page}
                  </button>
                ))}
              </div>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="flex items-center gap-1 rounded-lg border px-3 py-2 text-sm transition-colors hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
              >
                下一页
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Initial State */}
      {!loading && !searched && (
        <div className="flex flex-col items-center justify-center rounded-xl border bg-card py-20">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <SearchIcon className="h-8 w-8 text-primary/60" />
          </div>
          <h3 className="mb-2 text-lg font-semibold text-muted-foreground">开始检索</h3>
          <p className="max-w-sm text-center text-sm text-muted-foreground">
            输入关键词搜索法律法规、司法案例、司法解释等法律资源
          </p>

          {/* Search History */}
          {history.length > 0 && (
            <div className="mt-4 w-full max-w-md">
              <p className="mb-2 text-center text-xs text-muted-foreground">最近搜索</p>
              <div className="flex flex-wrap justify-center gap-2">
                {history.slice(0, 5).map((h) => (
                  <button
                    key={h}
                    onClick={() => handleSearch(h)}
                    className="flex items-center gap-1 rounded-full border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                  >
                    <Clock className="h-3 w-3" />
                    {h}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Suggested tags */}
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {['劳动合同解除', '拖欠工资', '试用期', '工伤认定'].map((tag) => (
              <button
                key={tag}
                onClick={() => handleSearch(tag)}
                className="rounded-full border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary hover:text-primary"
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default React.memo(Search);
