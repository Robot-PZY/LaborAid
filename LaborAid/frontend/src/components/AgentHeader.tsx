import type { AgentConfig } from '@/config/agents';
import { cn } from '@/lib/utils';

interface AgentHeaderProps {
  agent: AgentConfig;
}

export default function AgentHeader({ agent }: AgentHeaderProps) {
  const Icon = agent.icon;

  return (
    <div className="mb-8 flex gap-4 border-b border-border/80 pb-6">
      <div
        className={cn(
          'flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--radius-md)] border border-border bg-muted/40',
          agent.color,
        )}
      >
        <Icon className="h-5 w-5" strokeWidth={1.75} />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">智能工具</p>
        <h1 className="font-display text-xl font-semibold tracking-tight sm:text-2xl">{agent.name}</h1>
        <p className="mt-1 max-w-xl text-sm leading-relaxed text-muted-foreground">{agent.description}</p>
      </div>
    </div>
  );
}
