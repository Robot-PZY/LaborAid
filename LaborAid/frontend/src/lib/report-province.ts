import { listOfficialPlatformProvinces } from '@/lib/channels';
import { STORAGE_KEYS } from '@/lib/storage-keys';

const SHORT_ALIASES: Record<string, string> = {
  北京: '北京市',
  天津: '天津市',
  上海: '上海市',
  重庆: '重庆市',
  内蒙古: '内蒙古自治区',
  广西: '广西壮族自治区',
  西藏: '西藏自治区',
  宁夏: '宁夏回族自治区',
  新疆: '新疆维吾尔自治区',
};

/** 从 work_region 等自由文本中解析省级行政区名称。 */
export function parseProvinceFromWorkRegion(region: string | undefined | null): string | null {
  if (!region?.trim()) return null;
  const text = region.trim();
  const provinces = listOfficialPlatformProvinces();
  const byLength = [...provinces].sort((a, b) => b.length - a.length);
  for (const province of byLength) {
    if (text.startsWith(province) || text.includes(province)) {
      return province;
    }
  }
  for (const [alias, full] of Object.entries(SHORT_ALIASES)) {
    if (text.startsWith(alias) || text === alias) {
      return full;
    }
  }
  return null;
}

export function saveReportProvinceFromWorkRegion(region: string | undefined | null): void {
  const province = parseProvinceFromWorkRegion(region);
  if (!province) return;
  try {
    localStorage.setItem(STORAGE_KEYS.reportProvince, province);
  } catch {
    // ignore quota / private mode
  }
}
