import { Bot, CheckCircle2, Circle, Loader2, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DocRecommendation, DocRecommendationsResult } from '@/lib/doc-recommendations';

type Props = {
  data: DocRecommendationsResult | null;
  loading: boolean;
  generatingType: string | null;
  onGenerate: (docType: string) => void;
  onViewGenerated?: (docType: string, documentId?: number | null) => void;
};

export default function DocRecommendationPanel({
  data,
  loading,
  generatingType,
  onGenerate,
  onViewGenerated,
}: Props) {
  const items = data?.recommendations ?? [];
  const doneCount = items.filter((i) => i.generated).length;

  return (
    <div className="rounded-xl border border-accent/25 bg-gradient-to-br from-accent/5 via-card to-card p-4 sm:p-5 shadow-sm">
      <div className="flex flex-wrap items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-accent">
          <Bot className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-display text-base font-semibold">AI 文书推荐</p>
          {loading ? (
            <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              正在分析案情与证据材料…
            </p>
          ) : data ? (
            <>
              <p className="mt-1 text-sm text-muted-foreground">{data.summary}</p>
              {items.length > 0 && (
                <p className="mt-1 text-xs text-accent">
                  建议生成 {items.length} 份文书
                  {doneCount > 0 ? ` · 已完成 ${doneCount}/${items.length}` : ''}
                </p>
              )}
            </>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground">
              关联案件并填写案情后，将自动推荐应生成的文书清单。
            </p>
          )}
        </div>
      </div>

      {items.length > 0 && (
        <ul className="mt-4 space-y-2">
          {items.map((item) => (
            <RecommendationRow
              key={item.doc_type}
              item={item}
              busy={generatingType === item.doc_type}
              anyBusy={!!generatingType}
              onGenerate={() => onGenerate(item.doc_type)}
              onView={
                item.generated && onViewGenerated
                  ? () => onViewGenerated(item.doc_type, item.document_id)
                  : undefined
              }
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function RecommendationRow({
  item,
  busy,
  anyBusy,
  onGenerate,
  onView,
}: {
  item: DocRecommendation;
  busy: boolean;
  anyBusy: boolean;
  onGenerate: () => void;
  onView?: () => void;
}) {
  return (
    <li
      className={cn(
        'flex flex-col gap-2 rounded-lg border px-3 py-3 sm:flex-row sm:items-center sm:justify-between',
        item.generated ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-border/70 bg-card',
      )}
    >
      <div className="flex min-w-0 items-start gap-3">
        {item.generated ? (
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
        ) : (
          <Circle className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground/40" />
        )}
        <div className="min-w-0">
          <p className="text-sm font-medium">
            {item.priority}. {item.label}
            {item.generated && (
              <span className="ml-2 text-xs font-normal text-emerald-700 dark:text-emerald-300">
                已生成
              </span>
            )}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">{item.reason}</p>
        </div>
      </div>
      <div className="flex shrink-0 gap-2 pl-8 sm:pl-0">
        {item.generated && onView ? (
          <button
            type="button"
            onClick={onView}
            className="rounded-lg border px-3 py-1.5 text-xs font-medium hover:bg-muted"
          >
            查看
          </button>
        ) : !item.generated ? (
          <button
            type="button"
            onClick={onGenerate}
            disabled={anyBusy && !busy}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {busy ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            {busy ? '生成中…' : '生成此份'}
          </button>
        ) : null}
      </div>
    </li>
  );
}
