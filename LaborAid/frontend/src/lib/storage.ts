/**
 * LaborAid storage utilities — preferences, auto-save, sensitive data cleanup.
 */

import { migrateLegacyStorage, STORAGE_KEYS } from './storage-keys';

const AUTO_SAVE_INTERVAL = 10_000;

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  lastPage: string;
  lastSearchQuery: string;
  lastDocType: string;
}

const DEFAULT_PREFS: UserPreferences = {
  theme: 'light',
  lastPage: '/',
  lastSearchQuery: '',
  lastDocType: '',
};

migrateLegacyStorage();

export function loadPreferences(): UserPreferences {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.prefs);
    if (!raw) return { ...DEFAULT_PREFS };
    return { ...DEFAULT_PREFS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

export function savePreferences(prefs: Partial<UserPreferences>): void {
  const current = loadPreferences();
  const merged = { ...current, ...prefs };
  localStorage.setItem(STORAGE_KEYS.prefs, JSON.stringify(merged));
}

export function autoSave(key: string, value: string): void {
  try {
    localStorage.setItem(STORAGE_KEYS.autoSavePrefix + key, JSON.stringify({
      value,
      savedAt: new Date().toISOString(),
    }));
  } catch { /* quota exceeded */ }
}

export function loadAutoSave(key: string): { value: string; savedAt: string } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.autoSavePrefix + key);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearAutoSave(key: string): void {
  localStorage.removeItem(STORAGE_KEYS.autoSavePrefix + key);
}

export function clearAllAutoSaves(): void {
  const keysToRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key?.startsWith(STORAGE_KEYS.autoSavePrefix)) {
      keysToRemove.push(key);
    }
  }
  keysToRemove.forEach((key) => localStorage.removeItem(key));
}

export function clearSensitiveData(): void {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  clearAllAutoSaves();
  localStorage.removeItem(STORAGE_KEYS.docDrafts);
  localStorage.removeItem(STORAGE_KEYS.searchHistory);
}

export function startAutoSaveInterval(
  key: string,
  getValue: () => string,
  intervalMs: number = AUTO_SAVE_INTERVAL,
): number {
  return window.setInterval(() => {
    const value = getValue();
    if (value.trim()) {
      autoSave(key, value);
    }
  }, intervalMs);
}

export { STORAGE_KEYS };
