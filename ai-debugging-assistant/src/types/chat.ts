export type SourceType = 'static' | 'dynamic';

export interface SourceDoc {
  doc_id: string;
  source: SourceType;
  score: number;
  system_name?: string;
  error_code?: string;
  tags?: string[];
}

export interface UserMessage {
  id: string;
  role: 'user';
  text: string;
  image?: {
    name: string;
    url: string;
    size: number;
  };
}

export interface AssistantMessage {
  id: string;
  role: 'assistant';
  content: string;
  sources: SourceDoc[];
  reasoningTokens?: number;
  latencyMs?: number;
  status: 'streaming' | 'done' | 'error';
  errorMessage?: string;
}

export type ChatMessage = UserMessage | AssistantMessage;

export interface SSESessionData {
  session_id: string;
  user_message_id: string;
}

export interface SSEUsageData {
  usage: {
    completion_tokens: number;
    completion_tokens_details?: {
      reasoning_tokens?: number;
    };
    latency_checkpoint?: {
      user_visible_ttft_ms?: number;
    };
  };
}

export interface SSEAnswerDeltaData {
  text: string;
}

export interface SSEDoneData {
  message_id: string;
  answer: string;
  sources: SourceDoc[];
  usage: Record<string, unknown>;
}

export interface SSEErrorData {
  message: string;
}

export interface StreamCallbacks {
  onSession: (data: SSESessionData) => void;
  onSources: (docs: SourceDoc[]) => void;
  onUsage: (data: SSEUsageData) => void;
  onDelta: (data: SSEAnswerDeltaData) => void;
  onDone: (data: SSEDoneData) => void;
  onError: (data: SSEErrorData) => void;
}
