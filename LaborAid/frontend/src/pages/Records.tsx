import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Briefcase,
  FileText,
  Upload,
  BookOpen,
  ShieldCheck,
  Archive,
  ArrowUpRight,
  AlertCircle,
  Loader2,
  Trash2,
} from 'lucide-react';
import { AxiosError } from 'axios';
import { caseApi, documentApi, researchApi, evidenceApi, contractApi } from '@/lib/api';
import { userPortalApi, type UserRecentItem, type RecentKind } from '@/lib/api/user-portal';
import { useToast } from '@/lib/toast';
import { removeToolHistoryForDocument } from '@/lib/tool-history';
import { formatBytes } from '@/lib/format';
import { PageHeader, Surface, SectionTitle, Button } from '@/components/ui/primitives';
import ServiceStrip from '@/components/service/ServiceStrip';
import ToolHistoryPanel, { toolHistoryNavigatePath } from '@/components/history/ToolHistoryPanel';

const KIND_META: Record<
  RecentKind,
  { label: string; route: string; icon: React.ComponentType<{ className?: string }> }
> = {
  case: { label: '案件', route: '/cases', icon: Briefcase },
  document: { label: '文书', route: '/documents', icon: FileText },
  evidence: { label: '证据', route: '/evidence', icon: Upload },
  research: { label: '案情分析', route: '/research', icon: BookOpen },
  contract: { label: '合同', route: '/contracts', icon: ShieldCheck },
};

const DELETE_CONFIRM: Record<RecentKind, (title: string) => string> = {
  case: (t) =>
    `确定删除案件「${t}」？\n\n关联证据将一并删除；已生成的文书、案情分析报告仅解除关联，不会自动删除。`,
  document: (t) => `确定删除文书「${t}」？将同时删除后台记录与导出文件。`,
  evidence: (t) => `确定删除证据「${t}」？上传文件将一并删除。`,
  research: (t) => `确定删除案情分析报告「${t}」？`,
  contract: (t) => `确定删除合同「${t}」？`,
};

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function recentItemPath(item: UserRecentItem): string {
  switch (item.kind) {
    case 'case':
      return `/cases?open=${item.id}`;
    case 'document':
      return `/documents?docId=${item.id}&worker=1`;
    case 'research':
      return `/research?reportId=${item.id}`;
    case 'evidence':
      return `/evidence`;
    case 'contract':
      return `/contracts`;
  }
}

export default function Records() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [deletingKey, setDeletingKey] = useState<string | null>(null);
  const [overview, setOverview] = useState({
    cases: 0,
    documents: 0,
    evidence: 0,
    research: 0,
    contracts: 0,
    vault_files: 0,
    vault_bytes: 0,
    recent: [] as UserRecentItem[],
  });
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [error, setError] = useState('');

  const loadOverview = useCallback(() => {
    setOverviewLoading(true);
    userPortalApi
      .getOverview()
      .then(setOverview)
      .catch((err: unknown) => {
        const offline =
          !(err as { response?: unknown })?.response &&
          (err as { code?: string }).code !== 'ERR_CANCELED';
        setError(
          offline
            ? '无法连接后端服务，请确认后端已在 8000 端口启动。下方「工具使用记录」仍可在本地查看。'
            : '加载记录失败，请稍后重试',
        );
      })
      .finally(() => setOverviewLoading(false));
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const handleDeleteRecent = async (item: UserRecentItem) => {
    const msg = DELETE_CONFIRM[item.kind](item.title);
    if (!window.confirm(msg)) return;

    const key = `${item.kind}-${item.id}`;
    setDeletingKey(key);
    try {
      switch (item.kind) {
        case 'case':
          await caseApi.delete(item.id);
          break;
        case 'document':
          await documentApi.delete(item.id);
          removeToolHistoryForDocument(item.id);
          break;
        case 'evidence':
          await evidenceApi.delete(item.id);
          break;
        case 'research':
          await researchApi.delete(item.id);
          break;
        case 'contract':
          await contractApi.delete(item.id);
          break;
      }
      loadOverview();
      toast({ type: 'success', title: '已删除' });
    } catch (e: unknown) {
      const detail =
        e instanceof AxiosError
          ? (e.response?.data as { detail?: string })?.detail || '删除失败'
          : '删除失败';
      toast({ type: 'error', title: '删除失败', description: String(detail) });
      loadOverview();
    } finally {
      setDeletingKey(null);
    }
  };

  const stats = [
    { key: 'cases' as const, label: '案件', route: '/cases', icon: Briefcase },
    { key: 'documents' as const, label: '文书', route: '/documents', icon: FileText },
    { key: 'evidence' as const, label: '证据', route: '/evidence', icon: Upload },
    { key: 'research' as const, label: '案情分析', route: '/research', icon: BookOpen },
    { key: 'contracts' as const, label: '合同', route: '/contracts', icon: ShieldCheck },
  ];

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="个人数据"
        title="我的记录"
        description="汇总您在平台上的维权相关数据；可删除不需要的记录"
        action={
          <Button variant="outline" onClick={() => navigate('/vault')}>
            <Archive className="h-4 w-4" />
            材料库
          </Button>
        }
      />

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {overviewLoading ? (
        <div className="flex items-center gap-2 rounded-[var(--radius-md)] border border-border/70 bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          正在加载统计数据…
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {stats.map(({ key, label, route, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => navigate(route)}
            className="rounded-[var(--radius-md)] border border-border/70 bg-card p-4 text-left shadow-card transition-shadow hover:shadow-card-hover"
          >
            <Icon className="mb-2 h-4 w-4 text-muted-foreground" strokeWidth={1.75} />
            <p className="font-display text-2xl font-semibold tabular-nums">
              {overviewLoading ? '—' : overview[key]}
            </p>
            <p className="text-[11px] text-muted-foreground">{label}</p>
          </button>
        ))}
        <button
          type="button"
          onClick={() => navigate('/vault')}
          className="rounded-[var(--radius-md)] border border-accent/30 bg-accent/5 p-4 text-left shadow-card transition-shadow hover:shadow-card-hover"
        >
          <Archive className="mb-2 h-4 w-4 text-accent" strokeWidth={1.75} />
          <p className="font-display text-2xl font-semibold tabular-nums">
            {overviewLoading ? '—' : overview.vault_files}
          </p>
          <p className="text-[11px] text-muted-foreground">
            {overviewLoading ? '材料库' : formatBytes(overview.vault_bytes)}
          </p>
        </button>
      </div>

      <section>
        <SectionTitle title="最近更新" />
        <Surface padding="none">
          {overviewLoading ? (
            <p className="px-5 py-12 text-center text-sm text-muted-foreground">加载中…</p>
          ) : overview.recent.length === 0 ? (
            <p className="px-5 py-12 text-center text-sm text-muted-foreground">
              暂无记录，可从服务首页开始维权准备
            </p>
          ) : (
            <ul className="divide-y divide-border/60">
              {overview.recent.map((item) => {
                const meta = KIND_META[item.kind];
                const Icon = meta.icon;
                return (
                  <li key={`${item.kind}-${item.id}`} className="flex items-center">
                    <button
                      type="button"
                      onClick={() => navigate(recentItemPath(item))}
                      className="flex min-w-0 flex-1 items-center gap-4 px-5 py-3.5 text-left transition-colors hover:bg-muted/30"
                    >
                      <div className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] border border-border bg-muted/30">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{item.title}</p>
                        <p className="text-xs text-muted-foreground">{meta.label}</p>
                      </div>
                      <span className="shrink-0 text-[11px] tabular-nums text-muted-foreground">
                        {formatTime(item.updated_at)}
                      </span>
                      <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                    </button>
                    <button
                      type="button"
                      aria-label="删除记录"
                      disabled={deletingKey === `${item.kind}-${item.id}`}
                      onClick={() => handleDeleteRecent(item)}
                      className="mr-3 shrink-0 rounded p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                    >
                      {deletingKey === `${item.kind}-${item.id}` ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </Surface>
      </section>

      <section>
        <SectionTitle title="工具使用记录" />
        <p className="mb-3 text-sm text-muted-foreground">
          企业查询、法规检索、维权咨询、案情分析、审查合同、生成文书、整理证据等本地保存，仅在本设备当前账号可见
        </p>
        <ToolHistoryPanel
          limit={12}
          onSelect={(entry) => navigate(toolHistoryNavigatePath(entry))}
        />
      </section>

      <ServiceStrip />
    </div>
  );
}
