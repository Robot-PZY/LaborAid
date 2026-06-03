import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { Surface } from '@/components/ui/primitives';

/** 专项页指向维权指引中的唯一官方入口区块，避免重复罗列相同链接 */
export default function OfficialEntryHint() {
  return (
    <Surface
      padding="sm"
      className="flex flex-col gap-2 border-border/60 bg-muted/20 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="text-sm text-muted-foreground">
        劳动监察、仲裁、12348、欠薪线索等全国入口统一在维权指引页维护。
      </p>
      <Link
        to="/guidance#official"
        className="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-accent hover:underline"
      >
        官方办事入口
        <ArrowUpRight className="h-3.5 w-3.5" />
      </Link>
    </Surface>
  );
}
