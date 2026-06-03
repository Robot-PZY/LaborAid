import { useState } from 'react';
import guidanceFallback from '@/config/labor/guidance.json';
import { PageHeader } from '@/components/ui/primitives';
import ServiceStrip from '@/components/service/ServiceStrip';
import ReportDialog from '@/components/channels/ReportDialog';
import OfficialPlatformStrip from '@/components/channels/OfficialPlatformStrip';
import type { PlatformCategoryId } from '@/lib/channels';

export default function Guidance() {
  const [platformOpen, setPlatformOpen] = useState(false);
  const [platformCategory, setPlatformCategory] = useState<PlatformCategoryId>('labor_inspection');
  const disclaimer =
    (guidanceFallback as { disclaimer?: string }).disclaimer ||
    '本站提供的信息与链接仅供参考，不构成法律意见。';

  const openPlatform = (category: PlatformCategoryId) => {
    setPlatformCategory(category);
    setPlatformOpen(true);
  };

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="维权服务"
        title="办事资源"
        description="申诉网站、热线电话与属地官方入口集中查阅；开始维权请返回首页选择专项或普通入口"
      />

      <OfficialPlatformStrip onOpenPlatform={openPlatform} />

      <p className="text-[11px] leading-relaxed text-muted-foreground">{disclaimer}</p>

      <ServiceStrip />

      <ReportDialog
        open={platformOpen}
        onClose={() => setPlatformOpen(false)}
        buttonLabel="官方办事入口"
        initialCategory={platformCategory}
      />
    </div>
  );
}
