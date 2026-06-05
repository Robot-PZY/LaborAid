import { docTypeLabel, normalizeDocType } from '@/config/doc-types';
import type { IntakeSession } from '@/lib/intake-session';

export type DocRecommendation = {
  doc_type: string;
  label: string;
  reason: string;
  priority: number;
  generated: boolean;
  document_id?: number | null;
};

export type DocRecommendationsResult = {
  cause_type: string;
  cause_label: string;
  summary: string;
  recommendations: DocRecommendation[];
};

const CAUSE_BUNDLES: Record<string, string[]> = {
  wage_arrears: ['application', 'evidence_list'],
  illegal_termination: ['application', 'forced_termination_notice', 'evidence_list'],
  overtime_pay: ['application', 'evidence_list'],
  no_written_contract: ['application', 'evidence_list'],
};

const REASONS: Record<string, string> = {
  application: '核心维权文书，向劳动人事争议仲裁委员会申请仲裁',
  evidence_list: '整理已上传证据，列明证明目的',
  labor_supervision: '向人社监察部门书面投诉欠薪',
  wage_demand_letter: '书面催告用人单位限期支付工资',
  forced_termination_notice: '用人单位存在法定过错时，劳动者书面解除合同',
};

function matchCause(text: string): string {
  const rules: [string, string[]][] = [
    ['wage_arrears', ['拖欠', '欠薪', '不发工资', '讨薪', '包工头', '工地']],
    ['illegal_termination', ['辞退', '开除', '解除', '裁员', '被迫']],
    ['overtime_pay', ['加班', '加班费']],
    ['no_written_contract', ['没签合同', '未签合同', '二倍工资']],
  ];
  let best = 'wage_arrears';
  let score = 0;
  for (const [cause, kws] of rules) {
    const s = kws.filter((k) => text.includes(k)).length;
    if (s > score) {
      score = s;
      best = cause;
    }
  }
  return best;
}

/** 无关联案件时，根据案情文本本地推断推荐（与后端规则近似） */
export function buildLocalDocRecommendations(
  caseFacts: string,
  session?: IntakeSession | null,
): DocRecommendationsResult {
  const text = caseFacts.trim();
  const cause = session?.causeType || matchCause(text);
  const bundle = [...(CAUSE_BUNDLES[cause] || ['application', 'evidence_list'])];
  if (text.includes('监察') || text.includes('投诉')) bundle.push('labor_supervision');
  if (text.includes('包工头') || text.includes('工地')) bundle.push('wage_demand_letter');
  const deduped = Array.from(new Set(bundle.map((t) => normalizeDocType(t) || t)));

  const causeLabels: Record<string, string> = {
    wage_arrears: '拖欠工资',
    illegal_termination: '违法解除',
    overtime_pay: '加班费',
    no_written_contract: '未签合同',
  };

  return {
    cause_type: cause,
    cause_label: session?.causeLabel || causeLabels[cause] || '劳动争议',
    summary: text
      ? `根据案情描述推断为「${session?.causeLabel || causeLabels[cause] || '劳动争议'}」纠纷，建议按顺序准备以下文书。`
      : '请先填写案情描述，系统将推荐应生成的文书。',
    recommendations: deduped.map((doc_type, idx) => ({
      doc_type,
      label: docTypeLabel(doc_type),
      reason: REASONS[doc_type] || '适用于当前维权阶段',
      priority: idx + 1,
      generated: false,
    })),
  };
}
