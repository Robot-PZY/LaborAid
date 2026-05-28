import { useEffect, useState } from 'react';
import { Clock, X } from 'lucide-react';
import {
  clearToolHistory,
  listToolHistory,
  removeToolHistoryEntry,
  TOOL_HISTORY_LABELS,
  toolHistoryNavigatePath,
  type ToolHistoryEntry,
  type ToolHistoryKind,
} from '@/lib/tool-history';

function useToolHistory(kind?: ToolHistoryKind, limit = 8) {
  const [items, setItems] = useState<ToolHistoryEntry[]>(() => listToolHistory(kind, limit));

  useEffect(() => {
    setItems(listToolHistory(kind, limit));
    const refresh = () => setItems(listToolHistory(kind, limit));
    window.addEventListener('storage', refresh);
    window.addEventListener('laboraid-tool-history', refresh);
    return () => {
      window.removeEventListener('storage', refresh);
      window.removeEventListener('laboraid-tool-history', refresh);
    };
  }, [kind, limit]);

  return items;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

type ToolHistoryPanelProps = {
  kind?: ToolHistoryKind;
  limit?: number;
  title?: string;
  onSelect?: (entry: ToolHistoryEntry) => void;
  compact?: boolean;
};

export default function ToolHistoryPanel({
  kind,
  limit = 8,
  title = '最近使用',
  onSelect,
  compact = false,
}: ToolHistoryPanelProps) {
  const items = useToolHistory(kind, limit);

  if (items.length === 0) return null;

  const handleClear = () => {
    clearToolHistory(kind);
  };

  return (
    <div className={compact ? 'space-y-2' : 'space-y-3'}>
      <div className="flex items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          {title}
        </p>
        <button
          type="button"
          onClick={handleClear}
          className="text-[11px] text-muted-foreground hover:text-foreground"
        >
          清空
        </button>
      </div>

      {compact ? (
        <div className="flex flex-wrap gap-2">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect?.(item)}
              className="max-w-full truncate rounded-full border border-border/70 bg-muted/40 px-3 py-1 text-xs hover:bg-muted"
              title={item.subtitle || item.title}
            >
              {item.title}
            </button>
          ))}
        </div>
      ) : (
        <ul className="divide-y divide-border/60 rounded-[var(--radius-md)] border border-border/70 bg-card">
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-2 px-3 py-2.5">
              <button
                type="button"
                onClick={() => onSelect?.(item)}
                className="min-w-0 flex-1 text-left"
              >
                <p className="truncate text-sm font-medium">{item.title}</p>
                <p className="text-[11px] text-muted-foreground">
                  {TOOL_HISTORY_LABELS[item.kind]}
                  {item.subtitle ? ` · ${item.subtitle}` : ''}
                  {' · '}
                  {formatTime(item.created_at)}
                </p>
              </button>
              <button
                type="button"
                aria-label="删除"
                onClick={() => {
                  removeToolHistoryEntry(item.id);
                }}
                className="shrink-0 rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export { useToolHistory, toolHistoryNavigatePath };
export { notifyToolHistoryChanged } from '@/lib/tool-history';
