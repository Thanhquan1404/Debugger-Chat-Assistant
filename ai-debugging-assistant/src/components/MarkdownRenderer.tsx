import { CodeBlock } from './CodeBlock';
import type { ReactNode } from 'react';
import { CitationBadge } from './CitationBadge';
import type { SourceDoc } from '../types/chat';

interface MarkdownRendererProps {
  content: string;
  streaming?: boolean;
  sources?: SourceDoc[];
  onCitationSelect?: (source: SourceDoc) => void;
}

const CITATION_PATTERN = /\[([A-Za-z0-9][A-Za-z0-9._:-]*)\]/g;

function renderInlineContent(text: string, sources: SourceDoc[], onCitationSelect?: (source: SourceDoc) => void) {
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let match: RegExpExecArray | null;

  CITATION_PATTERN.lastIndex = 0;

  while ((match = CITATION_PATTERN.exec(text)) !== null) {
    if (match.index > cursor) {
      nodes.push(text.slice(cursor, match.index));
    }

    const docId = match[1];
    const source = sources.find((item) => item.doc_id === docId);

    if (!source) {
      nodes.push(match[0]);
      cursor = match.index + match[0].length;
      continue;
    }

    nodes.push(
      <CitationBadge
        key={`citation-${match.index}-${docId}`}
        docId={docId}
        source={source}
        onSelect={onCitationSelect}
      />,
    );

    cursor = match.index + match[0].length;
  }

  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }

  return nodes.length ? nodes : [text];
}

export function MarkdownRenderer({
  content,
  streaming = false,
  sources = [],
  onCitationSelect,
}: MarkdownRendererProps) {
  const blocks = content.split(/```/g);

  return (
    <div className="prose prose-sm max-w-none dark:prose-invert prose-headings:scroll-mt-20 prose-headings:font-semibold prose-p:leading-7 prose-pre:m-0 prose-pre:bg-transparent">
      {blocks.map((block, index) => {
        const isCode = index % 2 === 1;
        if (isCode) {
          const [languageLine, ...codeLines] = block.split('\n');
          const language = languageLine?.trim() || 'text';
          const code = codeLines.join('\n');
          return <CodeBlock key={`code-${index}`} code={code} language={language} />;
        }

        return block.split('\n\n').map((paragraph, paragraphIndex) => {
          const trimmed = paragraph.trim();
          if (!trimmed) return null;

          const key = `${index}-${paragraphIndex}`;
          if (trimmed.startsWith('### ')) {
            return (
              <h3 key={key} className="text-base text-zinc-950 dark:text-zinc-50">
                {renderInlineContent(trimmed.slice(4), sources, onCitationSelect)}
              </h3>
            );
          }

          if (trimmed.startsWith('## ')) {
            return (
              <h2 key={key} className="text-lg text-zinc-950 dark:text-zinc-50">
                {renderInlineContent(trimmed.slice(3), sources, onCitationSelect)}
              </h2>
            );
          }

          if (trimmed.startsWith('- ')) {
            return (
              <ul key={key} className="space-y-1 pl-5">
                {trimmed.split('\n').map((line, lineIndex) => (
                  <li key={`${key}-${lineIndex}`}>{renderInlineContent(line.replace(/^[-]\s+/, ''), sources, onCitationSelect)}</li>
                ))}
              </ul>
            );
          }

          return <p key={key}>{renderInlineContent(trimmed, sources, onCitationSelect)}</p>;
        });
      })}

      {streaming && (
        <span
          className="ml-1 inline-block h-4 w-0.5 translate-y-0.5 animate-pulse bg-indigo-500 align-middle"
          aria-label="Generating"
        />
      )}
    </div>
  );
}
