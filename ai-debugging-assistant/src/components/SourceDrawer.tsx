import { ArrowUpRight, FileSearch, X } from 'lucide-react';
import { useEffect } from 'react';
import type { SourceDoc } from '../types/chat';

interface SourceDrawerProps {
  source: SourceDoc | null;
  onClose: () => void;
}

export function SourceDrawer({ source, onClose }: SourceDrawerProps) {
  useEffect(() => {
    if (!source) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [source, onClose]);

  if (!source) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button className="absolute inset-0 cursor-default bg-black/40 backdrop-blur-[2px]" onClick={onClose} aria-label="Close sources" />
      <aside className="relative h-full w-full max-w-md border-l border-zinc-200 bg-white p-6 shadow-2xl dark:border-zinc-800 dark:bg-zinc-950">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="mb-2 inline-flex size-9 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-300">
              <FileSearch className="size-5" aria-hidden="true" />
            </div>
            <h2 className="text-lg font-semibold text-zinc-950 dark:text-zinc-50">Source details</h2>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Retrieved document metadata</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex size-9 items-center justify-center rounded-lg text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-950 dark:hover:bg-zinc-900 dark:hover:text-zinc-100"
            aria-label="Close source details"
          >
            <X className="size-5" />
          </button>
        </div>

        <dl className="mt-8 space-y-5">
          <Detail label="Document ID" value={source.doc_id} />
          <Detail label="Source type" value={source.source} />
          <Detail label="Score" value={source.score.toFixed(2)} />
          {source.system_name && <Detail label="System" value={source.system_name} />}
          {source.error_code && <Detail label="Error code" value={source.error_code} mono />}
        </dl>

        {source.tags?.length ? (
          <div className="mt-6">
            <div className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-zinc-500">Tags</div>
            <div className="flex flex-wrap gap-2">
              {source.tags.map((tag) => (
                <span key={tag} className="rounded-full border border-zinc-200 px-2.5 py-1 text-xs text-zinc-600 dark:border-zinc-800 dark:text-zinc-300">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        <div className="mt-8 flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
          <ArrowUpRight className="size-4" aria-hidden="true" />
          <span>Source metadata only; document navigation can be added when the backend exposes a source URL.</span>
        </div>
      </aside>
    </div>
  );
}

function Detail({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-[0.12em] text-zinc-500">{label}</dt>
      <dd className={`mt-1 text-sm text-zinc-900 dark:text-zinc-100 ${mono ? 'font-mono' : ''}`}>{value}</dd>
    </div>
  );
}
