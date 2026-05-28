import { useState } from 'react';
import { ArrowUpRight, Phone } from 'lucide-react';
import {
  listNationalPlatforms,
  listOfficialPlatformProvinces,
  resolvePlatformLink,
  type PlatformCategoryId,
} from '@/lib/channels';
import { SectionTitle } from '@/components/ui/primitives';

type Props = {
  onOpenPlatform: (category: PlatformCategoryId) => void;
  /** 女职工专区突出妇联/工会说明 */
  emphasizeWomenResources?: boolean;
};

const QUICK_CATEGORIES: { id: PlatformCategoryId; label: string }[] = [
  { id: 'wage_clue', label: '欠薪线索' },
  { id: 'labor_inspection', label: '劳动监察' },
  { id: 'arbitration', label: '劳动仲裁' },
  { id: 'legal_aid', label: '法律援助' },
  { id: 'women_federation', label: '妇联维权' },
  { id: 'union_hotline', label: '工会 12351' },
];

export default function OfficialPlatformStrip({ onOpenPlatform, emphasizeWomenResources }: Props) {
  const [previewProvince, setPreviewProvince] = useState(listOfficialPlatformProvinces()[0] || '');
  const provinces = listOfficialPlatformProvinces();
  const national = listNationalPlatforms().filter((n) => !QUICK_CATEGORIES.some((q) => q.id === n.key));

  return (
    <section>
      <SectionTitle
        title="官方办事入口"
        description={
          emphasizeWomenResources
            ? '含劳动监察、仲裁、12348、全国妇联与工会 12351；属地入口选省即可，妇联/工会为全国通道'
            : '按办事类型跳转，含妇联与工会全国入口；属地事项选省即可'
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        {QUICK_CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            type="button"
            onClick={() => onOpenPlatform(cat.id)}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors hover:border-accent/50 hover:bg-accent/5 ${
              cat.id === 'women_federation' || cat.id === 'union_hotline'
                ? 'border-rose-200/70 bg-rose-50/40 dark:border-rose-900/40 dark:bg-rose-950/20'
                : 'border-border'
            }`}
          >
            {cat.label}
            <ArrowUpRight className="ml-1 inline h-3 w-3" />
          </button>
        ))}
      </div>

      {emphasizeWomenResources && (
        <p className="mb-3 text-xs text-muted-foreground">
          女职工维权除人社渠道外，还可通过 <strong className="font-medium text-foreground">全国妇联</strong> 咨询反映、通过{' '}
          <strong className="font-medium text-foreground">工会 12351</strong> 寻求职工维权帮助。
        </p>
      )}

      <div className="grid gap-2 sm:grid-cols-2">
        {national.map(({ key, link }) => (
          <a
            key={key}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-[var(--radius-md)] border border-border/70 bg-card p-3 text-left text-sm transition-colors hover:bg-muted/30"
          >
            <p className="font-medium">{link.label}</p>
            {link.hint && (
              <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{link.hint}</p>
            )}
            {link.phone && (
              <p className="mt-2 flex items-center gap-1 text-xs text-accent">
                <Phone className="h-3 w-3" />
                {link.phone}
              </p>
            )}
          </a>
        ))}
      </div>

      {provinces.length > 0 && (
        <div className="mt-4 rounded-[var(--radius-md)] border border-border/70 bg-muted/20 p-4">
          <p className="text-xs font-medium">属地入口预览（任选省份，非绑定某一省）</p>
          <select
            value={previewProvince}
            onChange={(e) => setPreviewProvince(e.target.value)}
            className="input-field mt-2 max-w-xs"
          >
            {provinces.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <ul className="mt-3 space-y-2 text-xs">
            {(['labor_inspection', 'arbitration', 'legal_aid'] as const).map((cat) => {
              const link = resolvePlatformLink(cat, previewProvince);
              return (
                <li key={cat} className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-muted-foreground">
                    {cat === 'labor_inspection'
                      ? '监察'
                      : cat === 'arbitration'
                        ? '仲裁'
                        : '法援'}
                  </span>
                  <button
                    type="button"
                    onClick={() => onOpenPlatform(cat)}
                    className="font-medium hover:underline"
                  >
                    {link.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}
