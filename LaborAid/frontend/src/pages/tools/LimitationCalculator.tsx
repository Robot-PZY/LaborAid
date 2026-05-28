import { useMemo, useState } from 'react';
import { CalendarDays, Copy, Check, ArrowUpRight } from 'lucide-react';
import { PageHeader, Surface, Button } from '@/components/ui/primitives';
import { useToast } from '@/lib/toast';

type DisputeType =
  | 'wage_in_service'
  | 'wage_after_termination'
  | 'illegal_termination'
  | 'overtime'
  | 'no_written_contract'
  | 'other';

function parseDateInput(value: string): Date | null {
  if (!value) return null;
  const d = new Date(value + 'T00:00:00');
  return Number.isFinite(d.getTime()) ? d : null;
}

function addYears(date: Date, years: number): Date {
  const d = new Date(date);
  d.setFullYear(d.getFullYear() + years);
  return d;
}

function fmt(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function toMarkdownBlock(title: string, body: string): string {
  return `## ${title}\n\n${body.trim()}\n`;
}

export default function LimitationCalculator() {
  const { toast } = useToast();
  const [disputeType, setDisputeType] = useState<DisputeType>('illegal_termination');
  const [eventDate, setEventDate] = useState(''); // 解除/欠薪发生日/权利受侵害知晓日
  const [stillEmployed, setStillEmployed] = useState(true);
  const [terminationDate, setTerminationDate] = useState(''); // 在职欠薪：劳动关系终止日
  const [hasInterruption, setHasInterruption] = useState(false);
  const [interruptionDate, setInterruptionDate] = useState(''); // 中断起算日（提交仲裁/起诉/调解等）
  const [copied, setCopied] = useState(false);

  const calc = useMemo(() => {
    const event = parseDateInput(eventDate);
    const term = parseDateInput(terminationDate);
    const interrupt = parseDateInput(interruptionDate);
    const now = new Date();

    const tips: string[] = [];
    const deadlines: Array<{ label: string; date: Date }> = [];

    // 简化规则（先满足主线需求，后续可按地方法规/口径拓展）
    // 1) 一般：知道/应当知道权利被侵害之日起 1 年
    // 2) 劳动关系存续期间拖欠劳动报酬：不受 1 年限制；劳动关系终止后 1 年内提出
    // 3) 时效中断：按用户提供的“已采取法律行动日期”重新起算 1 年（简化）

    if (disputeType === 'wage_in_service') {
      tips.push('劳动关系存续期间因拖欠劳动报酬发生争议，通常不受一年仲裁时效限制。');
      if (stillEmployed) {
        tips.push('如仍在职：建议尽快固定证据并及时主张权利，避免举证困难。');
        tips.push('如后续离职：请关注“劳动关系终止后一年内申请仲裁”的期限。');
      } else {
        tips.push('如已离职：一般需在劳动关系终止之日起一年内申请仲裁。');
        if (term) {
          deadlines.push({ label: '建议最迟提交仲裁（终止后 1 年）', date: addYears(term, 1) });
        } else {
          tips.push('请补充“劳动关系终止日期”，以便计算最终截止日。');
        }
      }
    } else {
      if (!event) {
        tips.push('请先填写“关键事件日期”（解除/欠薪发生/知晓权利受侵害日期）。');
      } else {
        deadlines.push({ label: '建议最迟提交仲裁（一般 1 年）', date: addYears(event, 1) });
      }
    }

    if (hasInterruption) {
      if (interrupt) {
        tips.push('你选择了“时效中断/重新起算”：这里按中断日期起算 1 年给出提示（简化口径）。');
        deadlines.push({ label: '中断后建议最迟提交仲裁（重新起算 1 年）', date: addYears(interrupt, 1) });
      } else {
        tips.push('已勾选“时效中断/重新起算”，但未填写中断日期。');
      }
    }

    // 风险提示（对不同类型给一点更贴近的说明）
    if (disputeType === 'illegal_termination') {
      tips.push('违法解除/解除争议的“起算点”通常与解除通知/离职手续/明确知道解除事实有关。');
    }
    if (disputeType === 'no_written_contract') {
      tips.push('未签书面劳动合同的二倍工资等主张，可能涉及不同期间计算与举证，请结合当地口径核对。');
    }

    const sorted = deadlines
      .filter((d) => Number.isFinite(d.date.getTime()))
      .sort((a, b) => a.date.getTime() - b.date.getTime());

    const urgent = sorted.length > 0 && sorted[0]!.date.getTime() - now.getTime() < 14 * 24 * 3600 * 1000;

    const md = (() => {
      const head = [
        `- **争议类型**：${labelForDispute(disputeType)}`,
        event ? `- **关键事件日期**：${fmt(event)}` : `- **关键事件日期**：未填写`,
        disputeType === 'wage_in_service'
          ? `- **是否仍在职**：${stillEmployed ? '是' : '否'}`
          : null,
        !stillEmployed && term ? `- **劳动关系终止日期**：${fmt(term)}` : (!stillEmployed && disputeType === 'wage_in_service' ? `- **劳动关系终止日期**：未填写` : null),
        hasInterruption ? `- **是否存在中断/重新起算**：是` : `- **是否存在中断/重新起算**：否`,
        hasInterruption && interrupt ? `- **中断日期**：${fmt(interrupt)}` : null,
      ].filter(Boolean).join('\n');

      const dl = sorted.length
        ? sorted.map((d) => `- **${d.label}**：${fmt(d.date)}`).join('\n')
        : '- 暂无法计算截止日期（请补全必要时间信息）。';

      const note = tips.length ? tips.map((t) => `- ${t}`).join('\n') : '-（无）';

      return [
        toMarkdownBlock('仲裁时效/期限计算（参考）', head),
        toMarkdownBlock('关键截止日期清单', dl),
        toMarkdownBlock('提示与注意', note),
      ].join('\n');
    })();

    return { tips, deadlines: sorted, urgent, markdown: md };
  }, [disputeType, eventDate, stillEmployed, terminationDate, hasInterruption, interruptionDate]);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(calc.markdown);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
      toast({ type: 'success', title: '已复制', description: '可直接粘贴到“分析案情/报告”或笔记中。' });
    } catch {
      toast({ type: 'error', title: '复制失败', description: '请检查浏览器权限，或手动全选复制。' });
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="其他功能 · 计算器"
        title="时效/期限计算"
        description="根据事件时间、是否在职与中断情况，生成仲裁时效提示与关键截止日期清单（可复制）。"
      />

      <Surface padding="lg" className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-sm font-medium">争议类型</label>
            <select
              value={disputeType}
              onChange={(e) => setDisputeType(e.target.value as DisputeType)}
              className="input-field"
            >
              <option value="illegal_termination">违法解除/解除争议</option>
              <option value="wage_in_service">在职欠薪（劳动关系存续）</option>
              <option value="wage_after_termination">离职后欠薪/工资争议</option>
              <option value="overtime">加班费争议</option>
              <option value="no_written_contract">未签书面劳动合同/二倍工资</option>
              <option value="other">其他劳动争议</option>
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium">关键事件日期</label>
            <div className="flex items-center gap-2">
              <CalendarDays className="h-4 w-4 text-muted-foreground" />
              <input
                type="date"
                value={eventDate}
                onChange={(e) => setEventDate(e.target.value)}
                className="input-field"
              />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              例如：收到解除通知日、知道欠薪事实之日、权利受侵害的知晓日等。
            </p>
          </div>
        </div>

        {disputeType === 'wage_in_service' && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex items-center gap-3 rounded-[var(--radius-md)] border border-border/70 bg-muted/20 px-4 py-3">
              <input
                id="still-employed"
                type="checkbox"
                checked={stillEmployed}
                onChange={(e) => setStillEmployed(e.target.checked)}
              />
              <label htmlFor="still-employed" className="text-sm">
                目前仍在职（劳动关系尚未终止）
              </label>
            </div>
            {!stillEmployed && (
              <div>
                <label className="mb-1.5 block text-sm font-medium">劳动关系终止日期（离职/解除生效日）</label>
                <input
                  type="date"
                  value={terminationDate}
                  onChange={(e) => setTerminationDate(e.target.value)}
                  className="input-field"
                />
              </div>
            )}
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex items-center gap-3 rounded-[var(--radius-md)] border border-border/70 bg-muted/20 px-4 py-3">
            <input
              id="has-interruption"
              type="checkbox"
              checked={hasInterruption}
              onChange={(e) => setHasInterruption(e.target.checked)}
            />
            <label htmlFor="has-interruption" className="text-sm">
              存在时效中断/重新起算（如：已提交仲裁/起诉/调解）
            </label>
          </div>

          {hasInterruption && (
            <div>
              <label className="mb-1.5 block text-sm font-medium">中断日期（提交/受理/启动日期）</label>
              <input
                type="date"
                value={interruptionDate}
                onChange={(e) => setInterruptionDate(e.target.value)}
                className="input-field"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                这里按“中断日期起算 1 年”给出提示（简化口径；提交材料/受理时间以当地为准）。
              </p>
            </div>
          )}
        </div>
      </Surface>

      <Surface padding="lg" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">结果摘要</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {calc.urgent ? '⚠️ 距离最近截止日期可能较近，建议尽快处理。' : '（仅作参考，最终以当地仲裁委口径与具体事实为准）'}
            </p>
          </div>
          <Button variant="secondary" onClick={handleCopy}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? '已复制' : '复制结果'}
          </Button>
        </div>

        <div className="rounded-[var(--radius-md)] border border-border/70 bg-background p-4 text-sm">
          <pre className="whitespace-pre-wrap break-words text-xs leading-relaxed text-foreground">
            {calc.markdown}
          </pre>
        </div>

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

function labelForDispute(t: DisputeType): string {
  switch (t) {
    case 'wage_in_service':
      return '在职欠薪（劳动关系存续）';
    case 'wage_after_termination':
      return '离职后欠薪/工资争议';
    case 'illegal_termination':
      return '违法解除/解除争议';
    case 'overtime':
      return '加班费争议';
    case 'no_written_contract':
      return '未签书面劳动合同/二倍工资';
    default:
      return '其他劳动争议';
  }
}

