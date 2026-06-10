import { Badge } from '@/components/ui/primitives';
import type { IntakeAnalyzeResult } from '@/lib/api/intake';
import { FileText, Scale, AlertCircle, CheckCircle2 } from 'lucide-react';

interface AnalysisResultCardProps {
  result: IntakeAnalyzeResult;
}

export default function AnalysisResultCard({ result }: AnalysisResultCardProps) {
  return (
    <div className="rounded-lg border border-border/60 bg-card p-4 space-y-3 text-sm">
      {/* 纠纷类型 */}
      <div className="flex items-center gap-2">
        <Scale className="h-4 w-4 text-accent" />
        <span className="font-medium">纠纷类型：</span>
        <Badge tone="accent">{result.cause_label}</Badge>
      </div>

      {/* 案情摘要 */}
      {result.summary && (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">案情摘要</span>
          </div>
          <p className="text-muted-foreground pl-6 leading-relaxed">{result.summary}</p>
        </div>
      )}

      {/* 证据清单 */}
      {result.evidence_checklist.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span className="font-medium">建议准备的证据</span>
          </div>
          <ul className="pl-6 space-y-0.5">
            {result.evidence_checklist.slice(0, 5).map((item) => (
              <li key={item} className="text-muted-foreground flex items-start gap-2">
                <span className="text-accent mt-0.5">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 待补充信息 */}
      {result.missing_info.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <span className="font-medium">建议补充的信息</span>
          </div>
          <ul className="pl-6 space-y-0.5">
            {result.missing_info.slice(0, 3).map((item) => (
              <li key={item} className="text-muted-foreground flex items-start gap-2">
                <span className="text-amber-600 mt-0.5">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 可信度 */}
      <div className="pt-2 border-t border-border/40 flex items-center gap-2 text-xs text-muted-foreground">
        <span>分析可信度：</span>
        <span className={result.credibility.score >= 80 ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
          {result.credibility.score}分
        </span>
        {result.credibility.needs_human_review && (
          <span className="text-amber-600">（建议人工复核）</span>
        )}
      </div>
    </div>
  );
}
