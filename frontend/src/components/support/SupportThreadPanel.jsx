import React, { useCallback, useEffect, useRef, useState } from 'react';
import { showBannerToast } from '../../utils/notifications.js';
import SupportMessageBubble from './SupportMessageBubble.jsx';
import { canReplyToTicket, statusLabel } from '../../utils/supportFormat.js';

export default function SupportThreadPanel({
  ticket,
  messages = [],
  loading = false,
  onSend,
  headerExtra = null,
  showFooterNote = true,
  emptyMessage = 'No messages yet.',
  className = '',
  optimisticAuthorType = 'customer',
  optimisticAuthorName = 'You',
}) {
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [pending, setPending] = useState(null);
  const [showNewChip, setShowNewChip] = useState(false);
  const scrollRef = useRef(null);
  const atBottomRef = useRef(true);
  const prevCountRef = useRef(0);

  const scrollToBottom = useCallback((behavior = 'smooth') => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
    setShowNewChip(false);
    atBottomRef.current = true;
  }, []);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
    atBottomRef.current = nearBottom;
    if (nearBottom) setShowNewChip(false);
  };

  useEffect(() => {
    const count = messages.length + (pending ? 1 : 0);
    if (count > prevCountRef.current) {
      if (atBottomRef.current) {
        scrollToBottom(prevCountRef.current === 0 ? 'auto' : 'smooth');
      } else {
        setShowNewChip(true);
      }
    }
    prevCountRef.current = count;
  }, [messages, pending, scrollToBottom]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const body = draft.trim();
    if (!body || !onSend || sending) return;

    const optimistic = {
      id: `pending-${Date.now()}`,
      author_type: optimisticAuthorType,
      author_name: optimisticAuthorName,
      body,
      created_at: null,
    };
    setPending(optimistic);
    setDraft('');
    setSending(true);

    try {
      await onSend(body);
      setPending(null);
    } catch (err) {
      setPending(null);
      setDraft(body);
      showBannerToast('error', err?.message || 'Could not send message');
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (loading && !ticket) {
    return <div className="support-empty">Loading conversation…</div>;
  }

  if (!ticket) {
    return <div className="support-empty">{emptyMessage}</div>;
  }

  const replyOpen = canReplyToTicket(ticket) && onSend;

  return (
    <div className={`support-thread-panel ${className}`.trim()}>
      <div className="support-thread-header">
        <div>
          <span className="support-ref">{ticket.reference_code}</span>
          <h2 className="support-thread-title">{ticket.subject || ticket.category}</h2>
          {ticket.requester_name && ticket.requester_email && (
            <p className="support-thread-subtitle">
              {ticket.requester_name} · {ticket.requester_email}
            </p>
          )}
        </div>
        <div className="support-thread-header-actions">
          {!headerExtra && (
            <span className={`support-status-pill support-status-pill--${ticket.status}`}>
              {statusLabel(ticket.status)}
            </span>
          )}
          {headerExtra}
        </div>
      </div>

      <div className="support-thread-body">
        <div
          ref={scrollRef}
          className="support-messages support-messages--chat"
          role="log"
          aria-live="polite"
          onScroll={handleScroll}
        >
          {messages.length === 0 && !pending && (
            <div className="support-thread-empty-hint">{emptyMessage}</div>
          )}
          {messages.map((msg) => (
            <SupportMessageBubble key={msg.id} message={msg} />
          ))}
          {pending && <SupportMessageBubble message={pending} pending />}
        </div>

        {showNewChip && (
          <button type="button" className="support-new-messages-chip" onClick={() => scrollToBottom()}>
            New messages
          </button>
        )}

        {replyOpen && (
          <form className="support-composer" onSubmit={handleSubmit}>
            <textarea
              className="support-composer-input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message…"
              rows={1}
              disabled={sending}
              aria-label="Message"
            />
            <button type="submit" className="support-btn support-composer-send" disabled={sending || !draft.trim()}>
              {sending ? '…' : 'Send'}
            </button>
          </form>
        )}

        {showFooterNote && replyOpen && (
          <p className="support-thread-footer-note">
            Replies may take a few minutes — we&apos;ll email you too.
          </p>
        )}
      </div>
    </div>
  );
}
