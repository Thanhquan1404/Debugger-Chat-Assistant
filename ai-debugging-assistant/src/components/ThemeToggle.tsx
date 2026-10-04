import { Moon, Sun } from 'lucide-react';
import type { ThemeMode } from '../hooks/useTheme';

interface ThemeToggleProps {
  theme: ThemeMode;
  onToggle: () => void;
}

export function ThemeToggle({ theme, onToggle }: ThemeToggleProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="inline-flex size-9 items-center justify-center rounded-lg border border-zinc-200 bg-white text-zinc-600 transition hover:border-zinc-300 hover:text-zinc-950 focus:outline-none focus:ring-2 focus:ring-indigo-500/60 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:border-zinc-700 dark:hover:text-zinc-50"
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </button>
  );
}
