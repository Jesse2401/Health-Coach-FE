import { Message } from '../services/api';
import './MessageBubble.css';

interface Props {
  message: Message;
}

function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';
  
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true
    });
  };

  // Simple markdown-like formatting for the content
  const formatContent = (content: string) => {
    return content.split('\n').map((line, i) => (
      <span key={i}>
        {line}
        {i < content.split('\n').length - 1 && <br />}
      </span>
    ));
  };

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className={`message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`}>
        <div className="message-content">
          {formatContent(message.content)}
        </div>
        <span className="message-time">
          {formatTime(message.created_at)}
        </span>
      </div>
    </div>
  );
}

export default MessageBubble;

