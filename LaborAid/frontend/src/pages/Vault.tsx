import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Upload,
  Download,
  Trash2,
  Loader2,
  FileText,
  HardDrive,
  AlertCircle,
} from 'lucide-react';
import { caseApi, type Case } from '@/lib/api';
import { vaultApi, type UserMaterial, type VaultStats } from '@/lib/api/vault';
import { getActiveCaseId } from '@/lib/active-case';
import vaultMeta from '@/config/labor/material-vault.json';
import { useToast } from '@/lib/toast';
import { formatBytes } from '@/lib/format';
import { PageHeader, Surface, SectionTitle, Button, Badge } from '@/components/ui/primitives';
import ServiceStrip from '@/components/service/ServiceStrip';
import PageSkeleton from '@/components/ui/PageSkeleton';
import { downloadBlob } from '@/lib/api/client';
import { cn } from '@/lib/utils';

const STAGE_MAP = Object.fromEntries(vaultMeta.stages.map((s) => [s.id, s.label]));
const SOURCE_MAP = Object.fromEntries(vaultMeta.sources.map((s) => [s.id, s.label]));

function formatDate(s: string): string {
  return new Date(s).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function Vault() {
  const { toast } = useToast();
  const [searchParams] = useSearchParams();
  const fileRef = useRef<HTMLInputElement>(null);
  const [cases, setCases] = useState<Case[]>([]);
  const [caseFilter, setCaseFilter] = useState<number | ''>('');
  const [items, setItems] = useState<UserMaterial[]>([]);
  const [stats, setStats] = useState<VaultStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [stageFilter, setStageFilter] = useState('');
  const [query, setQuery] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(query.trim()), 300);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    caseApi.list().then(setCases).catch(() => {});
  }, []);

  useEffect(() => {
    const fromUrl = searchParams.get('caseId') || searchParams.get('open');
    if (fromUrl) {
      const id = Number(fromUrl);
      if (Number.isFinite(id) && id > 0) setCaseFilter(id);
      return;
    }
    const active = getActiveCaseId();
    if (active) setCaseFilter(active);
  }, [searchParams]);

  const caseTitleMap = useMemo(
    () => Object.fromEntries(cases.map((c) => [c.id, c.title])),
    [cases],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, st] = await Promise.all([
        vaultApi.list({
          stage: stageFilter || undefined,
          case_id: caseFilter === '' ? undefined : caseFilter,
          q: debouncedQ || undefined,
          limit: 100,
        }),
        vaultApi.getStats(),
      ]);
      setItems(list);
      setStats(st);
    } catch {
      toast('加载材料库失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [stageFilter, caseFilter, debouncedQ, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const uploadFiles = async (files: FileList | File[]) => {
    const list = Array.from(files);
    if (!list.length) return;
    setUploading(true);
    try {
      for (const file of list) {
        await vaultApi.upload(file, {
          stage: stageFilter || 'preparation',
          case_id: caseFilter === '' ? undefined : caseFilter,
        });
      }
      toast(`已上传 ${list.length} 个文件`, 'success');
      load();
    } catch {
      toast('上传失败，请检查容量或文件类型', 'error');
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleDownload = async (item: UserMaterial) => {
    try {
      const blob = await vaultApi.download(item.id);
      await downloadBlob(() => Promise.resolve(blob), item.original_filename);
    } catch {
      toast('下载失败', 'error');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除该材料？删除后不可恢复。')) return;
    try {
      await vaultApi.remove(id);
      toast('已删除', 'success');
      load();
    } catch {
      toast('删除失败', 'error');
    }
  };

  const handleStageChange = async (item: UserMaterial, stage: string) => {
    try {
      await vaultApi.update(item.id, { stage });
      setItems((prev) => prev.map((x) => (x.id === item.id ? { ...x, stage } : x)));
    } catch {
      toast('更新阶段失败', 'error');
    }
  };

  const usagePercent =
    stats && stats.quota_bytes > 0
      ? Math.min(100, Math.round((stats.total_bytes / stats.quota_bytes) * 100))
      : 0;

  if (loading && !items.length) {
    return <PageSkeleton rows={5} />;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="长期保存"
        title={vaultMeta.title}
        description={vaultMeta.description}
        action={
          <Button variant="secondary" disabled={uploading} onClick={() => fileRef.current?.click()}>
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            上传材料
          </Button>
        }
      />

      <input
        ref={fileRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => uploadFiles(e.target.files || [])}
      />

      <div
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && fileRef.current?.click()}
        onClick={() => !uploading && fileRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (!uploading) uploadFiles(e.dataTransfer.files);
        }}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center rounded-[var(--radius-lg)] border-2 border-dashed px-6 py-10 text-center transition-colors',
          dragOver ? 'border-accent bg-accent/5' : 'border-border hover:border-foreground/25 hover:bg-muted/30',
          uploading && 'pointer-events-none opacity-60',
        )}
      >
        <Upload className="mb-3 h-8 w-8 text-muted-foreground" strokeWidth={1.5} />
        <p className="text-sm font-medium">拖拽文件到此处，或点击选择</p>
        <p className="mt-1 text-xs text-muted-foreground">
          单文件最大 {vaultMeta.quota_hint.max_file_mb} MB · 在「整理证据」中上传的材料会同步保存在这里
        </p>
      </div>

      {stats && (
        <Surface padding="md" className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <HardDrive className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">
                已用 {formatBytes(stats.total_bytes)} / {formatBytes(stats.quota_bytes)}
              </p>
              <p className="text-xs text-muted-foreground">{stats.total_files} 个文件</p>
            </div>
          </div>
          <div className="h-2 w-full max-w-xs overflow-hidden rounded-full bg-muted sm:w-48">
            <div
              className={cn(
                'h-full rounded-full transition-all',
                usagePercent > 90 ? 'bg-destructive' : 'bg-accent',
              )}
              style={{ width: `${usagePercent}%` }}
            />
          </div>
        </Surface>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:flex-wrap">
        <select
          value={caseFilter === '' ? '' : String(caseFilter)}
          onChange={(e) => setCaseFilter(e.target.value ? Number(e.target.value) : '')}
          className="input-field max-w-[220px]"
          aria-label="筛选案件"
        >
          <option value="">全部案件</option>
          {cases.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title}
            </option>
          ))}
        </select>
        <select
          value={stageFilter}
          onChange={(e) => setStageFilter(e.target.value)}
          className="input-field max-w-[180px]"
          aria-label="筛选维权阶段"
        >
          <option value="">全部阶段</option>
          {vaultMeta.stages.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜索文件名…"
          className="input-field flex-1 max-w-md"
        />
      </div>

      <section>
        <SectionTitle title={`材料列表${items.length ? `（${items.length}）` : ''}`} />
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : items.length === 0 ? (
          <Surface className="py-16 text-center text-sm text-muted-foreground">
            <FileText className="mx-auto mb-3 h-10 w-10 opacity-40" />
            暂无材料，请上传或前往「整理证据」添加材料
          </Surface>
        ) : (
          <Surface padding="none" className="divide-y divide-border/60">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex min-w-0 gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[var(--radius-md)] border border-border bg-muted/40">
                    <FileText className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{item.title}</p>
                    <p className="truncate text-xs text-muted-foreground">{item.original_filename}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <select
                        value={item.stage}
                        onChange={(e) => handleStageChange(item, e.target.value)}
                        className="rounded border border-border bg-background px-2 py-0.5 text-[11px]"
                        aria-label="维权阶段"
                      >
                        {vaultMeta.stages.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                      <Badge tone="neutral">{SOURCE_MAP[item.source] || item.source}</Badge>
                      {item.case_id != null && (
                        <Badge tone="neutral">
                          {caseTitleMap[item.case_id] ? `案件：${caseTitleMap[item.case_id]}` : `案件 #${item.case_id}`}
                        </Badge>
                      )}
                      <span className="text-[11px] text-muted-foreground">
                        {formatBytes(item.size_bytes)} · {formatDate(item.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button variant="outline" size="sm" onClick={() => handleDownload(item)}>
                    <Download className="h-3.5 w-3.5" />
                    下载
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(item.id)}>
                    <Trash2 className="h-3.5 w-3.5 text-destructive" />
                  </Button>
                </div>
              </div>
            ))}
          </Surface>
        )}
      </section>

      <div className="flex items-start gap-2 text-xs text-muted-foreground">
        <AlertCircle className="h-4 w-4 shrink-0" />
        材料仅您本人可见，账号注销后将按平台政策删除。
      </div>

      <ServiceStrip />
    </div>
  );
}
