import { Bot, Copy, ThumbsDown, ThumbsUp, UserRound } from 'lucide-react';
import { useState } from 'react';
import type { ReactNode } from 'react';
import type { AssistantMessage, SourceDoc, UserMessage } from '../types/chat';
import { MarkdownRenderer } from './MarkdownRenderer';
import { ReasoningPanel } from './ReasoningPanel';
import { SourceChips } from './SourceChips';

interface UserMessageViewProps {
  message: UserMessage;
}

interface AssistantMessageViewProps {
  message: AssistantMessage;
  isStreaming: boolean;
  onSourceSelect: (source: SourceDoc) => void;
  onLike: (messageId: string) => Promise<void>;
}

export function UserMessageView({ message }: UserMessageViewProps) {
  return (
    <article className="flex gap-3 px-1 py-5">
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200">
        <UserRound className="size-4" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 text-xs font-medium uppercase tracking-[0.12em] text-zinc-400">You</div>
        {message.image && <img src={message.image.url} alt={message.image.name} className="mb-3 max-h-72 max-w-full rounded-xl border border-zinc-200 object-contain dark:border-zinc-800" />}
        {message.text && <p className="whitespace-pre-wrap text-sm leading-7 text-zinc-900 dark:text-zinc-100">{message.text}</p>}
      </div>
    </article>
  );
}

export function AssistantMessageView({ message, isStreaming, onSourceSelect, onLike }: AssistantMessageViewProps) {
  const [liked, setLiked] = useState(false);
  const [disliked, setDisliked] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  };

  const handleLike = async () => {
    if (liked || !message.id) return;
    await onLike(message.id);
    setLiked(true);
    setDisliked(false);
  };

  const handleDislike = () => {
    setDisliked((value) => !value);
    setLiked(false);
  };

  return (
    <article className="flex gap-3 border-t border-zinc-100 px-1 py-6 dark:border-zinc-900">
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-indigo-500/10 text-indigo-600 dark:text-indigo-300">
        <Bot className="size-4" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-3 text-xs font-medium uppercase tracking-[0.12em] text-zinc-400">Assistant</div>
        <SourceChips sources={message.sources} onSelect={onSourceSelect} />
        <ReasoningPanel message={message} isStreaming={isStreaming} />
        <MarkdownRenderer
          content={message.content}
          streaming={isStreaming}
          sources={message.sources}
          onCitationSelect={onSourceSelect}
        />

        {message.status === 'error' && message.errorMessage && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-950/70 dark:bg-red-950/20 dark:text-red-300">
            {message.errorMessage}
          </div>
        )}

        {message.status === 'done' && (
          <div className="mt-5 flex flex-wrap items-center gap-1.5 border-t border-zinc-100 pt-3 dark:border-zinc-900">
            <ActionButton icon={<Copy className="size-3.5" />} label={copied ? 'Copied' : 'Copy'} onClick={handleCopy} />
            <ActionButton icon={<ThumbsUp className="size-3.5" />} label="Like" onClick={() => void handleLike()} active={liked} disabled={liked} />
            <ActionButton icon={<ThumbsDown className="size-3.5" />} label="Dislike" onClick={handleDislike} active={disliked} />
          </div>
        )}
      </div>
    </article>
  );
}

function ActionButton({ icon, label, onClick, active = false, disabled = false }: { icon: ReactNode; label: string; onClick: () => void; active?: boolean; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs transition ${active ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-950' : 'text-zinc-500 hover:bg-zinc-100 hover:text-zinc-950 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-100'} disabled:cursor-default disabled:opacity-80`}
    >
      {icon}
      {label}
    </button>
  );
}
