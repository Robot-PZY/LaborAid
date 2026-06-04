import { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import MarkdownRenderer from '@/lib/markdown';
import { parseEvidenceAnalysis } from '@/lib/evidence-analysis-parse';

type Props = {
  analysis: string;
  className?: string;
};

export default function EvidenceAnalysisSummary({ analysis, className = '' }: Props) {
  const [showFull, setShowFull] = useState(false);
  const { sections } = useMemo(() => parseEvidenceAnalysis(analysis), [analysis]);

  const useCards = sections.length >= 2;

  return (
    <div className={className}>
      {useCards ? (
        <div className="grid gap-2 sm:grid-cols-2">
          {sections.map((s, i) => (
            <div
              key={`${s.title}-${i}`}
              className="rounded-lg border border-blue-100 bg-white/80 p-3 shadow-sm"
            >
              <p className="text-xs font-semibold text-blue-900">{s.title}</p>
              <p className="mt-1.5 text-xs leading-relaxed text-foreground line-clamp-4">
                {s.body}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-blue-100 bg-white/80 p-3 text-sm leading-relaxed text-foreground line-clamp-6">
          {sections[0]?.body || analysis.slice(0, 400)}
        </div>
      )}

      <button
        type="button"
        onClick={() => setShowFull((v) => !v)}
        className="mt-2 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        {showFull ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        {showFull ? '收起全文' : '展开完整分析'}
      </button>

      {showFull && (
        <div className="mt-2 max-h-72 overflow-y-auto rounded-lg border bg-muted/30 p-3 prose-sm max-w-none">
          <MarkdownRenderer content={analysis} />
        </div>
      )}
    </div>
  );
}
