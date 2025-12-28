// Use environment variable for production, fallback to proxy path for development
// If VITE_API_BASE_URL is set, append /api/chat to it; otherwise use proxy path
const getApiBase = () => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl) {
    // Remove trailing slash if present, then append /api/chat
    return `${envUrl.replace(/\/$/, '')}/api/chat`;
  }
  return '/api/chat';
};

const API_BASE = getApiBase();

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ChatHistoryResponse {
  messages: Message[];
  has_more: boolean;
  next_cursor: string | null;
}

export interface SendMessageResponse {
  user_message: Message;
  assistant_message: Message;
}

export interface InitChatResponse {
  is_new_user: boolean;
  onboarding_completed: boolean;
  user_id: string;
  greeting: string | null;
}

export interface TypingStatusResponse {
  is_typing: boolean;
  started_at: string | null;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new ApiError(response.status, error.detail || 'Request failed');
  }
  return response.json();
}

export const chatApi = {
  /**
   * Initialize chat session.
   * Creates user if not exists and returns onboarding status.
   */
  async init(): Promise<InitChatResponse> {
    const response = await fetch(`${API_BASE}/init`);
    return handleResponse<InitChatResponse>(response);
  },

  /**
   * Get chat history with cursor-based pagination.
   * @param cursor - ISO timestamp cursor (pass next_cursor from previous response)
   * @param limit - Number of messages to fetch
   */
  async getHistory(cursor?: string, limit = 20): Promise<ChatHistoryResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (cursor) {
      params.append('cursor', cursor);
    }
    
    const response = await fetch(`${API_BASE}/history?${params}`);
    return handleResponse<ChatHistoryResponse>(response);
  },

  /**
   * Send a message and get AI response.
   * @param content - Message content
   */
  async sendMessage(content: string): Promise<SendMessageResponse> {
    const response = await fetch(`${API_BASE}/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    return handleResponse<SendMessageResponse>(response);
  },

  /**
   * Get typing indicator status.
   * Poll this to show typing indicator.
   */
  async getTypingStatus(): Promise<TypingStatusResponse> {
    const response = await fetch(`${API_BASE}/typing`);
    return handleResponse<TypingStatusResponse>(response);
  },
};

