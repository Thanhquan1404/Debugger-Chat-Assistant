import { ChevronDown, CircleCheck, Sparkles } from 'lucide-react';
import { useState } from 'react';
import type { AssistantMessage } from '../types/chat';
import { LoadingIndicator } from './LoadingIndicator';

interface ReasoningPanelProps {
  message: AssistantMessage;
  isStreaming: boolean;
}

export function ReasoningPanel({ message, isStreaming }: ReasoningPanelProps) {
  const [expanded, setExpanded] = useState(isStreaming);
  const hasReasoning = typeof message.reasoningTokens === 'number' && message.reasoningTokens > 0;

  if (!isStreaming && !hasReasoning) return null;

  return (
    <section className="mb-4 overflow-hidden rounded-xl border border-zinc-200 bg-zinc-50/70 dark:border-zinc-800 dark:bg-zinc-900/60">
      <button
        type="button"
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
      >
        <span className="flex size-7 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-300">
          <Sparkles className="size-4" aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium text-zinc-900 dark:text-zinc-100">
            {isStreaming ? 'Reasoning in progress' : 'Reasoning summary'}
          </span>
          <span className="block text-xs text-zinc-500 dark:text-zinc-400">
            {hasReasoning ? `${message.reasoningTokens?.toLocaleString()} reasoning tokens` : 'Preparing response'}
          </span>
        </span>
        <ChevronDown className={`size-4 text-zinc-400 transition ${expanded ? 'rotate-180' : ''}`} aria-hidden="true" />
      </button>

      {expanded && (
        <div className="border-t border-zinc-200 px-4 py-3 dark:border-zinc-800">
          {isStreaming ? (
            <div className="space-y-3">
              <LoadingIndicator label="Analyzing request" />
              <div className="grid gap-2 text-xs text-zinc-500 dark:text-zinc-400 sm:grid-cols-3">
                <ReasoningStep label="Analyze" active />
                <ReasoningStep label="Retrieve" active={hasReasoning} />
                <ReasoningStep label="Compose" active={false} />
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
              <CircleCheck className="size-4 text-emerald-500" aria-hidden="true" />
              Reasoning metadata received. Internal chain-of-thought text is not rendered.
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function ReasoningStep({ label, active }: { label: string; active: boolean }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 py-2 dark:border-zinc-800 dark:bg-zinc-950">
      <span className={`size-1.5 rounded-full ${active ? 'bg-indigo-500' : 'bg-zinc-300 dark:bg-zinc-700'}`} />
      <span>{label}</span>
    </div>
  );
}
