import { Database, FileText } from 'lucide-react';
import type { SourceDoc } from '../types/chat';

interface SourceChipsProps {
  sources: SourceDoc[];
  onSelect: (source: SourceDoc) => void;
}

export function SourceChips({ sources, onSelect }: SourceChipsProps) {
  if (!sources.length) return null;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      <span className="mr-1 text-xs font-medium uppercase tracking-[0.12em] text-zinc-400">Sources</span>
      {sources.map((source) => {
        const Icon = source.source === 'dynamic' ? Database : FileText;
        return (
          <button
            type="button"
            key={`${source.doc_id}-${source.score}`}
            onClick={() => onSelect(source)}
            className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-xs text-zinc-600 transition hover:border-zinc-300 hover:text-zinc-950 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-300 dark:hover:border-zinc-700 dark:hover:text-zinc-50"
          >
            <Icon className="size-3.5 text-blue-500" aria-hidden="true" />
            <span>{source.doc_id}</span>
            <span className="text-zinc-400">{source.score.toFixed(2)}</span>
          </button>
        );
      })}
    </div>
  );
}
