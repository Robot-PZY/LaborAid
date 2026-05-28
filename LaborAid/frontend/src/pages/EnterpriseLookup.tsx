import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Building2,
  ExternalLink,
  Loader2,
  Search,
  AlertCircle,
  ShieldAlert,
  CheckCircle2,
} from 'lucide-react';
import { enterpriseApi, type EnterpriseScanResult } from '@/lib/api/enterprise';
import {
  getEnterpriseScanCache,
  hasEnterpriseScanCache,
  saveEnterpriseScanCache,
} from '@/lib/enterprise-cache';
import { PageHeader, Surface, SectionTitle, Button, Badge } from '@/components/ui/primitives';
import ToolHistoryPanel from '@/components/history/ToolHistoryPanel';
import { addToolHistory } from '@/lib/tool-history';

function InfoRow({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:gap-3">
      <dt className="shrink-0 text-xs font-medium text-muted-foreground sm:w-24">{label}</dt>
      <dd className="text-sm leading-relaxed">{value}</dd>
    </div>
  );
}

function regStatusTone(status: string): 'success' | 'warning' | 'neutral' {
  if (status.includes('存续') || status.includes('在业') || status.includes('开业')) return 'success';
  if (status.includes('注销') || status.includes('吊销')) return 'warning';
  return 'neutral';
}

function workerVerdict(data: EnterpriseScanResult): { tone: 'success' | 'warning' | 'neutral'; text: string } {
  const { company, risk_summary } = data;
  const status = company.reg_status || '';

  if (status.includes('注销') || status.includes('吊销')) {
    return { tone: 'warning', text: '该企业登记状态异常，维权时请重点核实主体是否仍在经营、有无承接主体。' };
  }
  if (risk_summary.shixin_count > 0 || risk_summary.zhixing_count > 0) {
    return { tone: 'warning', text: '存在失信或被执行记录，可能存在偿付能力不足，建议尽早固定证据并考虑财产保全。' };
  }
  if (risk_summary.penalty_count > 0 || risk_summary.exception_count > 0) {
    return { tone: 'warning', text: '存在行政处罚或经营异常记录，可结合仲裁/监察材料一并说明对方经营与合规情况。' };
  }
  if (risk_summary.has_risk) {
    return { tone: 'neutral', text: '发现其他公开风险信息，建议结合下方明细与官方渠道进一步核实。' };
  }
  return { tone: 'success', text: '未发现明显公开风险记录，仍请以劳动合同、工资流水等直接证据为准。' };
}

const CORE_RISKS = [
  { key: 'penalty_count' as const, label: '行政处罚' },
  { key: 'exception_count' as const, label: '经营异常' },
  { key: 'shixin_count' as const, label: '失信被执行人' },
  { key: 'zhixing_count' as const, label: '被执行人' },
];

function RiskRecord({
  title,
  items,
  renderItem,
}: {
  title: string;
  items: Record<string, unknown>[];
  renderItem: (item: Record<string, unknown>) => string;
}) {
  if (items.length === 0) return null;
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">{title}</h3>
      <ul className="space-y-2">
        {items.slice(0, 3).map((item, i) => (
          <li
            key={i}
            className="rounded-[var(--radius-md)] border border-border/70 bg-muted/30 px-3 py-2 text-sm leading-relaxed text-muted-foreground"
          >
            {renderItem(item)}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ScanResult({ data }: { data: EnterpriseScanResult }) {
  const { company, risk_summary, risks } = data;
  const verdict = workerVerdict(data);
  const activeRisks = CORE_RISKS.filter(({ key }) => risk_summary[key] > 0);
  const hasRiskDetails =
    risks.penalties.length > 0 ||
    risks.exceptions.length > 0 ||
    risks.shixin_items.length > 0 ||
    risks.zhixing_items.length > 0;

  return (
    <div className="space-y-6">
      <Surface className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-semibold">{company.name}</h2>
            {company.reg_status && (
              <Badge tone={regStatusTone(company.reg_status)} className="mt-2">
                {company.reg_status}
              </Badge>
            )}
          </div>
          {risk_summary.has_risk ? (
            <Badge tone="warning" className="gap-1">
              <ShieldAlert className="h-3.5 w-3.5" />
              有公开风险
            </Badge>
          ) : (
            <Badge tone="success" className="gap-1">
              <CheckCircle2 className="h-3.5 w-3.5" />
              暂无明显风险
            </Badge>
          )}
        </div>

        <div
          className={`rounded-[var(--radius-md)] border px-3 py-2.5 text-sm leading-relaxed ${
            verdict.tone === 'warning'
              ? 'border-amber-200/80 bg-amber-50/70 text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-100'
              : verdict.tone === 'success'
                ? 'border-emerald-200/80 bg-emerald-50/70 text-emerald-900 dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-100'
                : 'border-border/70 bg-muted/40 text-muted-foreground'
          }`}
        >
          {verdict.text}
        </div>

        <div>
          <SectionTitle title="工商登记" />
          <dl className="mt-3 space-y-2.5">
            <InfoRow label="信用代码" value={company.credit_code} />
            <InfoRow label="法定代表人" value={company.legal_person} />
            <InfoRow label="成立日期" value={company.establish_time} />
            <InfoRow label="注册地址" value={company.address} />
            <InfoRow label="参保人数" value={company.insured_count} />
          </dl>
        </div>

        {company.profile_url && (
          <a
            href={company.profile_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline"
          >
            在企查查查看完整信息
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </Surface>

      <section>
        <SectionTitle title="风险关注" />
        {activeRisks.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">未发现行政处罚、经营异常、失信或被执行记录。</p>
        ) : (
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {activeRisks.map(({ key, label }) => (
              <div
                key={key}
                className="rounded-[var(--radius-md)] border border-amber-300/80 bg-amber-50/80 px-3 py-2 text-center dark:border-amber-900/50 dark:bg-amber-950/30"
              >
                <p className="text-lg font-semibold text-amber-700 dark:text-amber-400">{risk_summary[key]}</p>
                <p className="text-xs text-muted-foreground">{label}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {hasRiskDetails && (
        <section className="space-y-4">
          <SectionTitle title="近期记录" />
          <RiskRecord
            title="行政处罚"
            items={risks.penalties}
            renderItem={(item) =>
              [item.PenaltyDate, item.OfficeName, item.Content || item.PenaltyType].filter(Boolean).join(' · ')
            }
          />
          <RiskRecord
            title="经营异常"
            items={risks.exceptions}
            renderItem={(item) =>
              [item.AddDate, item.AddReason].filter(Boolean).join(' · ')
            }
          />
          <RiskRecord
            title="失信被执行人"
            items={risks.shixin_items}
            renderItem={(item) =>
              [item.Publicdate, item.Executegov, item.Executestatus].filter(Boolean).join(' · ')
            }
          />
          <RiskRecord
            title="被执行人"
            items={risks.zhixing_items}
            renderItem={(item) =>
              [item.Liandate, item.ExecuteGov, item.Biaodi].filter(Boolean).join(' · ')
            }
          />
        </section>
      )}
    </div>
  );
}

export default function EnterpriseLookup() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialKeyword = searchParams.get('keyword') || searchParams.get('searchKey') || '';
  const [keyword, setKeyword] = useState(initialKeyword);
  const [loading, setLoading] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);
  const [configured, setConfigured] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [result, setResult] = useState<EnterpriseScanResult | null>(null);
  const [externalUrl, setExternalUrl] = useState<string | null>(null);
  const [disclaimer, setDisclaimer] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    enterpriseApi
      .status()
      .then((s) => {
        setConfigured(s.configured);
        setStatusMessage(s.message);
      })
      .catch((err: unknown) => {
        const offline =
          !(err as { response?: unknown })?.response &&
          (err as { code?: string }).code !== 'ERR_CANCELED';
        setStatusMessage(
          offline
            ? '无法连接后端服务，请确认后端已在 8000 端口启动后刷新页面'
            : '无法获取企业查询服务状态',
        );
      })
      .finally(() => setStatusLoading(false));
  }, []);

  const [viewingCached, setViewingCached] = useState(false);

  const applyResult = useCallback((data: EnterpriseScanResult, fromCache: boolean) => {
    setResult(data);
    setExternalUrl(data.external_search_url);
    setDisclaimer(data.disclaimer);
    setViewingCached(fromCache);
  }, []);

  const loadFromCache = useCallback(
    (kw: string): boolean => {
      const cached = getEnterpriseScanCache(kw);
      if (!cached) return false;
      applyResult(cached, true);
      setError('');
      setSearchParams({ keyword: kw.trim() });
      return true;
    },
    [applyResult, setSearchParams],
  );

  const runScan = useCallback(
    async (kw: string, options?: { forceApi?: boolean }) => {
      const trimmed = kw.trim();
      if (trimmed.length < 2) {
        setError('请输入至少 2 个字符的企业名称或统一社会信用代码');
        return;
      }

      if (!options?.forceApi && loadFromCache(trimmed)) {
        return;
      }

      setError('');
      setLoading(true);
      setResult(null);
      setViewingCached(false);
      setSearchParams(trimmed ? { keyword: trimmed } : {});

      try {
        const data = await enterpriseApi.scan(trimmed);
        saveEnterpriseScanCache(data);
        applyResult(data, false);
        addToolHistory({
          kind: 'enterprise',
          title: data.company.name,
          subtitle: data.risk_summary.has_risk ? '有公开风险' : '暂无明显风险',
          route: '/enterprise',
          query: data.search_key,
        });
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          '查询失败，请稍后重试';
        setError(typeof msg === 'string' ? msg : '查询失败，请稍后重试');
        setExternalUrl(`https://www.qcc.com/web/search?key=${encodeURIComponent(trimmed)}`);
      } finally {
        setLoading(false);
      }
    },
    [applyResult, loadFromCache, setSearchParams],
  );

  useEffect(() => {
    if (initialKeyword && initialKeyword.length >= 2 && configured) {
      if (!loadFromCache(initialKeyword)) {
        runScan(initialKeyword);
      }
    }
  }, [configured]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = keyword.trim();
    if (trimmed.length < 2) {
      setError('请输入至少 2 个字符的企业名称或统一社会信用代码');
      return;
    }
    if (!configured) {
      window.open(
        `https://www.qcc.com/web/search?key=${encodeURIComponent(trimmed)}`,
        '_blank',
        'noopener,noreferrer',
      );
      return;
    }
    runScan(keyword, { forceApi: true });
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="检索分析"
        title="查询企业"
        description="输入用人单位全称或统一社会信用代码，核实工商登记与公开风险情况。"
      />

      {(statusLoading || (!configured && statusMessage)) && (
        <Surface className="flex items-start gap-3 border-amber-200/80 bg-amber-50/80 dark:border-amber-900/50 dark:bg-amber-950/30">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          <div className="space-y-1">
            <p className="text-sm font-medium">
              {statusLoading ? '正在检查企查查服务…' : '企查查 API 尚未配置'}
            </p>
            <p className="text-sm text-muted-foreground">{statusMessage}</p>
          </div>
        </Surface>
      )}

      {configured && statusMessage && (
        <p className="text-xs text-muted-foreground">{statusMessage}</p>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Building2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="search"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="企业全称或统一社会信用代码"
            className="w-full rounded-[var(--radius-md)] border border-border/70 bg-card py-2.5 pl-10 pr-4 text-sm shadow-card outline-none focus:border-accent focus:ring-1 focus:ring-accent/30"
            maxLength={100}
          />
        </div>
        <Button type="submit" disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          {configured ? '查询' : '前往企查查搜索'}
        </Button>
      </form>

      <p className="text-[11px] text-muted-foreground">点击最近查询可查看已保存结果，不重复消耗查询次数</p>

      <ToolHistoryPanel
        kind="enterprise"
        limit={6}
        title="最近查询"
        compact
        onSelect={(entry) => {
          if (!entry.query) return;
          setKeyword(entry.query);
          if (hasEnterpriseScanCache(entry.query)) {
            loadFromCache(entry.query);
            return;
          }
          runScan(entry.query);
        }}
      />

      {viewingCached && result && (
        <p className="text-xs text-muted-foreground">
          正在查看本地保存的查询结果，未消耗新的查询次数。如需最新数据，请再次点击「查询」。
        </p>
      )}

      {error && (
        <Surface className="border-destructive/30 bg-destructive/5 text-sm text-destructive">
          {error}
          {externalUrl && (
            <a
              href={externalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1 font-medium underline"
            >
              前往企查查搜索
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        </Surface>
      )}

      {result && <ScanResult data={result} />}

      {disclaimer && (
        <p className="text-xs leading-relaxed text-muted-foreground">{disclaimer}</p>
      )}
    </div>
  );
}
