/**
 * 案件级 AI 分析结果本地缓存（证据链等），按用户隔离。
 */

import type { ChainAnalysisResult } from '@/lib/api';
import { STORAGE_KEYS } from '@/lib/storage-keys';

export type CachedChainAnalysis = ChainAnalysisResult & {
  savedAt: string;
};

function userSuffix(): string {
  try {
    const raw = localStorage.getItem('user');
    if (!raw) return 'anon';
    const user = JSON.parse(raw) as { id?: number };
    return user.id ? String(user.id) : 'anon';
  } catch {
    return 'anon';
  }
}

function chainKey(caseId: number): string {
  return `${STORAGE_KEYS.caseChainPrefix}${userSuffix()}:${caseId}`;
}

export function saveChainAnalysis(caseId: number, result: ChainAnalysisResult): void {
  try {
    const payload: CachedChainAnalysis = {
      ...result,
      savedAt: new Date().toISOString(),
    };
    localStorage.setItem(chainKey(caseId), JSON.stringify(payload));
  } catch {
    // ignore quota
  }
}

export function loadChainAnalysis(caseId: number): CachedChainAnalysis | null {
  try {
    const raw = localStorage.getItem(chainKey(caseId));
    if (!raw) return null;
    return JSON.parse(raw) as CachedChainAnalysis;
  } catch {
    return null;
  }
}

export function clearChainAnalysis(caseId: number): void {
  try {
    localStorage.removeItem(chainKey(caseId));
  } catch {
    // ignore
  }
}
