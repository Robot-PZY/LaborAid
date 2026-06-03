/**
 * LaborAid localStorage keys — with legacy LawMind / LexNexus migration.
 */

export const STORAGE_KEYS = {
  prefs: 'laboraid_prefs',
  rememberEmail: 'laboraid_remember_email',
  docDrafts: 'laboraid_doc_drafts',
  searchHistory: 'laboraid_search_history',
  savedResults: 'laboraid_saved_results',
  toolHistory: 'laboraid_tool_history',
  activeCase: 'laboraid_active_case',
  intakeSession: 'laboraid_intake_session',
  caseChainPrefix: 'laboraid_case_chain:',
  apiUsage: 'laboraid_api_usage',
  generalConfig: 'laboraid_general_config',
  autoSavePrefix: 'laboraid_autosave_',
} as const;

/** Older key names → current key (try in order). */
const LEGACY_SOURCES: Record<string, string[]> = {
  [STORAGE_KEYS.prefs]: ['lawmind_prefs', 'lexnexus_prefs', 'LaborAid_prefs'],
  [STORAGE_KEYS.rememberEmail]: ['lawmind_remember_email', 'lexnexus_remember_email', 'LaborAid_remember_email'],
  [STORAGE_KEYS.docDrafts]: ['lawmind_doc_drafts', 'lexnexus_doc_drafts', 'LaborAid_doc_drafts'],
  [STORAGE_KEYS.searchHistory]: ['lawmind_search_history', 'lexnexus_search_history', 'LaborAid_search_history'],
  [STORAGE_KEYS.savedResults]: ['lawmind_saved_results', 'lexnexus_saved_results', 'LaborAid_saved_results'],
  [STORAGE_KEYS.apiUsage]: ['lawmind_api_usage', 'lexnexus_api_usage', 'LaborAid_api_usage'],
  [STORAGE_KEYS.generalConfig]: ['lawmind_general_config', 'lexnexus_general_config', 'LaborAid_general_config'],
};

export function migrateStorageKey(newKey: string): void {
  const legacyKeys = LEGACY_SOURCES[newKey];
  if (!legacyKeys?.length) return;
  try {
    if (localStorage.getItem(newKey)) return;
    for (const oldKey of legacyKeys) {
      const legacy = localStorage.getItem(oldKey);
      if (legacy) {
        localStorage.setItem(newKey, legacy);
        return;
      }
    }
  } catch {
    // ignore quota / private mode
  }
}

export function migrateAutoSaveKeys(): void {
  const legacyPrefixes = ['lawmind_autosave_', 'lexnexus_autosave_', 'LaborAid_autosave_'];
  const newPrefix = STORAGE_KEYS.autoSavePrefix;
  try {
    const toMigrate: Array<{ old: string; val: string }> = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key) continue;
      if (legacyPrefixes.some((p) => key.startsWith(p))) {
        const val = localStorage.getItem(key);
        if (val) toMigrate.push({ old: key, val });
      }
    }
    for (const { old, val } of toMigrate) {
      const legacyPrefix = legacyPrefixes.find((p) => old.startsWith(p))!;
      const newKey = newPrefix + old.slice(legacyPrefix.length);
      if (!localStorage.getItem(newKey)) {
        localStorage.setItem(newKey, val);
      }
    }
  } catch {
    // ignore
  }
}

export function migrateLegacyStorage(): void {
  Object.keys(LEGACY_SOURCES).forEach(migrateStorageKey);
  migrateAutoSaveKeys();
}

export function migrateRecentAgentsKey(): void {
  const newKey = 'laboraid_recent_agents';
  const legacyKeys = ['lexnexus_recent_agents', 'LaborAid_recent_agents'];
  try {
    if (localStorage.getItem(newKey)) return;
    for (const oldKey of legacyKeys) {
      const legacy = localStorage.getItem(oldKey);
      if (legacy) {
        localStorage.setItem(newKey, legacy);
        return;
      }
    }
  } catch {
    // ignore
  }
}
