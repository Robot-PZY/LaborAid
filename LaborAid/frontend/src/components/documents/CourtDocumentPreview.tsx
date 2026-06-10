import { useEffect, useRef, useState } from 'react';
import { documentApi } from '@/lib/api';

type Props = {
  content: string;
  title?: string;
  className?: string;
};

/**
 * 法院标准文书预览 — Shadow DOM 隔离全局 Tailwind，避免标题被染成主题色；
 * 解析规则与 Word/HTML 导出一致。
 */
export default function CourtDocumentPreview({ content, title, className = '' }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [html, setHtml] = useState('');
  const [css, setCss] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await documentApi.renderPreview(content, title);
        if (!cancelled) {
          setHtml(result.html);
          setCss(result.css);
        }
      } catch {
        if (!cancelled) {
          setError('预览加载失败，请确认后端已启动后刷新页面');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 280);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [content, title]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || loading || error || !html || !css) return;

    let shadowRoot = host.shadowRoot;
    if (!shadowRoot) {
      shadowRoot = host.attachShadow({ mode: 'open' });
    }

    const bodyHtml = html.includes('class="court-document"')
      ? html
      : `<div class="court-document">${html}</div>`;

    shadowRoot.innerHTML = `<style>${css}</style>${bodyHtml}`;
  }, [html, css, loading, error]);

  if (loading && !html) {
    return (
      <div
        className={`rounded-lg border border-dashed bg-muted/20 px-6 py-12 text-center text-sm text-muted-foreground ${className}`}
      >
        正在加载与 Word 一致的版式预览…
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-6 text-sm text-destructive ${className}`}
      >
        {error}
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="overflow-auto rounded-lg bg-gray-100 p-4">
        <div
          ref={hostRef}
          className="min-h-[12rem] mx-auto bg-white shadow-md"
          style={{ maxWidth: '210mm', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}
          aria-label="法院标准文书预览"
        />
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        预览版式与下载的 Word 文书一致（仿宋正文、黑体/楷体标题、首行缩进 2 字、全黑墨色）。
      </p>
    </div>
  );
}
