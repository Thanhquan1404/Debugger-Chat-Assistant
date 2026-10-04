import { ImagePlus, Send, Timer, UploadCloud, X } from 'lucide-react';
import { useRef, useState } from 'react';
import type { DragEvent } from 'react';
import { ImagePreview } from './ImagePreview';

interface ChatComposerProps {
  isStreaming: boolean;
  elapsedSeconds: number;
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onSubmit: (query: string, file: File | null) => void;
}

const ALLOWED_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp']);
const MAX_FILE_SIZE = 10 * 1024 * 1024;

export function ChatComposer({ isStreaming, elapsedSeconds, selectedFile, onFileSelect, onSubmit }: ChatComposerProps) {
  const [query, setQuery] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const acceptFile = (file: File) => {
    if (!ALLOWED_TYPES.has(file.type)) return;
    if (file.size > MAX_FILE_SIZE) return;
    onFileSelect(file);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
    const file = event.dataTransfer.files.item(0);
    if (file) acceptFile(file);
  };

  const handleSubmit = () => {
    if (isStreaming) return;
    if (!query.trim() && !selectedFile) return;
    onSubmit(query.trim(), selectedFile);
    setQuery('');
  };

  return (
    <div className="border-t border-zinc-200 bg-white/95 px-4 pb-4 pt-3 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/95">
      <div
        className={`mx-auto max-w-4xl rounded-2xl border p-3 transition ${dragActive ? 'border-indigo-400 bg-indigo-50/60 dark:border-indigo-500/60 dark:bg-indigo-950/20' : 'border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900/60'}`}
        onDragEnter={(event) => { event.preventDefault(); setDragActive(true); }}
        onDragOver={(event) => { event.preventDefault(); setDragActive(true); }}
        onDragLeave={(event) => { event.preventDefault(); setDragActive(false); }}
        onDrop={handleDrop}
      >
        {(selectedFile || dragActive) && (
          <div className="mb-3 flex items-center justify-between gap-3">
            {selectedFile ? <ImagePreview file={selectedFile} onRemove={() => onFileSelect(null)} /> : <DropHint />}
            {dragActive && <button type="button" onClick={() => setDragActive(false)} aria-label="Close drop indicator" className="text-zinc-400"><X className="size-4" /></button>}
          </div>
        )}

        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              handleSubmit();
            }
          }}
          disabled={isStreaming}
          placeholder="Describe the error or upload a screenshot..."
          rows={2}
          className="w-full resize-none bg-transparent px-1 py-1 text-sm leading-6 text-zinc-950 outline-none placeholder:text-zinc-400 disabled:cursor-not-allowed dark:text-zinc-50"
        />

        <div className="mt-2 flex items-center justify-between gap-2">
          <div className="flex items-center gap-1">
            <button type="button" disabled={isStreaming} onClick={() => inputRef.current?.click()} className="inline-flex items-center gap-2 rounded-lg px-2.5 py-2 text-xs text-zinc-500 transition hover:bg-white hover:text-zinc-950 disabled:opacity-50 dark:hover:bg-zinc-800 dark:hover:text-zinc-100" title="Upload screenshot">
              <ImagePlus className="size-4" />
              <span className="hidden sm:inline">Upload image</span>
            </button>
            <span className="hidden text-[11px] text-zinc-400 sm:inline">PNG, JPEG, WebP · up to 10 MB</span>
            <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; if (file) acceptFile(file); event.currentTarget.value = ''; }} />
          </div>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={isStreaming || (!query.trim() && !selectedFile)}
            className="inline-flex min-w-24 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isStreaming ? <><Timer className="size-4" />{formatElapsed(elapsedSeconds)}</> : <><Send className="size-4" />Send</>}
          </button>
        </div>

        {dragActive && !selectedFile && <DropHint />}
      </div>
      <p className="mx-auto mt-2 max-w-4xl text-center text-[11px] text-zinc-400">Enter to send · Shift+Enter for a new line</p>
    </div>
  );
}

function formatElapsed(totalSeconds: number) {
  return `00:${String(totalSeconds).padStart(2, '0')}s`;
}

function DropHint() {
  return (
    <div className="flex flex-1 items-center gap-2 rounded-xl border border-dashed border-indigo-300 bg-indigo-50 px-3 py-2 text-xs text-indigo-700 dark:border-indigo-900 dark:bg-indigo-950/20 dark:text-indigo-300">
      <UploadCloud className="size-4" />
      Drop your screenshot here
    </div>
  );
}
