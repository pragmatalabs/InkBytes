import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

/**
 * NewsMarkdown — renders a synthesized news body (`synthesis_md`) as richly
 * formatted markdown with the InkBytes type system, plus inline source chips.
 *
 * Replaces the old paragraph-only renderer: now full markdown (headings, bold,
 * lists, blockquotes, links, tables, code, rules) renders properly, so the
 * synthesis prompt's structured output (lead → sections → key points) reads
 * the way it's written. Source citations written as `[Source: BBC]` /
 * `[Fuente: …]` are turned into small inline chips via the rehype pass below.
 *
 * Safety: raw HTML in the markdown is NOT rendered (no rehype-raw), so an LLM
 * that emits `<script>` can't inject anything — it's escaped as text.
 */

const CITATION_RE = /\[(?:Source|Fuente):\s*[^\]]+\]/g;

/**
 * rehype plugin: walk the HAST, split any text node containing
 * `[Source: …]` / `[Fuente: …]` and replace each marker with a `<cite>`
 * element (mapped to a styled chip in `components` below). Operating on HAST
 * (post-markdown) keeps it independent of surrounding markdown structure.
 */
function rehypeSourceChips() {
  type HastNode = {
    type: string;
    value?: string;
    tagName?: string;
    properties?: Record<string, unknown>;
    children?: HastNode[];
  };

  const splitTextNode = (value: string): HastNode[] => {
    const out: HastNode[] = [];
    let last = 0;
    for (const m of value.matchAll(CITATION_RE)) {
      const start = m.index ?? 0;
      if (start > last) out.push({ type: "text", value: value.slice(last, start) });
      // strip the surrounding [ ] for display; keep "Source: BBC"
      const label = m[0].slice(1, -1).trim();
      out.push({
        type: "element",
        tagName: "cite",
        properties: {},
        children: [{ type: "text", value: label }],
      });
      last = start + m[0].length;
    }
    if (last < value.length) out.push({ type: "text", value: value.slice(last) });
    return out;
  };

  const walk = (node: HastNode) => {
    if (!node.children) return;
    const next: HastNode[] = [];
    for (const child of node.children) {
      if (child.type === "text" && child.value && CITATION_RE.test(child.value)) {
        CITATION_RE.lastIndex = 0; // reset the stateful /g regex before splitting
        next.push(...splitTextNode(child.value));
      } else {
        if (child.children) walk(child);
        next.push(child);
      }
    }
    node.children = next;
  };

  return (tree: HastNode) => walk(tree);
}

const components: Components = {
  h1: ({ children }) => (
    <h2 className="mt-7 mb-2.5 text-[22px] font-bold tracking-tight text-[var(--ink)]">{children}</h2>
  ),
  h2: ({ children }) => (
    <h2 className="mt-7 mb-2.5 text-[20px] font-bold tracking-tight text-[var(--ink)]">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="mt-5 mb-2 text-[16px] font-semibold uppercase tracking-[0.06em] text-[var(--ink-muted)]">{children}</h3>
  ),
  p: ({ children }) => <p className="mb-5 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="mb-5 list-disc space-y-1.5 pl-5 marker:text-[var(--accent-dot)]">{children}</ul>,
  ol: ({ children }) => <ol className="mb-5 list-decimal space-y-1.5 pl-5 marker:text-[var(--ink-muted)]">{children}</ol>,
  li: ({ children }) => <li className="leading-[1.7] pl-1">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-6 border-l-[3px] border-[var(--accent-dot)] pl-4 text-[var(--ink-muted)] italic">{children}</blockquote>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[var(--accent)] underline underline-offset-2 decoration-1 hover:opacity-75 transition-opacity"
    >
      {children}
    </a>
  ),
  strong: ({ children }) => <strong className="font-semibold text-[var(--ink)]">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  hr: () => <hr className="my-8 border-t border-[var(--border)]" />,
  code: ({ children }) => (
    <code className="font-mono text-[13px] bg-gray-100 rounded px-1.5 py-0.5 text-[var(--ink)]">{children}</code>
  ),
  table: ({ children }) => (
    <div className="my-6 overflow-x-auto">
      <table className="w-full border-collapse text-[14px]">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border-b border-[var(--border)] px-3 py-2 text-left font-semibold text-[var(--ink)]">{children}</th>
  ),
  td: ({ children }) => <td className="border-b border-[var(--border)]/60 px-3 py-2 align-top">{children}</td>,
  // Inline source citation chip (emitted by rehypeSourceChips above).
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  cite: ({ children }: any) => (
    <cite className="not-italic inline-block align-middle mx-0.5 rounded bg-gray-100 px-1.5 py-px font-mono text-[10px] font-medium leading-none text-[var(--ink-muted)]">
      {children}
    </cite>
  ),
};

export function NewsMarkdown({ source }: { source: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeSourceChips]}
      components={components}
    >
      {source}
    </ReactMarkdown>
  );
}
