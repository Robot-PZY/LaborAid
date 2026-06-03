import { useCallback, useEffect, useState } from 'react';
import { caseApi, type CaseAgentNextStep } from '@/lib/api';
import { loadChainAnalysis } from '@/lib/case-ai-cache';

export function useCaseAgentStep(caseId: number | null) {
  const [step, setStep] = useState<CaseAgentNextStep | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!caseId) {
      setStep(null);
      setError('');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const cached = loadChainAnalysis(caseId);
      const raw = cached?.completeness_score;
      const chainScore =
        raw != null && !Number.isNaN(Number(raw)) ? Math.round(Number(raw)) : undefined;
      const data = await caseApi.getAgentNextStep(caseId, { chainScore });
      setStep(data);
    } catch {
      setError('维权助手暂时不可用，请稍后重试');
      setStep(null);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { step, loading, error, refresh: load };
}
