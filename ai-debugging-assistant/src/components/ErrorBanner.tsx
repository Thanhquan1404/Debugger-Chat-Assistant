import { AlertCircle, X } from 'lucide-react';
import { useEffect } from 'react';

interface ErrorBannerProps {
  message: string;
  onClose: () => void;
  durationMs?: number;
}

export function ErrorBanner({ message, onClose, durationMs = 10_000 }: ErrorBannerProps) {
  useEffect(() => {
    const timeoutId = window.setTimeout(onClose, durationMs);
    return () => window.clearTimeout(timeoutId);
  }, [message, onClose, durationMs]);

  return (
    <div className="fixed right-4 top-4 z-50 w-[min(420px,calc(100vw-2rem))] rounded-2xl border border-red-200 bg-white p-4 shadow-panel dark:border-red-950/70 dark:bg-zinc-950">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-red-500/10 text-red-600 dark:text-red-400">
          <AlertCircle className="size-4" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">Processing error</p>
          <p className="mt-1 text-sm leading-6 text-zinc-600 dark:text-zinc-400">{message}</p>
          <p className="mt-2 text-xs text-zinc-400 dark:text-zinc-500">This notification closes automatically after 10 seconds.</p>
        </div>
        <button type="button" onClick={onClose} className="inline-flex size-8 items-center justify-center rounded-lg text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-900 dark:hover:text-zinc-100" aria-label="Close error notification">
          <X className="size-4" />
        </button>
      </div>
    </div>
  );
}
