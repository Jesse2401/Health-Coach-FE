import './ChatHeader.css';

function ChatHeader() {
  return (
    <header className="chat-header">
      <div className="header-avatar">
        <span className="avatar-icon">🏥</span>
        <span className="online-indicator"></span>
      </div>
      <div className="header-info">
        <h1 className="header-title">Health Coach</h1>
        <span className="header-status">Online • Here to help</span>
      </div>
    </header>
  );
}

export default ChatHeader;

