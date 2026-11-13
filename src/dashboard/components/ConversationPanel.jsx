import React, { useEffect, useRef, useState } from 'react';
import { DashboardIcon } from './DashboardIcon.jsx';

export function ConversationPanel({
  messages,
  isTyping,
  onSendMessage,
  quickReplies = [],
}) {
  const [draftText, setDraftText] = useState('');
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = draftText.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setDraftText('');
  };

  return (
    <section className="miora-card miora-conv-panel" aria-labelledby="conversation-panel-title">
      <div className="miora-card-header">
        <div className="miora-card-title-group">
          <span className="miora-card-icon" aria-hidden="true">
            <DashboardIcon name="messageCircle" size={20} strokeWidth={1.65} />
          </span>
          <h2 id="conversation-panel-title" className="miora-card-title">
            Conversation
          </h2>
        </div>
        <span className="miora-conv-meta">Guided Check-in</span>
      </div>

      <div className="miora-conv-messages" ref={listRef} aria-live="polite">
        {messages.map((msg) => {
          const isAi = msg.sender === 'ai';
          return (
            <div
              key={msg.id}
              className={`miora-conv-row ${isAi ? 'is-ai' : 'is-mother'}`}
            >
              {isAi && (
                <span className="miora-conv-avatar is-ai" aria-hidden="true">
                  <DashboardIcon name="sparkle" size={14} />
                </span>
              )}

              <div className="miora-conv-bubble-col">
                <div className={`miora-conv-bubble ${isAi ? 'is-ai' : 'is-mother'}`}>
                  {msg.text}
                </div>
                <span className="miora-conv-time">{msg.timestamp}</span>
              </div>

              {!isAi && (
                <span className="miora-conv-avatar is-mother" aria-hidden="true">
                  <DashboardIcon name="user" size={14} />
                </span>
              )}
            </div>
          );
        })}

        {isTyping && (
          <div className="miora-conv-row is-ai" aria-label="Assistant is typing">
            <span className="miora-conv-avatar is-ai" aria-hidden="true">
              <DashboardIcon name="sparkle" size={14} />
            </span>
            <div className="miora-conv-bubble is-ai miora-typing-bubble">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
      </div>

      {quickReplies.length > 0 && (
        <div className="miora-quick-reply-row" aria-label="Suggested prompt responses">
          {quickReplies.map((reply) => (
            <button
              key={reply}
              type="button"
              className="miora-quick-reply-chip"
              onClick={() => onSendMessage(reply)}
            >
              {reply}
            </button>
          ))}
        </div>
      )}

      <form className="miora-conv-input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={draftText}
          onChange={(e) => setDraftText(e.target.value)}
          placeholder="Record mother's response or note..."
          aria-label="Mother response text"
        />
        <button
          type="submit"
          className="miora-conv-send-btn"
          disabled={!draftText.trim()}
          aria-label="Send response"
        >
          <DashboardIcon name="arrowRight" size={16} strokeWidth={2} />
        </button>
      </form>
    </section>
  );
}

