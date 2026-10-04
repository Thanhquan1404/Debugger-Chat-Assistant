import { ImagePlus, MessageSquareText, SearchCheck } from 'lucide-react';

interface EmptyStateProps {
  onPrompt: (text: string) => void;
}

const prompts = [
  'Why am I getting a 503 Service Unavailable error?',
  'Analyze this API error and suggest a fix.',
  'Find the likely root cause of this stack trace.',
];

export function EmptyState({ onPrompt }: EmptyStateProps) {
  return (
    <div className="flex min-h-[55vh] flex-col items-center justify-center px-6 py-16 text-center">
      <div className="mb-5 flex size-14 items-center justify-center rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <SearchCheck className="size-6 text-indigo-500" />
      </div>
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">AI Debugging Assistant</h1>
      <p className="mt-3 max-w-xl text-sm leading-7 text-zinc-500 dark:text-zinc-400">Upload an error screenshot or describe the problem. The assistant will retrieve relevant sources and stream a response.</p>
      <div className="mt-7 flex flex-wrap items-center justify-center gap-2">
        <button type="button" onClick={() => onPrompt(prompts[0])} className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-3.5 py-2 text-xs text-zinc-600 transition hover:border-zinc-300 hover:text-zinc-950 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:border-zinc-700 dark:hover:text-zinc-50">
          <MessageSquareText className="size-3.5" />
          Use a starter prompt
        </button>
        <span className="inline-flex items-center gap-2 rounded-full border border-zinc-200 px-3.5 py-2 text-xs text-zinc-400 dark:border-zinc-800"><ImagePlus className="size-3.5" />Upload screenshot</span>
      </div>
    </div>
  );
}
