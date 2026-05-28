import { documentApi } from '@/lib/api';
import type { Document } from '@/lib/api';

export type DocumentExportFormat = 'word' | 'pdf' | 'markdown' | 'html';

const EXT: Record<DocumentExportFormat, string> = {
  word: 'docx',
  pdf: 'pdf',
  markdown: 'md',
  html: 'html',
};

function safeFilename(title: string, ext: string): string {
  const base = (title || '法律文书').replace(/[<>:"/\\|?*\x00-\x1f]/g, '_').trim();
  return `${base.slice(0, 80)}.${ext}`;
}

async function blobToErrorMessage(blob: Blob): Promise<string | null> {
  const type = blob.type || '';
  if (!type.includes('json') && blob.size > 512) return null;
  try {
    const text = await blob.text();
    const data = JSON.parse(text) as { detail?: string | { msg?: string }[] };
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail) && data.detail[0]?.msg) return data.detail[0].msg;
    if (text.length < 200) return text;
  } catch {
    // not JSON
  }
  return null;
}

/** 触发浏览器下载已生成的文书 */
export async function downloadDocumentFile(
  doc: Pick<Document, 'id' | 'title'>,
  format: DocumentExportFormat,
): Promise<void> {
  let blob: Blob;
  switch (format) {
    case 'word':
      blob = await documentApi.exportWord(doc.id);
      break;
    case 'pdf':
      blob = await documentApi.exportPdf(doc.id);
      break;
    case 'html':
      blob = await documentApi.exportHtml(doc.id);
      break;
    default:
      blob = await documentApi.exportMarkdown(doc.id);
      break;
  }

  const errMsg = await blobToErrorMessage(blob);
  if (errMsg) throw new Error(errMsg);

  const ext = EXT[format];
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = safeFilename(doc.title || '法律文书', ext);
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
