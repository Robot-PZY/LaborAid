/** 维权前台会话 — 跨页面预填、跳转；本地缓存 + 服务端持久化（重新登录可恢复） */

import { setActiveCaseId } from '@/lib/active-case';
import { STORAGE_KEYS } from '@/lib/storage-keys';

export interface IntakeParties {
  plaintiff?: string | null;
  defendant?: string | null;
}

export interface IntakeCredibility {
  score: number;
  needs_human_review: boolean;
  reason: string;
}

export interface IntakeToolPrefill {
  title?: string | null;
  case_type?: string | null;
  description?: string | null;
  plaintiff?: string | null;
  defendant?: string | null;
  caseFacts?: string | null;
  docType?: string | null;
  docMode?: 'single' | 'bundle' | null;
  bundleDocTypes?: string[];
  searchQuery?: string | null;
  checklist?: string[];
  channelId?: string | null;
  scenarioId?: string | null;
}

export interface IntakeRecommendedTool {
  agent_id: string;
  priority: number;
  reason: string;
  action: string;
  prefill: IntakeToolPrefill;
}

export interface IntakeOfficialLink {
  id: string;
  title: string;
  when?: string;
}

export interface IntakePlanStep {
  step: number;
  step_type: string;
  label: string;
  reason: string;
  agent_id?: string | null;
  action: string;
  prefill: IntakeToolPrefill;
  platform_category?: string | null;
  official_link_id?: string | null;
  optional?: boolean;
}

export interface IntakeActionPlan {
  plan_id: string;
  title: string;
  steps: IntakePlanStep[];
  current_step: number;
}

export interface IntakeSession {
  id: string;
  causeType: string;
  causeLabel: string;
  summary: string;
  parties: IntakeParties;
  missingInfo: string[];
  evidenceChecklist: string[];
  recommendedTools: IntakeRecommendedTool[];
  officialLinks: IntakeOfficialLink[];
  credibility: IntakeCredibility;
  searchQuery: string;
  caseFacts: string;
  channelId?: string | null;
  scenarioId?: string | null;
  actionPlan?: IntakeActionPlan | null;
  currentStep?: number;
  createdCaseId?: number;
  /** 用户原始描述，用于回到咨询方案页时恢复 */
  inputText?: string;
  intakeMode?: 'structured' | 'freeform';
  structuredAnswers?: Record<string, string>;
  createdAt: string;
  updatedAt?: string;
}

const LEGACY_SESSION_KEY = 'laboraid_intake_session';
const SESSION_EVENT = 'laboraid-intake-session';

let syncTimer: ReturnType<typeof setTimeout> | null = null;
let hydratePromise: Promise<IntakeSession | null> | null = null;

function storageKey(): string {
  try {
    const raw = localStorage.getItem('user');
    if (!raw) return STORAGE_KEYS.intakeSession;
    const user = JSON.parse(raw) as { id?: number };
    return user.id ? `${STORAGE_KEYS.intakeSession}:${user.id}` : STORAGE_KEYS.intakeSession;
  } catch {
    return STORAGE_KEYS.intakeSession;
  }
}

function readLocalRaw(): string | null {
  try {
    return localStorage.getItem(storageKey());
  } catch {
    return null;
  }
}

function writeLocal(session: IntakeSession): void {
  try {
    localStorage.setItem(storageKey(), JSON.stringify(session));
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event(SESSION_EVENT));
    }
  } catch {
    // ignore quota
  }
}

function migrateLegacySessionStorage(): void {
  try {
    if (readLocalRaw()) return;
    const legacy = sessionStorage.getItem(LEGACY_SESSION_KEY);
    if (legacy) {
      localStorage.setItem(storageKey(), legacy);
      sessionStorage.removeItem(LEGACY_SESSION_KEY);
    }
  } catch {
    // ignore
  }
}

function scheduleSyncToServer(session: IntakeSession): void {
  if (!localStorage.getItem('token')) return;
  if (syncTimer) clearTimeout(syncTimer);
  syncTimer = setTimeout(() => {
    import('@/lib/api/intake')
      .then(({ intakeApi }) => intakeApi.saveSession(session))
      .catch(() => {
        // 离线或网络错误时仅保留本地
      });
  }, 400);
}

function sessionTimestamp(session: IntakeSession): number {
  const raw = session.updatedAt || session.createdAt;
  const t = Date.parse(raw);
  return Number.isFinite(t) ? t : 0;
}

export function saveIntakeSession(
  data: Omit<IntakeSession, 'id' | 'createdAt'> & { id?: string; createdAt?: string },
): IntakeSession {
  const now = new Date().toISOString();
  const existing = loadIntakeSession();
  const session: IntakeSession = {
    ...data,
    id: data.id || existing?.id || `intake_${Date.now()}`,
    createdAt: data.createdAt || existing?.createdAt || now,
    updatedAt: now,
  };
  writeLocal(session);
  scheduleSyncToServer(session);
  return session;
}

export function subscribeIntakeSession(listener: () => void): () => void {
  if (typeof window === 'undefined') return () => {};
  const handler = () => listener();
  window.addEventListener(SESSION_EVENT, handler);
  window.addEventListener('storage', handler);
  return () => {
    window.removeEventListener(SESSION_EVENT, handler);
    window.removeEventListener('storage', handler);
  };
}

export function loadIntakeSession(): IntakeSession | null {
  migrateLegacySessionStorage();
  try {
    const raw = readLocalRaw();
    if (!raw) return null;
    return JSON.parse(raw) as IntakeSession;
  } catch {
    return null;
  }
}

/** 登录后从服务端拉取维权方案，与本地合并（取较新的一份） */
export async function hydrateIntakeSessionFromServer(): Promise<IntakeSession | null> {
  if (!localStorage.getItem('token')) return loadIntakeSession();
  if (hydratePromise) return hydratePromise;

  hydratePromise = (async () => {
    migrateLegacySessionStorage();
    const local = loadIntakeSession();
    try {
      const { intakeApi } = await import('@/lib/api/intake');
      const remote = await intakeApi.getSession();
      if (!remote?.session) {
        if (local && hasActiveIntakePlan(local)) {
          scheduleSyncToServer(local);
        }
        return local;
      }
      const remoteSession = remote.session as IntakeSession;
      const remoteTs = Date.parse(remote.updated_at);
      const localTs = local ? sessionTimestamp(local) : 0;
      if (!local || (Number.isFinite(remoteTs) && remoteTs >= localTs)) {
        writeLocal({
          ...remoteSession,
          updatedAt: remote.updated_at || remoteSession.updatedAt,
        });
        if (remoteSession.createdCaseId) {
          setActiveCaseId(remoteSession.createdCaseId);
        }
        return remoteSession;
      }
      scheduleSyncToServer(local);
      return local;
    } catch {
      return local;
    } finally {
      hydratePromise = null;
    }
  })();

  return hydratePromise;
}

export function updateIntakeCaseId(caseId: number): void {
  const s = loadIntakeSession();
  if (!s) return;
  saveIntakeSession({ ...s, createdCaseId: caseId });
  setActiveCaseId(caseId);
}

export function clearIntakeSession(): void {
  try {
    localStorage.removeItem(storageKey());
    sessionStorage.removeItem(LEGACY_SESSION_KEY);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event(SESSION_EVENT));
    }
  } catch {
    // ignore
  }
  if (localStorage.getItem('token')) {
    import('@/lib/api/intake')
      .then(({ intakeApi }) => intakeApi.clearSession())
      .catch(() => {});
  }
}

/** 是否仍有可恢复的维权咨询方案 */
export function hasActiveIntakePlan(session?: IntakeSession | null): boolean {
  const s = session ?? loadIntakeSession();
  return Boolean(s?.actionPlan?.steps?.length || s?.recommendedTools?.length);
}

export function getAgentRoute(agentId: string, prefill?: IntakeToolPrefill): string {
  if (agentId === 'channels' && prefill?.channelId) {
    return `/channels/${prefill.channelId}`;
  }
  const routes: Record<string, string> = {
    cases: '/cases',
    evidence: '/evidence',
    docgen: '/documents',
    contract: '/contracts',
    search: '/search',
    guidance: '/guidance',
    channels: prefill?.channelId ? `/channels/${prefill.channelId}` : '/channels',
    vault: '/vault',
    research: '/research',
  };
  return routes[agentId] || '/';
}

export function buildPrefillSearchParams(
  agentId: string,
  session: IntakeSession,
  tool?: IntakeRecommendedTool | IntakePlanStep,
): string {
  const prefill = tool?.prefill || {};
  const params = new URLSearchParams();
  params.set('from', 'intake');
  params.set('worker', '1');

  if (session.createdCaseId) params.set('caseId', String(session.createdCaseId));
  if (session.causeType) params.set('cause', session.causeType);

  if (agentId === 'search') {
    const q =
      ('searchQuery' in prefill && prefill.searchQuery) ||
      session.searchQuery ||
      session.summary;
    params.set('q', q);
  }
  if (agentId === 'docgen') {
    const docType =
      prefill.docType ||
      session.recommendedTools.find((t) => t.agent_id === 'docgen')?.prefill.docType;
    if (docType) params.set('type', docType);
    const mode = prefill.docMode;
    if (mode === 'single' || mode === 'bundle') params.set('mode', mode);
    if (prefill.bundleDocTypes?.length) params.set('bundle', prefill.bundleDocTypes.join(','));
    if (session.caseFacts) params.set('facts', session.caseFacts.slice(0, 500));
  }
  if (agentId === 'channels') {
    const scenarioId = prefill.scenarioId || session.scenarioId;
    if (scenarioId) params.set('scenario', scenarioId);
  }
  if (agentId === 'guidance' && session.causeType) {
    params.set('cause', session.causeType);
  }
  if (agentId === 'evidence') {
    const list =
      prefill.checklist?.length ? prefill.checklist : session.evidenceChecklist;
    if (list?.length) params.set('checklist', list.join('|'));
  }

  return params.toString();
}
