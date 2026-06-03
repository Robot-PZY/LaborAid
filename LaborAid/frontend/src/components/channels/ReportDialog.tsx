import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, ExternalLink, MapPin, Phone, X } from 'lucide-react';
import {
  getReportProvinces,
  hasProvincePlatformData,
  isNationalPlatformCategory,
  listPlatformCategories,
  resolvePlatformLink,
  type PlatformCategoryId,
} from '@/lib/channels';
import { STORAGE_KEYS } from '@/lib/storage-keys';
import { Button } from '@/components/ui/primitives';

const PROVINCIAL_CATEGORIES: PlatformCategoryId[] = [
  'labor_inspection',
  'arbitration',
  'legal_aid',
];

export interface ReportDialogProps {
  open: boolean;
  onClose: () => void;
  buttonLabel?: string;
  /** 打开时默认选中的办事类型 */
  initialCategory?: PlatformCategoryId;
}

function loadSavedProvince(provinces: string[]): string {
  try {
    const saved = localStorage.getItem(STORAGE_KEYS.reportProvince);
    if (saved && provinces.includes(saved)) return saved;
  } catch {
    // ignore
  }
  return provinces[0] || '';
}

function saveProvince(province: string): void {
  try {
    localStorage.setItem(STORAGE_KEYS.reportProvince, province);
  } catch {
    // ignore
  }
}

export default function ReportDialog({
  open,
  onClose,
  buttonLabel,
  initialCategory = 'labor_inspection',
}: ReportDialogProps) {
  const categories = listPlatformCategories();
  const provinces = getReportProvinces();
  const [category, setCategory] = useState<PlatformCategoryId>(initialCategory);
  const [province, setProvince] = useState(() => loadSavedProvince(provinces));
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    if (open) {
      setCategory(initialCategory);
      setProvince(loadSavedProvince(provinces));
      setConfirmed(false);
    }
  }, [open, initialCategory, provinces]);

  const needsProvince = !isNationalPlatformCategory(category);
  const link = useMemo(
    () => resolvePlatformLink(category, needsProvince ? province : undefined),
    [category, needsProvince, province],
  );
  const activeMeta = categories.find((c) => c.id === category);
  const provinceReady = !needsProvince || (province && hasProvincePlatformData(province));

  const handleOpen = () => {
    if (!confirmed || !provinceReady) return;
    if (needsProvince && province) saveProvince(province);
    window.open(link.url, '_blank', 'noopener,noreferrer');
    onClose();
    setConfirmed(false);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ink/50 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div
        role="dialog"
        aria-modal
        aria-labelledby="report-dialog-title"
        className="relative z-10 flex max-h-[90vh] w-full max-w-lg flex-col rounded-[var(--radius-lg)] border border-border bg-card shadow-elevated"
      >
        <div className="shrink-0 p-6 pb-0">
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground hover:bg-muted"
            aria-label="关闭"
          >
            <X className="h-4 w-4" />
          </button>

          <h2 id="report-dialog-title" className="font-display text-lg font-semibold pr-8">
            {buttonLabel || '官方办事入口'}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            本站不受理业务，仅跳转至政府官方渠道。{needsProvince ? '请先选择用工所在省份。' : '全国入口，无需选省。'}
          </p>

          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {categories.map((cat) => {
              const active = category === cat.id;
              const provincial = PROVINCIAL_CATEGORIES.includes(cat.id);
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => {
                    setCategory(cat.id);
                    setConfirmed(false);
                  }}
                  className={`rounded-[var(--radius-md)] border px-3 py-2.5 text-left text-sm transition-colors ${
                    active
                      ? 'border-accent bg-accent/10 text-foreground'
                      : 'border-border text-muted-foreground hover:bg-muted/50'
                  }`}
                >
                  <span className="font-medium">{cat.label}</span>
                  {provincial && (
                    <span className="mt-0.5 block text-[10px] text-muted-foreground">需选省份</span>
                  )}
                </button>
              );
            })}
          </div>
          {activeMeta && (
            <p className="mt-2 text-xs text-muted-foreground">{activeMeta.description}</p>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
          {needsProvince && (
            <div className="space-y-2">
              <label htmlFor="report-province" className="flex items-center gap-1.5 text-sm font-medium">
                <MapPin className="h-4 w-4 text-accent" />
                用工所在地（省级）
              </label>
              <select
                id="report-province"
                value={province}
                onChange={(e) => {
                  setProvince(e.target.value);
                  setConfirmed(false);
                }}
                className="input-field w-full text-sm"
              >
                {provinces.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                监察、仲裁、法援实行属地管辖，请按<strong className="font-medium text-foreground">实际用工省份</strong>选择。
              </p>
            </div>
          )}

          {'usedFallback' in link && link.usedFallback && (
            <div className="mt-3 flex items-start gap-2 rounded-[var(--radius-md)] border border-amber-200/80 bg-amber-50/70 px-3 py-2 text-xs text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/40 dark:text-amber-100">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              暂未配置「{province}」的专属链接，将跳转全国人社政务平台，请在平台内再选属地。
            </div>
          )}

          <div className="mt-4 rounded-[var(--radius-md)] border border-border/80 bg-muted/40 p-4 text-sm">
            {needsProvince && province && !link.usedFallback && (
              <p className="mb-2 text-xs font-medium text-accent">
                已匹配 {province} · {activeMeta?.label}
              </p>
            )}
            <p className="font-medium">{link.label}</p>
            {link.hint && <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{link.hint}</p>}
            {link.phone && (
              <p className="mt-2 flex items-center gap-1.5 text-xs">
                <Phone className="h-3.5 w-3.5" />
                可拨打 {link.phone}
              </p>
            )}
            <p className="mt-2 break-all text-[11px] text-muted-foreground/80">{link.url}</p>
          </div>

          {category === 'wage_clue' && (
            <p className="mt-3 text-xs text-muted-foreground">
              工程建设领域欠薪建议选「工程建设领域」填报，系统可关联项目总包信息。
            </p>
          )}
          {category === 'women_federation' && (
            <p className="mt-3 text-xs text-muted-foreground">
              妇联提供女职工权益保护咨询与反映渠道，可与劳动监察、仲裁配合使用；全国入口，不限定省份。
            </p>
          )}
          {category === 'union_hotline' && (
            <p className="mt-3 text-xs text-muted-foreground">
              可先联系用人单位工会；无工会或需上级协助时，可拨打 12351 或通过全国总工会网站求助。
            </p>
          )}
        </div>

        <div className="shrink-0 border-t border-border/60 p-6 pt-4">
          <label className="flex cursor-pointer items-start gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
              className="mt-0.5 rounded border-input"
            />
            我已知悉将离开劳权智助，前往第三方官方网站，办理结果以该网站为准。
          </label>

          <div className="mt-4 flex gap-2">
            <Button variant="outline" className="flex-1" onClick={onClose}>
              取消
            </Button>
            <Button
              variant="secondary"
              className="flex-1"
              disabled={!confirmed || !provinceReady}
              onClick={handleOpen}
            >
              <ExternalLink className="h-4 w-4" />
              前往{needsProvince && province ? `（${province}）` : ''}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
