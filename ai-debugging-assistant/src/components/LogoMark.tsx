import { Bot } from 'lucide-react';

export function LogoMark() {
  return (
    <div className="flex size-9 items-center justify-center rounded-xl border border-zinc-200 bg-white text-zinc-900 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100">
      <Bot className="size-5" strokeWidth={1.8} aria-hidden="true" />
    </div>
  );
}
