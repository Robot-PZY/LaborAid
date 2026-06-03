import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import type { CaseAgentStatusItem, CaseAgentsList } from '@/lib/api';
import { AGENTS } from '@/config/agents';
import { cn } from '@/lib/utils';

const STATUS_LABEL: Record<string, string> = {
  active: '主责',
  done: '完成',
  blocked: '受阻',
  idle: '待命',
  optional: '可选',
};

function statusClass(status: string, isActive: boolean) {
  if (isActive || status === 'active') {
    return 'border-violet-500/40 bg-violet-500/10 text-violet-900 dark:text-violet-100';
  }
  if (status === 'done') return 'border-emerald-500/30 bg-emerald-500/5 text-emerald-900 dark:text-emerald-100';
  if (status === 'blocked') return 'border-amber-500/35 bg-amber-500/5 text-amber-900 dark:text-amber-100';
  return 'border-border/60 bg-muted/30 text-muted-foreground';
}

function toolLabels(toolIds: string[]): string {
  const names = toolIds
    .map((id) => AGENTS.find((a) => a.id === id)?.shortName || AGENTS.find((a) => a.id === id)?.name)
    .filter(Boolean) as string[];
  return names.length ? names.join(' · ') : '';
}

interface CaseAgentsStripProps {
  agents: CaseAgentsList | null;
  loading?: boolean;
  error?: string;
  className?: string;
  compact?: boolean;
}

function AgentChip({
  agent,
  isActive,
  compact,
  onOpen,
}: {
  agent: CaseAgentStatusItem;
  isActive: boolean;
  compact?: boolean;
  onOpen: () => void;
}) {
  const tools = toolLabels(agent.tool_ids || []);

  return (
    <button
      type="button"
      onClick={onOpen}
      title={[agent.role, tools && `关联功能：${tools}`, agent.summary].filter(Boolean).join('\n')}
      className={cn(
        'cursor-pointer rounded-lg border px-2 py-1.5 text-left transition-colors hover:opacity-90',
        statusClass(agent.status, isActive),
        compact ? 'min-w-0 flex-1' : 'w-full',
      )}
    >
      <div className="flex items-center justify-between gap-1">
        <span className="truncate text-[11px] font-medium">{agent.name}</span>
        <span className="shrink-0 text-[9px] opacity-80">
          {isActive ? '主责' : STATUS_LABEL[agent.status] || agent.status}
        </span>
      </div>
      {!compact && tools && (
        <p className="mt-0.5 truncate text-[9px] opacity-75">含 {tools}</p>
      )}
      {!compact && (
        <p className="mt-0.5 line-clamp-2 text-[10px] leading-snug opacity-85">{agent.summary}</p>
      )}
    </button>
  );
}

export default function CaseAgentsStrip({
  agents,
  loading = false,
  error,
  className,
  compact = false,
}: CaseAgentsStripProps) {
  const navigate = useNavigate();
  const activeId = agents?.active_agent_id;

  const sorted = useMemo(() => {
    if (!agents?.agents.length) return [];
    const order = ['guidance', 'evidence', 'docgen', 'research', 'records'];
    return [...agents.agents].sort(
      (a, b) => order.indexOf(a.agent_id) - order.indexOf(b.agent_id),
    );
  }, [agents?.agents]);

  if (loading) {
    return (
      <div className={cn('text-[11px] text-muted-foreground', className)}>
        <Loader2 className="mr-1 inline h-3 w-3 animate-spin" />
        协作智能体状态加载中…
      </div>
    );
  }

  if (error || !sorted.length) return null;

  return (
    <div className={cn('space-y-2', className)}>
      <p className="text-[10px] leading-relaxed text-muted-foreground">
        按维权阶段协作；每个智能体可调度多项功能，非一功能一 Agent。
      </p>
      <div
        className={cn(
          compact ? 'flex flex-wrap gap-1.5' : 'grid gap-1.5 sm:grid-cols-2 lg:grid-cols-3',
        )}
      >
        {sorted.map((agent) => (
          <AgentChip
            key={agent.agent_id}
            agent={agent}
            isActive={agent.agent_id === activeId}
            compact={compact}
            onOpen={() => navigate(agent.route)}
          />
        ))}
      </div>
    </div>
  );
}
