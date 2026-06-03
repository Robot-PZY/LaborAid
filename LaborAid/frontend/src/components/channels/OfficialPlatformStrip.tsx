import {
  ArrowUpRight,
  ExternalLink,
  Gavel,
  HeartHandshake,
  Phone,
  Scale,
  Shield,
  Users,
} from 'lucide-react';
import {
  isNationalPlatformCategory,
  listNationalPlatforms,
  listPlatformCategories,
  type PlatformCategoryId,
} from '@/lib/channels';
import { SectionTitle, Surface } from '@/components/ui/primitives';
import { cn } from '@/lib/utils';

type Props = {
  onOpenPlatform: (category: PlatformCategoryId) => void;
};

const CATEGORY_ICON: Record<PlatformCategoryId, typeof Scale> = {
  wage_clue: Shield,
  labor_inspection: Scale,
  arbitration: Gavel,
  legal_aid: Phone,
  women_federation: HeartHandshake,
  union_hotline: Users,
};

const HOTLINES = [
  { phone: '12333', label: '人社咨询', hint: '劳动监察、仲裁、社保等' },
  { phone: '12348', label: '法律服务', hint: '免费法律咨询' },
  { phone: '12351', label: '工会维权', hint: '职工权益求助' },
] as const;

export default function OfficialPlatformStrip({ onOpenPlatform }: Props) {
  const categories = listPlatformCategories();
  const nationalDirect = listNationalPlatforms().filter(
    ({ key }) => !categories.some((c) => c.id === key),
  );

  return (
    <section id="official" className="space-y-8">
      <SectionTitle
        title="官方办事入口"
        description="点击下方卡片选择办事类型；监察、仲裁、法援在弹窗内选择省份后跳转"
      />

      <Surface padding="sm" className="border-border/60 bg-muted/15">
        <p className="text-xs font-medium text-muted-foreground">常用电话（可直接拨打）</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          {HOTLINES.map((item) => (
            <a
              key={item.phone}
              href={`tel:${item.phone}`}
              className="flex flex-col rounded-[var(--radius-md)] border border-border/70 bg-card px-4 py-3 transition-colors hover:border-accent/40 hover:bg-muted/30"
            >
              <span className="font-display text-xl font-semibold tabular-nums text-foreground">
                {item.phone}
              </span>
              <span className="mt-0.5 text-sm font-medium">{item.label}</span>
              <span className="mt-1 text-xs text-muted-foreground">{item.hint}</span>
            </a>
          ))}
        </div>
      </Surface>

      <div>
        <p className="mb-3 text-sm font-medium text-foreground">按办事类型</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {categories.map((cat) => {
            const Icon = CATEGORY_ICON[cat.id as PlatformCategoryId] ?? Scale;
            const isNational = isNationalPlatformCategory(cat.id as PlatformCategoryId);
            const isWomenUnion =
              cat.id === 'women_federation' || cat.id === 'union_hotline';

            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => onOpenPlatform(cat.id as PlatformCategoryId)}
                className={cn(
                  'group flex h-full flex-col rounded-[var(--radius-md)] border border-border/70 bg-card p-5 text-left shadow-card transition-all',
                  'hover:border-accent/40 hover:shadow-card-hover',
                  isWomenUnion && 'border-rose-200/60 bg-rose-50/30 dark:border-rose-900/35 dark:bg-rose-950/15',
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <span
                    className={cn(
                      'inline-flex rounded-lg p-2',
                      isWomenUnion ? 'bg-rose-500/12 text-rose-700 dark:text-rose-200' : 'bg-accent/10 text-accent',
                    )}
                  >
                    <Icon className="h-5 w-5" strokeWidth={1.75} />
                  </span>
                  {!isNational && (
                    <span className="shrink-0 rounded-full border border-border bg-muted/50 px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                      需选省份
                    </span>
                  )}
                </div>
                <p className="mt-3 text-base font-medium text-foreground">{cat.label}</p>
                <p className="mt-1.5 flex-1 text-sm leading-relaxed text-muted-foreground">
                  {cat.description}
                </p>
                <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-accent group-hover:underline">
                  选择并跳转
                  <ArrowUpRight className="h-4 w-4" />
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {nationalDirect.length > 0 && (
        <div>
          <p className="mb-3 text-sm font-medium text-foreground">全国平台直达</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {nationalDirect.map(({ key, link }) => (
              <a
                key={key}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex flex-col rounded-[var(--radius-md)] border border-border/70 bg-card p-5 shadow-card transition-all hover:border-accent/40 hover:shadow-card-hover"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="text-base font-medium">{link.label}</p>
                  <ExternalLink className="h-4 w-4 shrink-0 text-muted-foreground group-hover:text-accent" />
                </div>
                {link.hint && (
                  <p className="mt-2 flex-1 text-sm leading-relaxed text-muted-foreground">{link.hint}</p>
                )}
                {link.phone && (
                  <p className="mt-3 flex items-center gap-1.5 text-sm text-accent">
                    <Phone className="h-4 w-4" />
                    {link.phone}
                  </p>
                )}
              </a>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
