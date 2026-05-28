/** Canonical doc type slugs — must match backend `DOC_TYPE_NAMES` / template `type`. */

export type DocTypeOption = { value: string; label: string; desc?: string };

/** Legacy URL / draft values → canonical slug */
export const DOC_TYPE_ALIASES: Record<string, string> = {
  defense: 'answer',
  representation: 'agency_opinion',
  opinion: 'legal_opinion',
  criminal_complaint: 'complaint',
};

export function normalizeDocType(type: string | null | undefined): string {
  if (!type) return '';
  const t = type.trim();
  return DOC_TYPE_ALIASES[t] ?? t;
}

export const WORKER_DOC_TYPE_VALUES = [
  'application',
  'labor_supervision',
  'wage_demand_letter',
  'forced_termination_notice',
  'arbitration_authorization',
  'evidence_list',
  'labor_contract',
  'mediation',
  'settlement_agreement',
] as const;

export const DOC_TYPES: DocTypeOption[] = [
  { value: 'application', label: '劳动仲裁申请书', desc: '向劳动人事争议仲裁委员会申请仲裁（欠薪、违法解除等）' },
  { value: 'labor_supervision', label: '劳动监察投诉书', desc: '向人社监察部门投诉用人单位违法用工' },
  { value: 'wage_demand_letter', label: '工资催告函', desc: '书面催告用人单位限期支付拖欠工资' },
  {
    value: 'forced_termination_notice',
    label: '被迫解除劳动合同通知书',
    desc: '用人单位存在法定过错时，劳动者书面解除合同',
  },
  { value: 'arbitration_authorization', label: '劳动仲裁代理委托书', desc: '委托律师或公民代理参加劳动仲裁' },
  { value: 'evidence_list', label: '证据清单', desc: '列明仲裁或诉讼提交的证据材料及证明目的' },
  {
    value: 'labor_contract',
    label: '劳动合同',
    desc: '参考人社部示范文本，含法定必备条款',
  },
  { value: 'mediation', label: '劳动争议调解协议书', desc: '经调解组织主持达成协议' },
  { value: 'settlement_agreement', label: '劳动争议和解协议', desc: '双方自行和解一次性了结争议' },
  { value: 'complaint', label: '民事起诉状', desc: '劳动纠纷经仲裁后可向法院起诉（要素式）' },
  { value: 'answer', label: '答辩状', desc: '对原告起诉状的答辩和反驳意见' },
  { value: 'appeal', label: '上诉状', desc: '对一审判决不服，向上级法院提起上诉' },
  { value: 'agency_opinion', label: '代理词', desc: '诉讼代理人在庭审中发表的代理意见' },
  { value: 'legal_opinion', label: '法律意见书', desc: '就特定法律问题出具的专业意见' },
  { value: 'lawyer_letter', label: '律师函', desc: '律师就纠纷发出的正式函件' },
  { value: 'contract', label: '通用民事合同', desc: '买卖、服务、租赁等民事合同' },
  { value: 'preservation_application', label: '财产保全申请书', desc: '诉前或诉中申请查封、冻结财产' },
  { value: 'other', label: '其他文书', desc: '其他类型的法律文书' },
];

export const WORKER_DOC_TYPES = DOC_TYPES.filter((d) =>
  (WORKER_DOC_TYPE_VALUES as readonly string[]).includes(d.value),
);

export const BUNDLE_PRESETS = [
  {
    key: 'labor_worker_basic',
    label: '劳动者维权基础套装',
    desc: '劳动仲裁申请书 + 证据清单',
    types: ['application', 'evidence_list'],
    workerOnly: true,
  },
  {
    key: 'labor_supervision_pack',
    label: '欠薪监察套装',
    desc: '劳动监察投诉书 + 工资催告函 + 证据清单',
    types: ['labor_supervision', 'wage_demand_letter', 'evidence_list'],
    workerOnly: true,
  },
  {
    key: 'labor_contract_pack',
    label: '入职签约套装',
    desc: '劳动合同 + 保密约定（通用合同）',
    types: ['labor_contract', 'contract'],
    workerOnly: true,
  },
  {
    key: 'labor_mediation_pack',
    label: '调解和解套装',
    desc: '调解协议书 + 和解协议',
    types: ['mediation', 'settlement_agreement'],
    workerOnly: true,
  },
  {
    key: 'civil_complaint_full',
    label: '民事起诉全套',
    desc: '起诉状 + 证据清单 + 代理词',
    types: ['complaint', 'evidence_list', 'agency_opinion'],
    workerOnly: false,
  },
  {
    key: 'defense_full',
    label: '答辩全套',
    desc: '答辩状 + 证据清单 + 代理词',
    types: ['answer', 'evidence_list', 'agency_opinion'],
    workerOnly: false,
  },
  {
    key: 'appeal_full',
    label: '上诉全套',
    desc: '上诉状 + 证据清单',
    types: ['appeal', 'evidence_list'],
    workerOnly: false,
  },
];

export function docTypeLabel(value: string): string {
  const canonical = normalizeDocType(value);
  return DOC_TYPES.find((d) => d.value === canonical)?.label ?? value;
}
