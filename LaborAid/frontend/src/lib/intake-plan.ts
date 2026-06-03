import type { NavigateFunction } from 'react-router-dom';
import { resolvePlatformLink, type PlatformCategoryId } from '@/lib/channels';
import platformsData from '@/config/labor/official-platforms.json';
import { intakeApi, type IntakeAnalyzeResult } from '@/lib/api/intake';
import { withCaseTitleDatePrefix } from '@/lib/case-title';
import {
  buildPrefillSearchParams,
  getAgentRoute,
  loadIntakeSession,
  saveIntakeSession,
  updateIntakeCaseId,
  type IntakeActionPlan,
  type IntakePlanStep,
  type IntakeSession,
} from '@/lib/intake-session';

const NATIONAL_EXTRA_KEYS: Record<string, keyof typeof platformsData.national> = {
  '12348': 'legal_12348',
  mohrss: 'mohrss_service',
  npc_laws: 'npc_laws',
};

const PLATFORM_CATEGORIES = new Set<PlatformCategoryId>([
  'wage_clue',
  'labor_inspection',
  'arbitration',
  'legal_aid',
  'women_federation',
  'union_hotline',
]);

export function resolveStepExternalUrl(step: IntakePlanStep): string | null {
  const raw = step.platform_category || step.official_link_id;
  if (!raw) return null;
  return resolveOfficialLinkUrl(raw);
}

export function resolveOfficialLinkUrl(linkId: string): string | null {
  const extra = NATIONAL_EXTRA_KEYS[linkId];
  if (extra && platformsData.national[extra]?.url) {
    return platformsData.national[extra].url;
  }
  if (PLATFORM_CATEGORIES.has(linkId as PlatformCategoryId)) {
    return resolvePlatformLink(linkId as PlatformCategoryId).url;
  }
  return null;
}

export function sessionToAnalyzeResult(session: IntakeSession): IntakeAnalyzeResult {
  return {
    cause_type: session.causeType,
    cause_label: session.causeLabel,
    summary: session.summary,
    parties: session.parties,
    missing_info: session.missingInfo,
    evidence_checklist: session.evidenceChecklist,
    recommended_tools: session.recommendedTools.map((t) => ({
      agent_id: t.agent_id,
      priority: t.priority,
      reason: t.reason,
      action: t.action,
      prefill: t.prefill as Record<string, unknown>,
    })),
    official_links: session.officialLinks,
    credibility: session.credibility,
    extracted_from_images: '',
    search_query: session.searchQuery,
    channel_id: session.channelId ?? null,
    scenario_id: session.scenarioId ?? null,
    action_plan: session.actionPlan ?? null,
  };
}

export function resultToSession(data: IntakeAnalyzeResult, caseFacts: string): IntakeSession {
  return saveIntakeSession({
    causeType: data.cause_type,
    causeLabel: data.cause_label,
    inputText: caseFacts,
    summary: data.summary,
    parties: data.parties,
    missingInfo: data.missing_info,
    evidenceChecklist: data.evidence_checklist,
    recommendedTools: data.recommended_tools.map((t) => ({
      ...t,
      prefill: t.prefill as IntakeSession['recommendedTools'][0]['prefill'],
    })),
    officialLinks: data.official_links,
    credibility: data.credibility,
    searchQuery: data.search_query,
    caseFacts,
    channelId: data.channel_id ?? null,
    scenarioId: data.scenario_id ?? null,
    actionPlan: data.action_plan ?? null,
    currentStep: data.action_plan?.current_step ?? 1,
    intakeMode: data.intake_mode === 'structured' ? 'structured' : 'freeform',
    structuredAnswers: (data.structured_answers as Record<string, string> | undefined) ?? undefined,
  });
}

export async function executePlanStep(
  step: IntakePlanStep,
  session: IntakeSession,
  navigate: NavigateFunction,
): Promise<IntakeSession> {
  if (step.step_type === 'official_external' || step.action === 'external') {
    const url = resolveStepExternalUrl(step);
    if (url) window.open(url, '_blank', 'noopener,noreferrer');
    return saveIntakeSession({ ...session, currentStep: step.step + 1 });
  }

  if (step.action === 'create_case' || step.step_type === 'create_case') {
    const pf = step.prefill || {};
    const rawTitle = pf.title || `${session.causeLabel}维权`;
    const created = await intakeApi.createCase({
      title: withCaseTitleDatePrefix(rawTitle),
      case_type: pf.case_type || 'administrative_labor',
      description: pf.description || session.caseFacts,
      plaintiff: pf.plaintiff || session.parties.plaintiff || undefined,
      defendant: pf.defendant || session.parties.defendant || undefined,
      cause_type: session.causeType,
    });
    updateIntakeCaseId(created.id);
    return saveIntakeSession({
      ...loadIntakeSession()!,
      createdCaseId: created.id,
      currentStep: step.step + 1,
    });
  }

  const route = getAgentRoute(step.agent_id || '', step.prefill);
  const toolLike = {
    agent_id: step.agent_id || '',
    priority: step.step,
    reason: step.reason,
    action: step.action,
    prefill: step.prefill,
  };
  const qs = buildPrefillSearchParams(step.agent_id || '', session, toolLike);
  const next = saveIntakeSession({ ...session, currentStep: step.step + 1 });
  navigate(`${route}?${qs}`);
  return next;
}

export function getActivePlanStep(session: IntakeSession): IntakePlanStep | null {
  const plan = session.actionPlan;
  if (!plan?.steps?.length) return null;
  const idx = session.currentStep ?? 1;
  return plan.steps.find((s) => s.step === idx) ?? plan.steps[0];
}

/** 按推荐计划：先建案，再跳转第一个关键内链步骤（专区 > 证据） */
export async function startRecommendedPlan(
  session: IntakeSession,
  navigate: NavigateFunction,
): Promise<IntakeSession> {
  const plan = session.actionPlan;
  if (!plan?.steps.length) return session;

  let current = session;

  const createStep = plan.steps.find((s) => s.step_type === 'create_case');
  if (createStep && !current.createdCaseId) {
    current = await executePlanStep(createStep, current, navigate);
  }

  const navigatePriority = ['evidence', 'docgen', 'research'];
  for (const type of navigatePriority) {
    const step = plan.steps.find((s) => s.step_type === type);
    if (step) {
      await executePlanStep(step, current, navigate);
      return loadIntakeSession() || current;
    }
  }

  return current;
}

export function buildFallbackPlanFromTools(
  result: IntakeAnalyzeResult,
): IntakeActionPlan | null {
  if (!result.recommended_tools.length) return null;
  return {
    plan_id: result.cause_type,
    title: `您的维权安排：${result.cause_label}`,
    current_step: 1,
    steps: result.recommended_tools.map((t, i) => ({
      step: i + 1,
      step_type: t.action === 'create_case' ? 'create_case' : t.agent_id,
      label: t.agent_id,
      reason: t.reason,
      agent_id: t.agent_id,
      action: t.action,
      prefill: t.prefill as IntakePlanStep['prefill'],
    })),
  };
}
