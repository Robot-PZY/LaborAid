import { useCallback, useEffect, useState } from 'react';
import { caseApi, type CaseAgentsList } from '@/lib/api';
import { loadChainAnalysis } from '@/lib/case-ai-cache';

export function useCaseAgents(caseId: number | null) {
  const [agents, setAgents] = useState<CaseAgentsList | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!caseId) {
      setAgents(null);
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
      const data = await caseApi.getCaseAgents(caseId, { chainScore });
      setAgents(data);
    } catch {
      setError('智能体状态暂时不可用');
      setAgents(null);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    void load();
  }, [load]);

  return { agents, loading, error, refresh: load };
}
