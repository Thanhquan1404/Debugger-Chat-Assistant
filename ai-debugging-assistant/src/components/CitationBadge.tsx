import type { SourceDoc } from '../types/chat';

interface CitationBadgeProps {
  docId: string;
  source?: SourceDoc;
  onSelect?: (source: SourceDoc) => void;
}

export function CitationBadge({ docId, source, onSelect }: CitationBadgeProps) {
  const interactive = Boolean(source && onSelect);

  const content = (
    <span className="inline-flex translate-y-[-1px] items-center gap-1 rounded-md border border-indigo-200/80 bg-indigo-50 px-1.5 py-0.5 align-baseline font-mono text-[0.72em] font-medium leading-none text-indigo-700 transition-colors dark:border-indigo-400/20 dark:bg-indigo-400/10 dark:text-indigo-300">
      <FileText className="size-3 shrink-0" aria-hidden="true" />
      <span>{docId}</span>
    </span>
  );

  if (!interactive) {
    return (
      <span className="mx-0.5 whitespace-nowrap" title="Citation source is not available in the retrieved context">
        {content}
      </span>
    );
  }

  if (!source || !onSelect) {
    return content;
  }

  return (
    <button
      type="button"
      onClick={() => onSelect(source)}
      className="mx-0.5 whitespace-nowrap rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60 focus-visible:ring-offset-1 dark:focus-visible:ring-offset-zinc-950"
      title={`Open source ${docId}`}
      aria-label={`Open citation ${docId}`}
    >
      {content}
    </button>
  );
}
