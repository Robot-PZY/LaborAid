import { useCallback, useEffect, useState } from 'react';
import { caseApi, type CaseWorkflow } from '@/lib/api';
import { loadChainAnalysis } from '@/lib/case-ai-cache';

export function useCaseWorkflow(caseId: number | null) {
  const [workflow, setWorkflow] = useState<CaseWorkflow | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!caseId) {
      setWorkflow(null);
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
      const data = await caseApi.getCaseWorkflow(caseId, { chainScore });
      setWorkflow(data);
    } catch {
      setError('工作流状态暂时不可用');
      setWorkflow(null);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { workflow, loading, error, refresh: load };
}
