import { useState, useCallback, useRef, useEffect } from 'react';
import { chatApi, Message } from '../services/api';

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  isSending: boolean;
  isTyping: boolean;
  hasMore: boolean;
  error: string | null;
  loadMoreMessages: () => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  clearError: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);
  
  const cursorRef = useRef<string | null>(null);
  const loadingRef = useRef(false);

  // Initialize chat on mount
  useEffect(() => {
    const init = async () => {
      try {
        const response = await chatApi.init();
        setInitialized(true);
        
        // Load initial messages
        await loadMoreMessages();
      } catch (err) {
        setError('Failed to initialize chat. Please refresh the page.');
        console.error('Init error:', err);
      }
    };
    
    init();
  }, []);

  // Load more messages (for infinite scroll)
  const loadMoreMessages = useCallback(async () => {
    if (loadingRef.current || !hasMore) return;
    
    loadingRef.current = true;
    setIsLoading(true);
    
    try {
      const response = await chatApi.getHistory(cursorRef.current || undefined);
      
      // Prepend older messages to the beginning
      setMessages(prev => [...response.messages, ...prev]);
      setHasMore(response.has_more);
      cursorRef.current = response.next_cursor;
    } catch (err) {
      console.error('Failed to load messages:', err);
      setError('Failed to load messages. Please try again.');
    } finally {
      setIsLoading(false);
      loadingRef.current = false;
    }
  }, [hasMore]);

  // Send message
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isSending) return;
    
    setIsSending(true);
    setIsTyping(true);
    setError(null);
    
    // Optimistically add user message
    const tempId = `temp-${Date.now()}`;
    const tempUserMsg: Message = {
      id: tempId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMsg]);
    
    try {
      const response = await chatApi.sendMessage(content);
      
      // Replace temp message with real messages
      setMessages(prev => [
        ...prev.filter(m => m.id !== tempId),
        response.user_message,
        response.assistant_message,
      ]);
    } catch (err: any) {
      // Remove optimistic message on error
      setMessages(prev => prev.filter(m => m.id !== tempId));
      setError(err.message || 'Failed to send message. Please try again.');
    } finally {
      setIsSending(false);
      setIsTyping(false);
    }
  }, [isSending]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    isSending,
    isTyping,
    hasMore,
    error,
    loadMoreMessages,
    sendMessage,
    clearError,
  };
}

