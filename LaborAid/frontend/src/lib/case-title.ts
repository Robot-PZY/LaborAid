/** 案件标题日期前缀，格式：2026.5.27（月、日不补零） */

const DATE_PREFIX_RE = /^\d{4}\.\d{1,2}\.\d{1,2}\s+/;

export function formatCaseDatePrefix(date = new Date()): string {
  return `${date.getFullYear()}.${date.getMonth() + 1}.${date.getDate()}`;
}

/** 为案件标题加上当日日期前缀；若已有前缀则不再重复添加 */
export function withCaseTitleDatePrefix(title: string, date = new Date()): string {
  const trimmed = title.trim();
  if (!trimmed) return formatCaseDatePrefix(date);
  if (DATE_PREFIX_RE.test(trimmed)) return trimmed;
  return `${formatCaseDatePrefix(date)} ${trimmed}`;
}
