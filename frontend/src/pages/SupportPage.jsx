import React, { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import api from '../api';
import PageHeader from '../components/ui/PageHeader.jsx';
import SupportThreadPanel from '../components/support/SupportThreadPanel.jsx';
import { useSupportThreadPoll } from '../hooks/useSupportThreadPoll.js';
import { useSupportThreadWs } from '../hooks/useSupportThreadWs.js';
import { formatDateTime, statusLabel } from '../utils/supportFormat.js';
import '../styles/support-tickets.css';

function SupportPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tickets, setTickets] = useState([]);
  const [selectedRef, setSelectedRef] = useState(searchParams.get('ref') || '');
  const [thread, setThread] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);

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
    if (tickets.length > 0 && !selectedRef) {
      setSelectedRef(tickets[0].reference_code);
    }
  }, [searchParams, tickets, selectedRef]);

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

  const ticket = thread?.ticket;
  const messages = thread?.messages || [];

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
      )}
    </div>
  );
}

export default SupportPage;
