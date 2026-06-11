import React, { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import api from '../api';
import PageHeader from '../components/ui/PageHeader.jsx';
import { usePageRefresh } from '../hooks/usePageRefresh.js';
import SupportThreadPanel from '../components/support/SupportThreadPanel.jsx';
import { useSupportThreadPoll } from '../hooks/useSupportThreadPoll.js';
import { useSupportThreadWs } from '../hooks/useSupportThreadWs.js';
import { formatDateTime, statusLabel } from '../utils/supportFormat.js';
import '../styles/support-tickets.css';

const CATEGORIES = [
  { value: 'general', label: 'General' },
  { value: 'billing', label: 'Billing' },
  { value: 'technical', label: 'Technical' },
  { value: 'account', label: 'Account' },
];

function SupportPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tickets, setTickets] = useState([]);
  const [selectedRef, setSelectedRef] = useState(searchParams.get('ref') || '');
  const [thread, setThread] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);
  const [showNewTicket, setShowNewTicket] = useState(searchParams.get('new') === '1');
  const [newTicket, setNewTicket] = useState({ category: 'general', subject: '', body: '' });
  const [creating, setCreating] = useState(false);
  const { runPageRefresh, pageRefreshing } = usePageRefresh();

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

  const fetchThread = useCallback(async (ref, { silent = false } = {}) => {
    if (!ref) {
      setThread(null);
      return;
    }
    if (!silent) setLoadingThread(true);
    try {
      const res = await api.get(`/support/tickets/${encodeURIComponent(ref)}`);
      setThread(res.data);
    } catch {
      if (!silent) {
        toast.error('Could not load ticket thread');
        setThread(null);
      }
    } finally {
      if (!silent) setLoadingThread(false);
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
    if (tickets.length > 0 && !selectedRef && !showNewTicket) {
      setSelectedRef(tickets[0].reference_code);
    }
  }, [searchParams, tickets, selectedRef, showNewTicket]);

  useEffect(() => {
    if (selectedRef) fetchThread(selectedRef);
  }, [selectedRef, fetchThread]);

  const refreshThread = useCallback(() => {
    if (selectedRef) fetchThread(selectedRef, { silent: true });
  }, [selectedRef, fetchThread]);

  useSupportThreadPoll(refreshThread, { enabled: Boolean(selectedRef) });
  useSupportThreadWs(refreshThread, {
    referenceCode: selectedRef,
    events: ['support_reply'],
    enabled: Boolean(selectedRef),
  });

  const handleSelect = (ref) => {
    setShowNewTicket(false);
    setSelectedRef(ref);
    setSearchParams({ ref }, { replace: true });
  };

  const handleSend = async (body) => {
    const res = await api.post(
      `/support/tickets/${encodeURIComponent(selectedRef)}/messages`,
      { body }
    );
    setThread(res.data);
    fetchTickets();
  };

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    if (!newTicket.body.trim()) {
      toast.error('Please enter a message');
      return;
    }
    setCreating(true);
    try {
      const res = await api.post('/support/tickets', {
        category: newTicket.category,
        subject: newTicket.subject || newTicket.category,
        body: newTicket.body.trim(),
      });
      const ref = res.data?.ticket?.reference_code;
      setShowNewTicket(false);
      setNewTicket({ category: 'general', subject: '', body: '' });
      await fetchTickets();
      if (ref) {
        setSelectedRef(ref);
        setSearchParams({ ref }, { replace: true });
        setThread(res.data);
      }
      toast.success('Support ticket created');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not create ticket');
    } finally {
      setCreating(false);
    }
  };

  const ticket = thread?.ticket;
  const messages = thread?.messages || [];

  return (
    <div className="support-dashboard-page">
      <PageHeader
        kicker="Support"
        title="My support tickets"
        subtitle="View and reply to your conversations with Zenith Support"
        actions={
          <button
            type="button"
            className="support-btn"
            onClick={() => {
              setShowNewTicket(true);
              setSearchParams({ new: '1' }, { replace: true });
            }}
          >
            New ticket
          </button>
        }
        onRefresh={() =>
          runPageRefresh(
            async () => {
              await fetchTickets();
              if (selectedRef) {
                await fetchThread(selectedRef, { silent: true });
              }
            },
            {
              loadingMessage: 'Refreshing support tickets…',
              successMessage: 'Support page refreshed.',
              errorMessage: 'Failed to refresh support page.',
            }
          )
        }
        refreshing={pageRefreshing || loadingList}
      />

      {showNewTicket && (
        <form className="support-card support-new-ticket-form" onSubmit={handleCreateTicket}>
          <h3>Create a support ticket</h3>
          <label htmlFor="support-category">Category</label>
          <select
            id="support-category"
            value={newTicket.category}
            onChange={(e) => setNewTicket((f) => ({ ...f, category: e.target.value }))}
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          <label htmlFor="support-subject">Subject (optional)</label>
          <input
            id="support-subject"
            type="text"
            value={newTicket.subject}
            onChange={(e) => setNewTicket((f) => ({ ...f, subject: e.target.value }))}
            placeholder="Brief summary"
            maxLength={120}
          />
          <label htmlFor="support-body">Message</label>
          <textarea
            id="support-body"
            rows={5}
            value={newTicket.body}
            onChange={(e) => setNewTicket((f) => ({ ...f, body: e.target.value }))}
            placeholder="Describe your issue…"
            required
          />
          <div className="support-new-ticket-actions">
            <button type="button" className="support-btn support-btn--ghost" onClick={() => setShowNewTicket(false)}>
              Cancel
            </button>
            <button type="submit" className="support-btn" disabled={creating}>
              {creating ? 'Creating…' : 'Submit ticket'}
            </button>
          </div>
        </form>
      )}

      {loadingList ? (
        <div className="support-empty">Loading tickets…</div>
      ) : tickets.length === 0 && !showNewTicket ? (
        <div className="support-empty support-card">
          <p>You have no support tickets yet.</p>
          <button
            type="button"
            className="support-btn"
            style={{ marginTop: '1rem' }}
            onClick={() => setShowNewTicket(true)}
          >
            Create your first ticket
          </button>
        </div>
      ) : tickets.length > 0 ? (
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
                <div className="date">{formatDateTime(t.last_message_at)}</div>
                <span className={`support-status-pill support-status-pill--${t.status}`}>
                  {statusLabel(t.status)}
                </span>
              </button>
            ))}
          </aside>

          <section className="support-card support-card--chat">
            <SupportThreadPanel
              ticket={ticket}
              messages={messages}
              loading={loadingThread && !thread}
              onSend={ticket ? handleSend : null}
              emptyMessage="Select a ticket to view the thread"
            />
          </section>
        </div>
      ) : null}
    </div>
  );
}

export default SupportPage;
