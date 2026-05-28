import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';

/** Reusable MarkdownRenderer with Tailwind-styled components */
export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={MARKDOWN_COMPONENTS}
    >
      {content}
    </ReactMarkdown>
  );
}

/** Tailwind-styled markdown component overrides */
const MARKDOWN_COMPONENTS: Components = {
  h1: ({ children }) => (
    <h1 className="text-xl font-bold mt-6 mb-3 text-foreground">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-lg font-bold mt-5 mb-2 text-foreground">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-base font-semibold mt-4 mb-2 text-foreground">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-sm font-semibold mt-3 mb-1 text-foreground">{children}</h4>
  ),
  p: ({ children }) => (
    <p className="text-sm my-1.5 leading-relaxed">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-foreground">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic">{children}</em>
  ),
  ul: ({ children }) => (
    <ul className="my-2 space-y-1">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-2 space-y-1 list-decimal ml-4">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="text-sm leading-relaxed ml-4 list-disc">{children}</li>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-primary/30 pl-3 my-2 text-sm italic text-muted-foreground">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-4 border-border" />,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary underline hover:text-primary/80"
    >
      {children}
    </a>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-3">
      <table className="border-collapse w-full border text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-muted/50">{children}</thead>
  ),
  tbody: ({ children }) => (
    <tbody>{children}</tbody>
  ),
  tr: ({ children }) => (
    <tr className="border-b hover:bg-muted/30">{children}</tr>
  ),
  th: ({ children }) => (
    <th className="border px-3 py-2 text-left text-sm font-semibold">{children}</th>
  ),
  td: ({ children }) => (
    <td className="border px-3 py-2 text-sm">{children}</td>
  ),
  code: ({ className, children, ...props }) => {
    const isInline = !className;
    if (isInline) {
      return (
        <code className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="overflow-x-auto rounded-lg bg-muted p-4 my-3 text-xs font-mono leading-relaxed">
      {children}
    </pre>
  ),
};
