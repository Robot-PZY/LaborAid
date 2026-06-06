import { useMemo, useState } from 'react';
import { Calculator, Copy, Check, ArrowUpRight, Info } from 'lucide-react';
import { PageHeader, Surface, Button } from '@/components/ui/primitives';
import { useToast } from '@/lib/toast';

type TerminationType =
  | 'illegal' // 违法解除 → 2N
  | 'employer_no_fault' // 用人单位解除（经济补偿 N）
  | 'mutual' // 协商一致（通常 N）
  | 'employee_resign' // 劳动者主动离职（通常 0，除非被迫解除）
  | 'forced' // 被迫解除（通常 N）
  | 'other';

function clampNum(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}

function toNumber(v: string): number | null {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function toMarkdownBlock(title: string, body: string): string {
  return `## ${title}\n\n${body.trim()}\n`;
}

function formatMoney(n: number): string {
  const v = Math.round(n * 100) / 100;
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
}

function calcN(years: number, months: number): number {
  const totalMonths = clampNum(Math.floor(years) * 12 + Math.floor(months), 0, 1000);
  const fullYears = Math.floor(totalMonths / 12);
  const rem = totalMonths % 12;
  if (rem === 0) return fullYears;
  if (rem <= 6) return fullYears + 0.5;
  return fullYears + 1;
}

function labelForTermination(t: TerminationType): string {
  switch (t) {
    case 'illegal':
      return '违法解除（赔偿金 2N）';
    case 'employer_no_fault':
      return '用人单位解除（经济补偿 N）';
    case 'mutual':
      return '协商一致解除（通常 N）';
    case 'forced':
      return '被迫解除（通常 N）';
    case 'employee_resign':
      return '劳动者主动离职（通常 0）';
    default:
      return '其他/不确定';
  }
}

export default function CompensationCalculator() {
  const { toast } = useToast();
  const [monthlyWage, setMonthlyWage] = useState('');
  const [years, setYears] = useState('0');
  const [months, setMonths] = useState('0');
  const [terminationType, setTerminationType] = useState<TerminationType>('illegal');
  const [useLocalAvgCap, setUseLocalAvgCap] = useState(false);
  const [localAvgWage, setLocalAvgWage] = useState('');
  const [copied, setCopied] = useState(false);

  const result = useMemo(() => {
    const wage = toNumber(monthlyWage);
    const y = toNumber(years) ?? 0;
    const m = toNumber(months) ?? 0;

    const n = calcN(y, m);
    const notes: string[] = [];

    let effectiveWage = wage ?? 0;
    if (useLocalAvgCap) {
      const avg = toNumber(localAvgWage);
      if (avg && avg > 0 && wage && wage > 0) {
        const cap = 3 * avg;
        if (wage > cap) {
          notes.push(`你启用了"3 倍社平工资封顶"：月工资按 ${formatMoney(cap)} 元计（原输入 ${formatMoney(wage)} 元）。`);
          effectiveWage = cap;
        } else {
          notes.push(`你启用了"3 倍社平工资封顶"：你的月工资未超过封顶线。`);
        }
      } else {
        notes.push('已启用"3 倍社平工资封顶"，但未填写有效的"当地职工月平均工资"。');
      }
    }

    let formula = '';
    let min = 0;
    let max = 0;

    if (!wage || wage <= 0) {
      notes.push('请先填写"月工资（计算基数）"。');
    }

    switch (terminationType) {
      case 'illegal':
        formula = `赔偿金 = 2N × 月工资`;
        min = 2 * n * effectiveWage;
        max = min;
        break;
      case 'employer_no_fault':
        formula = `经济补偿 = N × 月工资`;
        min = n * effectiveWage;
        max = min;
        break;
      case 'mutual':
        formula = `通常：经济补偿 = N × 月工资（以协议为准）`;
        min = n * effectiveWage;
        max = min;
        break;
      case 'forced':
        formula = `通常：经济补偿 = N × 月工资（需证明被迫解除法定情形）`;
        min = n * effectiveWage;
        max = min;
        break;
      case 'employee_resign':
        formula = `通常：补偿为 0（如属于被迫解除，改选"被迫解除"）`;
        min = 0;
        max = 0;
        break;
      default:
        formula = `可能涉及 N 或 2N（取决于解除是否合法、是否构成违法解除等）`;
        min = n * effectiveWage;
        max = 2 * n * effectiveWage;
        notes.push('你选择了"不确定/其他"：这里给出 N～2N 的粗略区间，需结合事实与证据判断。');
        break;
    }

    if (n > 12) {
      notes.push('提示：经济补偿年限在部分规则下可能存在上限（常见口径为 12 年），请结合当地与具体情形核对。');
    }

    const md = (() => {
      const head = [
        `- **解除类型**：${labelForTermination(terminationType)}`,
        `- **月工资（计算基数）**：${wage ? `${formatMoney(wage)} 元` : '未填写'}`,
        `- **工龄输入**：${Math.max(0, Math.floor(y))} 年 ${Math.max(0, Math.floor(m))} 个月`,
        `- **折算 N**：${n}`,
        useLocalAvgCap ? `- **3 倍社平工资封顶**：启用` : `- **3 倍社平工资封顶**：未启用`,
        useLocalAvgCap && localAvgWage ? `- **当地月平均工资**：${formatMoney(toNumber(localAvgWage) || 0)} 元` : null,
      ].filter(Boolean).join('\n');

      const amountLine =
        min === max
          ? `- **计算结果**：约 ${formatMoney(min)} 元`
          : `- **计算区间**：约 ${formatMoney(min)}～${formatMoney(max)} 元`;

      const formulaBlock = `- **公式**：${formula}\n${amountLine}`;
      const noteBlock = notes.length ? notes.map((n) => `- ${n}`).join('\n') : '-（无）';

      return [
        toMarkdownBlock('赔偿/补偿计算（参考）', head),
        toMarkdownBlock('计算结果', formulaBlock),
        toMarkdownBlock('提示与注意', noteBlock),
      ].join('\n');
    })();

    return { n, min, max, formula, notes, markdown: md, wage, effectiveWage };
  }, [monthlyWage, years, months, terminationType, useLocalAvgCap, localAvgWage]);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(result.markdown);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
      toast({ type: 'success', title: '已复制', description: '可直接粘贴到"分析案情/报告"或笔记中。' });
    } catch {
      toast({ type: 'error', title: '复制失败', description: '请检查浏览器权限，或手动全选复制。' });
    }
  }

  // 计算各项金额
  const nAmount = result.n * result.effectiveWage;
  const twoNAmount = 2 * result.n * result.effectiveWage;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="其他功能 · 计算器"
        title="赔偿/补偿计算"
        description="按月工资、工龄与解除类型，粗算经济补偿/赔偿金区间并给出公式。"
      />

      <Surface padding="lg" className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-sm font-medium">解除类型</label>
            <select
              value={terminationType}
              onChange={(e) => setTerminationType(e.target.value as TerminationType)}
              className="input-field"
            >
              <option value="illegal">违法解除（赔偿金 2N）</option>
              <option value="employer_no_fault">用人单位解除（经济补偿 N）</option>
              <option value="mutual">协商一致解除（通常 N）</option>
              <option value="forced">被迫解除（通常 N）</option>
              <option value="employee_resign">劳动者主动离职（通常 0）</option>
              <option value="other">其他/不确定（给区间）</option>
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium">月工资（计算基数，元）</label>
            <div className="flex items-center gap-2">
              <Calculator className="h-4 w-4 text-muted-foreground" />
              <input
                inputMode="decimal"
                value={monthlyWage}
                onChange={(e) => setMonthlyWage(e.target.value)}
                placeholder="例如：8000"
                className="input-field"
              />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              这里按"月工资 × N/2N"简化计算；奖金、补贴、封顶口径等可在下方启用提示项。
            </p>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-1.5 block text-sm font-medium">工作年限（年）</label>
            <input
              inputMode="numeric"
              value={years}
              onChange={(e) => setYears(e.target.value)}
              className="input-field"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium">额外月份（月）</label>
            <input
              inputMode="numeric"
              value={months}
              onChange={(e) => setMonths(e.target.value)}
              className="input-field"
            />
            <p className="mt-1 text-xs text-muted-foreground">折算口径：≤6 个月按 0.5，&gt;6 个月按 1。</p>
          </div>
          <div className="flex items-center gap-3 rounded-[var(--radius-md)] border border-border/70 bg-muted/20 px-4 py-3">
            <input
              id="cap"
              type="checkbox"
              checked={useLocalAvgCap}
              onChange={(e) => setUseLocalAvgCap(e.target.checked)}
            />
            <label htmlFor="cap" className="text-sm">
              启用 3 倍社平工资封顶提示
            </label>
          </div>
        </div>

        {useLocalAvgCap && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium">当地职工上年度月平均工资（元，可选）</label>
              <input
                inputMode="decimal"
                value={localAvgWage}
                onChange={(e) => setLocalAvgWage(e.target.value)}
                placeholder="例如：10000"
                className="input-field"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                仅用于"封顶提示"的粗算；实际以当地公布口径、你的工资构成与证据为准。
              </p>
            </div>
          </div>
        )}
      </Surface>

      {/* 结果卡片 */}
      <Surface padding="lg" className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">计算结果</p>
            <p className="mt-0.5 text-xs text-muted-foreground">（仅作参考，最终以证据、裁判/仲裁口径为准）</p>
          </div>
          <Button variant="secondary" onClick={handleCopy}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? '已复制' : '复制结果'}
          </Button>
        </div>

        {/* 主要结果 */}
        <div className="rounded-lg border-2 border-emerald-200 bg-emerald-50 p-6">
          <div className="flex items-start gap-4">
            <div className="rounded-full bg-emerald-100 p-3">
              <Calculator className="h-6 w-6 text-emerald-600" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-emerald-700">计算结果</p>
              {result.min === result.max ? (
                <p className="mt-2 text-3xl font-bold text-emerald-600">
                  ¥{formatMoney(result.min)}
                </p>
              ) : (
                <p className="mt-2 text-3xl font-bold text-emerald-600">
                  ¥{formatMoney(result.min)} ~ ¥{formatMoney(result.max)}
                </p>
              )}
              <p className="mt-2 text-sm text-muted-foreground">
                {result.formula}
              </p>
            </div>
          </div>
        </div>

        {/* 计算明细表格 */}
        {result.wage && result.wage > 0 && (
          <div className="space-y-3">
            <p className="text-sm font-medium text-foreground">计算明细</p>
            <div className="overflow-hidden rounded-lg border border-border/70">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">项目</th>
                    <th className="px-4 py-2 text-right font-medium">金额</th>
                    <th className="px-4 py-2 text-left font-medium">计算说明</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/70">
                  <tr>
                    <td className="px-4 py-3 font-medium">经济补偿 (N)</td>
                    <td className="px-4 py-3 text-right font-semibold">¥{formatMoney(nAmount)}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {result.effectiveWage} × {result.n} = {formatMoney(nAmount)}
                    </td>
                  </tr>
                  {terminationType === 'illegal' && (
                    <tr className="bg-emerald-50/50">
                      <td className="px-4 py-3 font-medium text-emerald-700">赔偿金 (2N)</td>
                      <td className="px-4 py-3 text-right font-semibold text-emerald-600">¥{formatMoney(twoNAmount)}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {result.effectiveWage} × {result.n} × 2 = {formatMoney(twoNAmount)}
                      </td>
                    </tr>
                  )}
                  <tr>
                    <td className="px-4 py-3 font-medium">代通知金（1个月）</td>
                    <td className="px-4 py-3 text-right font-semibold">¥{formatMoney(result.effectiveWage)}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      未提前30日通知时适用
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 计算依据 */}
        <div className="space-y-3">
          <p className="text-sm font-medium text-foreground">计算依据</p>
          <div className="rounded-lg border border-border/70 bg-muted/20 p-4">
            <div className="grid gap-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">解除类型</span>
                <span className="font-medium">{labelForTermination(terminationType)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">月工资基数</span>
                <span className="font-medium">{result.wage ? `¥${formatMoney(result.wage)}` : '未填写'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">工龄</span>
                <span className="font-medium">{Math.max(0, Math.floor(toNumber(years) ?? 0))} 年 {Math.max(0, Math.floor(toNumber(months) ?? 0))} 个月</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">折算 N</span>
                <span className="font-medium">{result.n}</span>
              </div>
              {useLocalAvgCap && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">3倍社平工资封顶</span>
                  <span className="font-medium">已启用</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 提示信息 */}
        {result.notes.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-amber-500" />
              <p className="text-sm font-medium text-foreground">提示与注意</p>
            </div>
            <div className="space-y-2">
              {result.notes.map((note, i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="mt-0.5 text-foreground">•</span>
                  <span>{note}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <span>可复制后粘贴到「分析案情」的补充说明或报告正文里。</span>
          <a href="/research" className="inline-flex items-center gap-1 text-foreground underline-offset-4 hover:underline">
            去分析案情
            <ArrowUpRight className="h-3.5 w-3.5" />
          </a>
        </div>
      </Surface>
    </div>
  );
}
