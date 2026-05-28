import { caseApi, contractApi, documentApi, evidenceApi, researchApi } from '@/lib/api';
import type { IntakePlanStep } from '@/lib/intake-session';

export type CaseProgress = {
  caseId: number | null;
  hasCase: boolean;
  evidenceWithFile: number;
  documents: number;
  contractsWithFile: number;
  reports: number;
};

export const EMPTY_CASE_PROGRESS: CaseProgress = {
  caseId: null,
  hasCase: false,
  evidenceWithFile: 0,
  documents: 0,
  contractsWithFile: 0,
  reports: 0,
};

export async function fetchCaseProgress(caseId: number | null): Promise<CaseProgress> {
  if (!caseId) return { ...EMPTY_CASE_PROGRESS };

  try {
    const [evidence, documents, reports, contracts] = await Promise.all([
      evidenceApi.list(caseId).catch(() => []),
      documentApi.list({ case_id: caseId, limit: 200 }).catch(() => []),
      researchApi.list({ case_id: caseId, limit: 20 }).catch(() => []),
      contractApi.list(caseId).catch(() => []),
    ]);

    const evidenceWithFile = evidence.filter((e) => e.has_file).length;
    const contractsWithFile = contracts.filter(
      (c) => c.has_file || Boolean(c.parsed_text?.trim()) || Boolean(c.review_report?.trim()),
    ).length;

    return {
      caseId,
      hasCase: true,
      evidenceWithFile,
      documents: documents.length,
      contractsWithFile,
      reports: reports.length,
    };
  } catch {
    return { ...EMPTY_CASE_PROGRESS, caseId, hasCase: true };
  }
}

/** 维权安排某步是否确有成果（非仅点击「前往」） */
export function isIntakePlanStepDone(
  step: IntakePlanStep,
  progress: CaseProgress,
  createdCaseId?: number | null,
): boolean {
  const type = step.step_type || step.agent_id || '';

  if (type === 'create_case') {
    return Boolean(createdCaseId && progress.hasCase);
  }
  if (type === 'official_external' || step.action === 'external') {
    return false;
  }
  if (type === 'evidence') {
    return progress.evidenceWithFile > 0;
  }
  if (type === 'contract') {
    return progress.contractsWithFile > 0;
  }
  if (type === 'docgen') {
    return progress.documents > 0;
  }
  if (type === 'research') {
    return progress.reports > 0;
  }
  return false;
}

export function getActivePlanStepNumber(
  steps: IntakePlanStep[],
  progress: CaseProgress,
  createdCaseId?: number | null,
): number {
  if (!steps.length) return 1;
  const firstOpen = steps.find((s) => !isIntakePlanStepDone(s, progress, createdCaseId));
  return firstOpen?.step ?? steps[steps.length - 1]!.step;
}
