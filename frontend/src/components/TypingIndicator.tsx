import './TypingIndicator.css';

function TypingIndicator() {
  return (
    <div className="message-row assistant">
      <div className="typing-bubble">
        <div className="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
}

export default TypingIndicator;

