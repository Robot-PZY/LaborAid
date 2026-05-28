import type { OcrStatus } from '@/components/ocr/OcrStatusBadge';

const TECHNICAL_PATTERN =
  /OCR|视觉|模型|百炼|qwen|deepseek|API|\.env|VISION|LLM|配置|通义|dashscope/i;

/** User-facing OCR hint — hides admin / model configuration details. */
export function userFacingOcrMessage(
  status?: OcrStatus | string | null,
  message?: string | null,
): string | undefined {
  if (!message?.trim()) return undefined;
  const trimmed = message.trim();
  const key = status ?? 'pending';

  if (key === 'processing') return undefined;
  if (key === 'success') {
    return TECHNICAL_PATTERN.test(trimmed) ? undefined : trimmed;
  }
  if (key === 'failed' || key === 'pending') {
    if (TECHNICAL_PATTERN.test(trimmed)) {
      return '识别失败，请上传更清晰的文件后重试';
    }
    if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
      return '识别失败，请上传更清晰的文件后重试';
    }
    return trimmed;
  }
  return TECHNICAL_PATTERN.test(trimmed) ? undefined : trimmed;
}
