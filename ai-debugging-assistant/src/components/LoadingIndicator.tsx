interface LoadingIndicatorProps {
  label?: string;
}

export function LoadingIndicator({ label = 'Thinking' }: LoadingIndicatorProps) {
  return (
    <div className="inline-flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400" aria-live="polite">
      <span className="relative flex size-4 items-center justify-center" aria-hidden="true">
        <span className="absolute size-4 animate-spin rounded-full border-2 border-zinc-200 border-t-indigo-500 dark:border-zinc-800 dark:border-t-indigo-400" />
        <span className="size-1.5 rounded-full bg-indigo-500 dark:bg-indigo-400" />
      </span>
      <span>{label}</span>
      <span className="thinking-dots inline-flex gap-0.5" aria-hidden="true">
        <span>.</span><span>.</span><span>.</span>
      </span>
    </div>
  );
}
