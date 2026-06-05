/**
 * 工具使用历史 — 本地按账号保存（企业查询、法规检索、维权咨询等）
 */

import { clearEnterpriseScanCache, removeEnterpriseScanCache } from '@/lib/enterprise-cache';
import { getIntakeResumeUrl } from '@/lib/intake-session';
import { STORAGE_KEYS } from '@/lib/storage-keys';

export type ToolHistoryKind =
  | 'enterprise'
  | 'search'
  | 'intake'
  | 'research'
  | 'contract'
  | 'docgen'
  | 'evidence';

export interface ToolHistoryEntry {
  id: string;
  kind: ToolHistoryKind;
  title: string;
  subtitle?: string;
  route: string;
  /** URL 查询参数或预填关键词 */
  query?: string;
  created_at: string;
}

const MAX_TOTAL = 40;
const MAX_PER_KIND: Partial<Record<ToolHistoryKind, number>> = {
  enterprise: 15,
  search: 20,
  intake: 10,
};

function storageKey(): string {
  try {
    const raw = localStorage.getItem('user');
    if (!raw) return STORAGE_KEYS.toolHistory;
    const user = JSON.parse(raw) as { id?: number };
    return user.id ? `${STORAGE_KEYS.toolHistory}:${user.id}` : STORAGE_KEYS.toolHistory;
  } catch {
    return STORAGE_KEYS.toolHistory;
  }
}

function readAll(): ToolHistoryEntry[] {
  try {
    const raw = localStorage.getItem(storageKey());
    const list = raw ? (JSON.parse(raw) as ToolHistoryEntry[]) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function notifyChanged() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event('laboraid-tool-history'));
  }
}

function writeAll(entries: ToolHistoryEntry[]) {
  try {
    localStorage.setItem(storageKey(), JSON.stringify(entries.slice(0, MAX_TOTAL)));
    notifyChanged();
  } catch {
    // quota / private mode
  }
}

function dedupeKey(entry: Pick<ToolHistoryEntry, 'kind' | 'title' | 'query'>): string {
  return `${entry.kind}:${(entry.query || entry.title).trim().toLowerCase()}`;
}

export function addToolHistory(
  entry: Omit<ToolHistoryEntry, 'id' | 'created_at'> & { id?: string; created_at?: string },
): ToolHistoryEntry {
  const now = entry.created_at || new Date().toISOString();
  const item: ToolHistoryEntry = {
    id: entry.id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    kind: entry.kind,
    title: entry.title.trim(),
    subtitle: entry.subtitle?.trim() || undefined,
    route: entry.route,
    query: entry.query?.trim() || undefined,
    created_at: now,
  };

  const key = dedupeKey(item);
  let list = readAll().filter((e) => dedupeKey(e) !== key);
  list.unshift(item);

  const kindLimit = MAX_PER_KIND[item.kind];
  if (kindLimit) {
    const sameKind = list.filter((e) => e.kind === item.kind);
    const other = list.filter((e) => e.kind !== item.kind);
    list = [...sameKind.slice(0, kindLimit), ...other];
    list.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }

  writeAll(list);
  return item;
}

export function listToolHistory(kind?: ToolHistoryKind, limit = 10): ToolHistoryEntry[] {
  let list = readAll();
  if (kind) list = list.filter((e) => e.kind === kind);
  return list.slice(0, limit);
}

export function clearToolHistory(kind?: ToolHistoryKind) {
  if (!kind) {
    writeAll([]);
    clearEnterpriseScanCache();
    return;
  }
  if (kind === 'enterprise') {
    clearEnterpriseScanCache();
  }
  writeAll(readAll().filter((e) => e.kind !== kind));
}

export function removeToolHistoryEntry(id: string) {
  const entry = readAll().find((e) => e.id === id);
  if (entry?.kind === 'enterprise' && entry.query) {
    removeEnterpriseScanCache(entry.query);
  }
  writeAll(readAll().filter((e) => e.id !== id));
}

/** 删除文书后同步移除本地「生成文书」历史（query 为 document id） */
export function removeToolHistoryForDocument(docId: number) {
  const key = String(docId);
  writeAll(
    readAll().filter(
      (e) => !(e.kind === 'docgen' && (e.query === key || e.query === String(docId))),
    ),
  );
}

export function notifyToolHistoryChanged() {
  notifyChanged();
}

export const TOOL_HISTORY_LABELS: Record<ToolHistoryKind, string> = {
  enterprise: '企业查询',
  search: '法规检索',
  intake: '维权咨询',
  research: '分析案情',
  contract: '审查合同',
  docgen: '生成文书',
  evidence: '整理证据',
};

export function toolHistoryNavigatePath(entry: ToolHistoryEntry): string {
  if (!entry.query) return entry.route;
  if (entry.kind === 'enterprise') {
    return `/enterprise?keyword=${encodeURIComponent(entry.query)}`;
  }
  if (entry.kind === 'search') {
    return `/search?q=${encodeURIComponent(entry.query)}`;
  }
  if (entry.kind === 'intake') {
    return getIntakeResumeUrl();
  }
  if (entry.kind === 'docgen' && entry.query) {
    return `/documents?docId=${encodeURIComponent(entry.query)}&worker=1`;
  }
  if (entry.kind === 'research' && entry.query) {
    return `/research?reportId=${encodeURIComponent(entry.query)}`;
  }
  return entry.route;
}
