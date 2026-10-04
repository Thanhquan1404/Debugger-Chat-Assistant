import type {
  SSEAnswerDeltaData,
  SSEErrorData,
  SSESessionData,
  SSEDoneData,
  SSEUsageData,
  SourceDoc,
  StreamCallbacks,
} from '../types/chat';

const STREAM_ENDPOINT = '/api/chat/stream';
const STREAM_TIMEOUT_MS = 60_000;

interface ApiErrorPayload {
  data: null;
  success: false;
  error?: {
    code?: string;
    message?: string;
  };
}

function parseErrorMessage(payload: ApiErrorPayload | null, status: number): string {
  return payload?.error?.message ?? `Request failed with HTTP ${status}`;
}

export async function executeStreamChat(
  form: FormData,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const timeoutController = new AbortController();
  const timeoutId = window.setTimeout(() => timeoutController.abort(), STREAM_TIMEOUT_MS);

  const effectiveSignal = signal
    ? AbortSignal.any([signal, timeoutController.signal])
    : timeoutController.signal;

  try {
    const response = await fetch(STREAM_ENDPOINT, {
      method: 'POST',
      body: form,
      headers: {
        Accept: 'text/event-stream',
      },
      signal: effectiveSignal,
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as ApiErrorPayload | null;
      throw new Error(parseErrorMessage(payload, response.status));
    }

    if (!response.body) {
      throw new Error('ReadableStream is not available in this browser.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let currentEvent = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? '';

      for (const rawLine of lines) {
        const line = rawLine.trimEnd();
        if (!line || line.startsWith(':')) continue;

        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim();
          continue;
        }

        if (!line.startsWith('data:')) continue;

        const dataText = line.slice(5).trim();
        if (!dataText) continue;

        try {
          const parsed = JSON.parse(dataText) as { data?: unknown };
          const payload = parsed.data;

          switch (currentEvent) {
            case 'session':
              callbacks.onSession(payload as SSESessionData);
              break;
            case 'sources': {
              const docs = (payload as { docs?: SourceDoc[] })?.docs ?? [];
              callbacks.onSources(docs);
              break;
            }
            case 'usage':
              callbacks.onUsage(payload as SSEUsageData);
              break;
            case 'answer_delta':
              callbacks.onDelta(payload as SSEAnswerDeltaData);
              break;
            case 'done':
              callbacks.onDone(payload as SSEDoneData);
              break;
            case 'error':
              callbacks.onError(payload as SSEErrorData);
              return;
            default:
              break;
          }
        } catch {
          // Ignore malformed frames so one bad chunk does not crash the stream parser.
        }
      }
    }
  } catch (error) {
    const isTimeout = timeoutController.signal.aborted && !signal?.aborted;
    const message = isTimeout
      ? 'The upload or processing time exceeded 60 seconds.'
      : error instanceof Error
        ? error.message
        : 'An unknown network error occurred.';

    callbacks.onError({ message });
  } finally {
    window.clearTimeout(timeoutId);
  }
}
