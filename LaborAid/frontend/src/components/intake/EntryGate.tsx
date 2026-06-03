import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { HeartHandshake, MessageSquareText } from 'lucide-react';
import ChannelIntakeWizard from '@/components/intake/ChannelIntakeWizard';
import IntakeDesk from '@/components/intake/IntakeDesk';
import { Surface, Badge } from '@/components/ui/primitives';
import { cn } from '@/lib/utils';

type Props = {
  initialPath?: EntryPath;
  initialChannelId?: string | null;
  initialScenarioId?: string | null;
};

export type EntryPath = 'choose' | 'special' | 'general';

export default function EntryGate(_props: Props) {
  const [searchParams, setSearchParams] = useSearchParams();

  const initial = useMemo(() => {
    const intake = searchParams.get('intake');
    if (intake === 'special') {
      return {
        path: 'special' as EntryPath,
        channelId: searchParams.get('channel'),
        scenarioId: searchParams.get('scenario'),
      };
    }
    if (intake === 'general') {
      return { path: 'general' as EntryPath, channelId: null, scenarioId: null };
    }
    return { path: 'choose' as EntryPath, channelId: null, scenarioId: null };
  }, [searchParams]);

  const [path, setPath] = useState<EntryPath>(initial.path);

  useEffect(() => {
    setPath(initial.path);
  }, [initial.path]);

  const clearIntakeParams = () => {
    const next = new URLSearchParams(searchParams);
    next.delete('intake');
    next.delete('channel');
    next.delete('scenario');
    setSearchParams(next, { replace: true });
  };

  const goChoose = () => {
    setPath('choose');
    clearIntakeParams();
  };

  const goSpecial = () => {
    setPath('special');
    const next = new URLSearchParams(searchParams);
    next.set('intake', 'special');
    setSearchParams(next, { replace: true });
  };

  const goGeneral = () => {
    setPath('general');
    const next = new URLSearchParams(searchParams);
    next.set('intake', 'general');
    next.delete('channel');
    next.delete('scenario');
    setSearchParams(next, { replace: true });
  };

  if (path === 'special') {
    return (
      <div id="intake-desk" className="scroll-mt-24">
        <Surface padding="lg" className="border-accent/20 bg-gradient-to-br from-card to-accent/5">
          <Badge tone="accent">专项通道</Badge>
          <h2 className="mt-2 font-display text-lg font-semibold">按身份填写案情</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            选择身份与常见情形，按提示填写关键信息，系统将生成维权安排并引导建案。
          </p>
          <div className="mt-4">
            <ChannelIntakeWizard
              initialChannelId={initial.channelId}
              initialScenarioId={initial.scenarioId}
              onBack={goChoose}
            />
          </div>
        </Surface>
      </div>
    );
  }

  if (path === 'general') {
    return (
      <div id="intake-desk" className="scroll-mt-24 space-y-3">
        <button
          type="button"
          onClick={goChoose}
          className="text-sm text-muted-foreground hover:text-foreground hover:underline"
        >
          ← 返回选择维权方式
        </button>
        <IntakeDesk embedded />
      </div>
    );
  }

  return (
    <div id="intake-desk" className="scroll-mt-24">
      <Surface padding="lg" className="border-accent/20 bg-gradient-to-br from-card to-accent/5">
        <Badge tone="accent">开始维权</Badge>
        <h2 className="mt-2 font-display text-lg font-semibold">请选择维权方式</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          专项通道按身份引导填写；普通入口适合自行描述案情。
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={goSpecial}
            className={cn(
              'rounded-[var(--radius-md)] border border-border/70 bg-card p-5 text-left shadow-card transition-all',
              'hover:border-accent/40 hover:shadow-card-hover',
            )}
          >
            <HeartHandshake className="h-5 w-5 text-accent" />
            <p className="mt-3 font-medium">专项通道</p>
            <p className="mt-1 text-sm text-muted-foreground">
              农民工、实习生/试用期、女职工等，按常见情形填写结构化信息。
            </p>
          </button>
          <button
            type="button"
            onClick={goGeneral}
            className={cn(
              'rounded-[var(--radius-md)] border border-border/70 bg-card p-5 text-left shadow-card transition-all',
              'hover:border-accent/40 hover:shadow-card-hover',
            )}
          >
            <MessageSquareText className="h-5 w-5 text-accent" />
            <p className="mt-3 font-medium">普通入口</p>
            <p className="mt-1 text-sm text-muted-foreground">
              自由描述情况并上传材料，由系统分析后给出维权安排。
            </p>
          </button>
        </div>
      </Surface>
    </div>
  );
}
