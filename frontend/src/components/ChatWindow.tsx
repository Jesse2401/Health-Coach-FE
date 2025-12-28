import { useRef, useEffect, useCallback } from 'react';
import { useChat } from '../hooks/useChat';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';
import ChatInput from './ChatInput';
import ChatHeader from './ChatHeader';
import './ChatWindow.css';

function ChatWindow() {
  const {
    messages,
    isLoading,
    isSending,
    isTyping,
    hasMore,
    error,
    loadMoreMessages,
    sendMessage,
    clearError,
  } = useChat();
  
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevScrollHeightRef = useRef(0);
  const isInitialLoadRef = useRef(true);

  // Auto-scroll to bottom on new messages (only for new outgoing messages)
  useEffect(() => {
    if (isInitialLoadRef.current && messages.length > 0) {
      // Initial load - scroll to bottom
      bottomRef.current?.scrollIntoView();
      isInitialLoadRef.current = false;
    } else if (messages.length > 0) {
      // Check if user sent a message (last message is from user or we just got a response)
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === 'assistant' || isSending) {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }, [messages, isSending]);

  // Maintain scroll position when loading older messages
  useEffect(() => {
    if (containerRef.current && prevScrollHeightRef.current > 0) {
      const newScrollHeight = containerRef.current.scrollHeight;
      containerRef.current.scrollTop = newScrollHeight - prevScrollHeightRef.current;
      prevScrollHeightRef.current = 0;
    }
  }, [messages]);

  // Infinite scroll handler
  const handleScroll = useCallback(() => {
    if (!containerRef.current || isLoading || !hasMore) return;
    
    // Load more when scrolled near the top
    if (containerRef.current.scrollTop < 100) {
      prevScrollHeightRef.current = containerRef.current.scrollHeight;
      loadMoreMessages();
    }
  }, [isLoading, hasMore, loadMoreMessages]);

  return (
    <div className="chat-window">
      <ChatHeader />
      
      {error && (
        <div className="error-banner" onClick={clearError}>
          {error}
          <span className="error-dismiss">×</span>
        </div>
      )}
      
      <div 
        ref={containerRef}
        className="messages-container"
        onScroll={handleScroll}
      >
        {isLoading && (
          <div className="loading-indicator">
            <div className="loading-spinner"></div>
            <span>Loading messages...</span>
          </div>
        )}
        
        {!hasMore && messages.length > 0 && (
          <div className="chat-start-indicator">
            Start of conversation
          </div>
        )}
        
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {isTyping && <TypingIndicator />}
        
        <div ref={bottomRef} />
      </div>
      
      <ChatInput onSend={sendMessage} disabled={isSending} />
    </div>
  );
}

export default ChatWindow;

