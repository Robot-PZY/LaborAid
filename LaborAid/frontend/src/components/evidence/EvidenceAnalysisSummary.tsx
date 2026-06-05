import { useMemo } from 'react';

type Props = {
  analysis: string;
  className?: string;
};

/** 证据 AI 分析 — 单段话：材料说了什么、有何证明作用 */
export default function EvidenceAnalysisSummary({ analysis, className = '' }: Props) {
  const text = useMemo(() => {
    const raw = (analysis || '').trim();
    if (!raw) return '';
    return raw.replace(/\s+/g, ' ').slice(0, 80);
  }, [analysis]);

  if (!text) return null;

  return (
    <div
      className={`rounded-md border border-blue-100/80 bg-blue-50/40 px-3 py-2 text-xs leading-snug text-foreground/90 ${className}`}
    >
      <span className="font-medium text-blue-800/90">AI 解读：</span>
      <span className="line-clamp-2">{text}</span>
    </div>
  );
};
