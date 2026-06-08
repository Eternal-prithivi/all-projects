import React, { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import api from '../api';
import PageHeader from '../components/ui/PageHeader.jsx';
import '../styles/support-tickets.css';

function formatDate(value) {
  if (!value) return '';
  return new Date(value).toLocaleString();
}

function statusLabel(status) {
  return (status || '').replace(/_/g, ' ');
}

function SupportPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tickets, setTickets] = useState([]);
  const [selectedRef, setSelectedRef] = useState(searchParams.get('ref') || '');
  const [thread, setThread] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);

  const fetchTickets = useCallback(async () => {
    setLoadingList(true);
    try {
      const res = await api.get('/support/tickets');
      setTickets(res.data.tickets || []);
    } catch {
      toast.error('Could not load support tickets');
    } finally {
      setLoadingList(false);
    }
  }, []);

  const fetchThread = useCallback(async (ref) => {
    if (!ref) {
      setThread(null);
      return;
    }
    setLoadingThread(true);
    try {
      const res = await api.get(`/support/tickets/${encodeURIComponent(ref)}`);
      setThread(res.data);
    } catch {
      toast.error('Could not load ticket thread');
      setThread(null);
    } finally {
      setLoadingThread(false);
    }
  }, []);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  useEffect(() => {
    const ref = searchParams.get('ref');
    if (ref) {
      setSelectedRef(ref);
      return;
    }
    if (tickets.length > 0 && !selectedRef) {
      setSelectedRef(tickets[0].reference_code);
    }
  }, [searchParams, tickets, selectedRef]);

  useEffect(() => {
    if (selectedRef) {
      fetchThread(selectedRef);
    }
  }, [selectedRef, fetchThread]);

  useEffect(() => {
    if (!selectedRef) return undefined;
    const id = setInterval(() => fetchThread(selectedRef), 60000);
    return () => clearInterval(id);
  }, [selectedRef, fetchThread]);

  const handleSelect = (ref) => {
    setSelectedRef(ref);
    setReply('');
    setSearchParams({ ref }, { replace: true });
  };

  const handleReply = async (e) => {
    e.preventDefault();
    if (!reply.trim() || !selectedRef) return;
    setSending(true);
    try {
      const res = await api.post(
        `/support/tickets/${encodeURIComponent(selectedRef)}/messages`,
        { body: reply.trim() }
      );
      setThread(res.data);
      setReply('');
      toast.success('Reply sent');
      fetchTickets();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not send reply');
    } finally {
      setSending(false);
    }
  };

  const ticket = thread?.ticket;
  const messages = thread?.messages || [];
  const canReply =
    ticket && ticket.status !== 'closed' && ticket.status !== 'resolved';

  return (
    <div className="support-dashboard-page">
      <PageHeader
        kicker="Support"
        title="My support tickets"
        subtitle="View and reply to your conversations with Zenith Support"
      />

      {loadingList ? (
        <div className="support-empty">Loading tickets…</div>
      ) : tickets.length === 0 ? (
        <div className="support-empty support-card">
          <p>You have no support tickets yet.</p>
          <Link to="/contact" className="support-btn" style={{ marginTop: '1rem' }}>
            Contact support
          </Link>
        </div>
      ) : (
        <div className="support-page-layout">
          <aside className="support-ticket-list" aria-label="Your tickets">
            {tickets.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`support-ticket-list-item ${selectedRef === t.reference_code ? 'active' : ''}`}
                onClick={() => handleSelect(t.reference_code)}
              >
                <div className="ref">{t.reference_code}</div>
                <div className="subject">{t.subject || t.category}</div>
                <div className="date">{formatDate(t.last_message_at)}</div>
                <span className={`support-status-pill support-status-pill--${t.status}`}>
                  {statusLabel(t.status)}
                </span>
              </button>
            ))}
          </aside>

          <section className="support-card admin-support-detail">
            {loadingThread && !thread ? (
              <div className="support-empty">Loading conversation…</div>
            ) : ticket ? (
              <>
                <div className="support-thread-header">
                  <div>
                    <span className="support-ref">{ticket.reference_code}</span>
                    <h2 style={{ margin: '0.35rem 0 0', fontSize: '1.1rem' }}>
                      {ticket.subject || ticket.category}
                    </h2>
                  </div>
                  <span className={`support-status-pill support-status-pill--${ticket.status}`}>
                    {statusLabel(ticket.status)}
                  </span>
                </div>

                <div className="support-messages" role="log" aria-live="polite">
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`support-bubble support-bubble--${msg.author_type}`}
                    >
                      <div className="support-bubble-meta">
                        {msg.author_name} · {formatDate(msg.created_at)}
                      </div>
                      <div style={{ whiteSpace: 'pre-wrap' }}>{msg.body}</div>
                    </div>
                  ))}
                </div>

                {canReply && (
                  <form className="support-form admin-support-reply" onSubmit={handleReply}>
                    <textarea
                      value={reply}
                      onChange={(e) => setReply(e.target.value)}
                      placeholder="Type your reply…"
                      required
                    />
                    <button type="submit" className="support-btn" disabled={sending || !reply.trim()}>
                      {sending ? 'Sending…' : 'Send reply'}
                    </button>
                  </form>
                )}
              </>
            ) : (
              <div className="support-empty">Select a ticket to view the thread</div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

export default SupportPage;
