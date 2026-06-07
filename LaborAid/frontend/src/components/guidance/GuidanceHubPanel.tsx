import { useNavigate } from 'react-router-dom';
import { ArrowUpRight, Compass } from 'lucide-react';
import { CAUSE_QUICK_ENTRIES } from '@/lib/guidance-labels';
import { SectionTitle, Surface } from '@/components/ui/primitives';

type GuidanceHubPanelProps = {
  showSectionTitle?: boolean;
  className?: string;
};

/** 首页底部横向栏：办事资源快捷入口 */
export default function GuidanceHubPanel({
  showSectionTitle = true,
  className,
}: GuidanceHubPanelProps) {
  const navigate = useNavigate();

  return (
    <section className={className}>
      {showSectionTitle && (
        <SectionTitle
          title="办事资源"
          description="监察、仲裁、12348、欠薪线索等全国与属地官方入口。"
        />
      )}

      <Surface padding="none" className="overflow-hidden">
        <div className="flex flex-col items-center gap-3 p-5 sm:flex-row sm:justify-between sm:p-6">
          <div className="flex flex-wrap items-center gap-1.5">
            <Compass className="mr-1 h-4 w-4 text-accent" />
            {CAUSE_QUICK_ENTRIES.map((c) => (
              <span
                key={c.key}
                className="rounded-full border border-border/70 bg-background px-3 py-1 text-xs font-medium text-muted-foreground"
              >
                {c.label}
              </span>
            ))}
          </div>
          <button
            type="button"
            onClick={() => navigate('/guidance')}
            className="inline-flex shrink-0 cursor-pointer items-center gap-1 text-xs font-medium text-accent hover:underline"
          >
            查看办事资源
            <ArrowUpRight className="h-3 w-3" />
          </button>
        </div>
      </Surface>
    </section>
  );
}
