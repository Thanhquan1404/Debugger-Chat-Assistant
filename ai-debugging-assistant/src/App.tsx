import { useEffect, useMemo, useRef, useState } from 'react';
import { ThemeToggle } from './components/ThemeToggle';
import { LogoMark } from './components/LogoMark';
import { ChatComposer } from './components/ChatComposer';
import { EmptyState } from './components/EmptyState';
import { UserMessageView, AssistantMessageView } from './components/ChatMessageView';
import { SourceDrawer } from './components/SourceDrawer';
import { ErrorBanner } from './components/ErrorBanner';
import { executeStreamChat } from './lib/sse';
import type { AssistantMessage, ChatMessage, SourceDoc, UserMessage } from './types/chat';
import { useTheme } from './hooks/useTheme';

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedSource, setSelectedSource] = useState<SourceDoc | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamStartedAtRef = useRef<number | null>(null);
  const scrollAnchorRef = useRef<HTMLDivElement | null>(null);
  const userPausedScrollRef = useRef(false);

  const assistantMessageId = useMemo(() => {
    const assistantMessages = messages.filter((message): message is AssistantMessage => message.role === 'assistant');
    return assistantMessages.at(-1)?.id ?? null;
  }, [messages]);
  const currentAssistantIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!isStreaming) return;
    const interval = window.setInterval(() => {
      if (streamStartedAtRef.current) {
        setElapsedSeconds(Math.min(60, Math.floor((Date.now() - streamStartedAtRef.current) / 1000)));
      }
    }, 200);
    return () => window.clearInterval(interval);
  }, [isStreaming]);

  useEffect(() => {
    if (userPausedScrollRef.current) return;
    scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  const startMessage = (query: string, file: File | null) => {
    const userMessage: UserMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      text: query,
      image: file
        ? { name: file.name, url: URL.createObjectURL(file), size: file.size }
        : undefined,
    };

    const assistantMessage: AssistantMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      sources: [],
      status: 'streaming',
    };

    currentAssistantIdRef.current = assistantMessage.id;
    setMessages((current) => [...current, userMessage, assistantMessage]);
    setIsStreaming(true);
    setElapsedSeconds(0);
    setErrorMessage(null);
    streamStartedAtRef.current = Date.now();

    const form = new FormData();
    if (query) form.append('query', query);
    if (file) form.append('image', file);
    if (sessionId) form.append('session_id', sessionId);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    void executeStreamChat(form, {
      onSession: ({ session_id }) => setSessionId(session_id),
      onSources: (docs) => updateAssistant((message) => ({ ...message, sources: docs })),
      onUsage: ({ usage }) => {
        const reasoningTokens = usage.completion_tokens_details?.reasoning_tokens ?? 0;
        const ttft = usage.latency_checkpoint?.user_visible_ttft_ms;
        updateAssistant((message) => ({
          ...message,
          reasoningTokens,
          latencyMs: ttft ?? message.latencyMs,
        }));
      },
      onDelta: ({ text }) => updateAssistant((message) => ({ ...message, content: message.content + text })),
      onDone: (data) => {
        updateAssistant((message) => ({
          ...message,
          id: data.message_id,
          content: data.answer,
          sources: data.sources,
          status: 'done',
        }));
        currentAssistantIdRef.current = data.message_id;
        finishStreaming(false);
      },
      onError: ({ message }) => {
        updateAssistant((current) => ({ ...current, status: 'error', errorMessage: message }));
        finishStreaming(true, message);
      },
    }, controller.signal);
  };

  const finishStreaming = (reset: boolean, message?: string) => {
    setIsStreaming(false);
    setElapsedSeconds(0);
    streamStartedAtRef.current = null;
    abortControllerRef.current = null;
    if (reset) setSessionId(null);
    if (message) setErrorMessage(message);
  };

  const updateAssistant = (updater: (message: AssistantMessage) => AssistantMessage) => {
    const targetId = currentAssistantIdRef.current;
    if (!targetId) return;
    setMessages((current) => current.map((message) => {
      if (message.role !== 'assistant' || message.id !== targetId) return message;
      return updater(message);
    }));
  };

  const handleLike = async (messageId: string) => {
    const response = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message_id: messageId, value: 'like' }),
    });
    if (!response.ok) throw new Error('Failed to submit feedback.');
  };

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-950 antialiased dark:bg-[#09090b] dark:text-zinc-50">
      <header className="sticky top-0 z-40 border-b border-zinc-200/80 bg-white/90 backdrop-blur dark:border-zinc-800/80 dark:bg-[#09090b]/90">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <LogoMark />
            <div>
              <div className="text-sm font-semibold tracking-tight">UIT-AI Debugging Assistant</div>
              {sessionId && <div className="max-w-44 truncate text-[11px] text-zinc-400" title={sessionId}>Session {sessionId}</div>}
            </div>
          </div>
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
        </div>
      </header>

      <main className="min-h-[calc(100vh-56px)] pb-44">
        <div className="mx-auto max-w-4xl px-4">
          {messages.length === 0 ? <EmptyState onPrompt={(prompt) => startMessage(prompt, null)} /> : messages.map((message) => {
            if (message.role === 'user') return <UserMessageView key={message.id} message={message} />;
            const isCurrentAssistant = message.id === assistantMessageId;
            return (
              <AssistantMessageView
                key={message.id}
                message={message}
                isStreaming={isCurrentAssistant && isStreaming}
                onSourceSelect={setSelectedSource}
                onLike={handleLike}
              />
            );
          })}
          <div ref={scrollAnchorRef} />
        </div>
      </main>

      <div className="fixed inset-x-0 bottom-0 z-30">
        <ChatComposer isStreaming={isStreaming} elapsedSeconds={elapsedSeconds} selectedFile={selectedFile} onFileSelect={setSelectedFile} onSubmit={(query, file) => { startMessage(query, file); setSelectedFile(null); }} />
      </div>

      {selectedSource && <SourceDrawer source={selectedSource} onClose={() => setSelectedSource(null)} />}
      {errorMessage && <ErrorBanner message={errorMessage} onClose={() => setErrorMessage(null)} />}

      <button
        type="button"
        onClick={() => {
          userPausedScrollRef.current = false;
          scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth' });
        }}
        className="sr-only"
      >
        Jump to bottom
      </button>
    </div>
  );
}
