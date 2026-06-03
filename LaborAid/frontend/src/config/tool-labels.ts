/**
 * 工具显示名称（与 agents.ts 保持一致，供文档与注释引用）
 * 命名风格：动词 + 名词（服务入口「我的×」除外）
 */
export const TOOL_LABELS = {
  docgen: '生成文书',
  contract: '审查合同',
  evidence: '整理证据',
  search: '检索法规',
  enterprise: '查询企业',
  limitation_calc: '时效/期限计算',
  compensation_calc: '赔偿/补偿计算',
  research: '分析案情',
  cases: '管理案件',
  knowledge: '法律知识库',
  templates: '文书模板',
  channels: '专项维权',
  vault: '我的材料',
  guidance: '办事资源',
  records: '我的记录',
} as const;

/** 历史名称 → 现用名称（文档迁移对照） */
export const LEGACY_TOOL_NAME_MAP: Record<string, string> = {
  文墨: TOOL_LABELS.docgen,
  盾律: TOOL_LABELS.contract,
  证链: TOOL_LABELS.evidence,
  法眼: TOOL_LABELS.search,
  研法: TOOL_LABELS.research,
  案管: TOOL_LABELS.cases,
  智库: TOOL_LABELS.knowledge,
  模板库: TOOL_LABELS.templates,
  专项维权: TOOL_LABELS.channels,
  我的材料库: TOOL_LABELS.vault,
  写文书: TOOL_LABELS.docgen,
  审合同: TOOL_LABELS.contract,
  查法律: TOOL_LABELS.search,
  案情分析: TOOL_LABELS.research,
  我的案件: TOOL_LABELS.cases,
};
