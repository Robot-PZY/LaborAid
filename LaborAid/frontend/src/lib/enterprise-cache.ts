import type { EnterpriseScanResult } from '@/lib/api/enterprise';
import { STORAGE_KEYS } from '@/lib/storage-keys';

type CacheStore = Record<string, { saved_at: string; result: EnterpriseScanResult }>;

function cacheStorageKey(): string {
  try {
    const raw = localStorage.getItem('user');
    if (!raw) return `${STORAGE_KEYS.toolHistory}:enterprise_cache`;
    const user = JSON.parse(raw) as { id?: number };
    return user.id
      ? `${STORAGE_KEYS.toolHistory}:${user.id}:enterprise_cache`
      : `${STORAGE_KEYS.toolHistory}:enterprise_cache`;
  } catch {
    return `${STORAGE_KEYS.toolHistory}:enterprise_cache`;
  }
}

export function normalizeEnterpriseKey(searchKey: string): string {
  return searchKey.trim().toLowerCase();
}

function readStore(): CacheStore {
  try {
    const raw = localStorage.getItem(cacheStorageKey());
    const data = raw ? (JSON.parse(raw) as CacheStore) : {};
    return data && typeof data === 'object' ? data : {};
  } catch {
    return {};
  }
}

function writeStore(store: CacheStore): void {
  try {
    const keys = Object.keys(store);
    const trimmed =
      keys.length > 30
        ? Object.fromEntries(
            keys
              .sort((a, b) => new Date(store[b].saved_at).getTime() - new Date(store[a].saved_at).getTime())
              .slice(0, 30)
              .map((k) => [k, store[k]]),
          )
        : store;
    localStorage.setItem(cacheStorageKey(), JSON.stringify(trimmed));
  } catch {
    // ignore quota
  }
}

export function saveEnterpriseScanCache(result: EnterpriseScanResult): void {
  const key = normalizeEnterpriseKey(result.search_key);
  const store = readStore();
  store[key] = { saved_at: new Date().toISOString(), result };
  writeStore(store);
}

export function getEnterpriseScanCache(searchKey: string): EnterpriseScanResult | null {
  const key = normalizeEnterpriseKey(searchKey);
  return readStore()[key]?.result ?? null;
}

export function hasEnterpriseScanCache(searchKey: string): boolean {
  return getEnterpriseScanCache(searchKey) != null;
}

export function removeEnterpriseScanCache(searchKey: string): void {
  const key = normalizeEnterpriseKey(searchKey);
  const store = readStore();
  if (!store[key]) return;
  delete store[key];
  writeStore(store);
}

export function clearEnterpriseScanCache(): void {
  try {
    localStorage.removeItem(cacheStorageKey());
  } catch {
    // ignore
  }
}
