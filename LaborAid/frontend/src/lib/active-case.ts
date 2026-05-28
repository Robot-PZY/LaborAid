/**
 * 当前维权案件 — 跨页面关联证据、文书等操作
 */

import { STORAGE_KEYS } from '@/lib/storage-keys';

const EVENT_NAME = 'laboraid-active-case';

function storageKey(): string {
  try {
    const raw = localStorage.getItem('user');
    if (!raw) return STORAGE_KEYS.activeCase;
    const user = JSON.parse(raw) as { id?: number };
    return user.id ? `${STORAGE_KEYS.activeCase}:${user.id}` : STORAGE_KEYS.activeCase;
  } catch {
    return STORAGE_KEYS.activeCase;
  }
}

export function getActiveCaseId(): number | null {
  try {
    const raw = localStorage.getItem(storageKey());
    if (!raw) return null;
    const id = Number(raw);
    return Number.isFinite(id) && id > 0 ? id : null;
  } catch {
    return null;
  }
}

export function setActiveCaseId(caseId: number | null): void {
  try {
    if (caseId == null) {
      localStorage.removeItem(storageKey());
    } else {
      localStorage.setItem(storageKey(), String(caseId));
    }
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event(EVENT_NAME));
    }
  } catch {
    // ignore
  }
}

export function subscribeActiveCase(listener: () => void): () => void {
  if (typeof window === 'undefined') return () => {};
  const handler = () => listener();
  window.addEventListener(EVENT_NAME, handler);
  window.addEventListener('storage', handler);
  return () => {
    window.removeEventListener(EVENT_NAME, handler);
    window.removeEventListener('storage', handler);
  };
}
