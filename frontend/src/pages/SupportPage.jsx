import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  FaTimes,
  FaQuestionCircle,
  FaDollarSign,
  FaWrench,
  FaUser,
  FaEllipsisH,
  FaPaperPlane,
} from 'react-icons/fa';
import api from '../api';
import PageHeader from '../components/ui/PageHeader.jsx';
import { usePageRefresh } from '../hooks/usePageRefresh.js';
import SupportThreadPanel from '../components/support/SupportThreadPanel.jsx';
import { useSupportThreadPoll } from '../hooks/useSupportThreadPoll.js';
import { useSupportThreadWs } from '../hooks/useSupportThreadWs.js';
import { formatDateTime, statusLabel } from '../utils/supportFormat.js';
import { PATHS } from '../data/productFacts.js';
import '../styles/support-tickets.css';

const MESSAGE_MAX = 8000;

const CATEGORIES = [
  { value: 'general', label: 'General', icon: FaQuestionCircle, hint: 'Platform questions' },
  { value: 'billing', label: 'Billing', icon: FaDollarSign, hint: 'Plans & payments' },
  { value: 'technical', label: 'Technical', icon: FaWrench, hint: 'Bugs & cloud issues' },
  { value: 'account', label: 'Account', icon: FaUser, hint: 'Login & profile' },
  { value: 'others', label: 'Others', icon: FaEllipsisH, hint: 'Anything else' },
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
  const messageRef = useRef(null);
  const { runPageRefresh, pageRefreshing } = usePageRefresh();

  const closeNewTicket = useCallback(() => {
    setShowNewTicket(false);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('new');
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  useEffect(() => {
    if (showNewTicket && messageRef.current) {
      messageRef.current.focus();
    }
  }, [showNewTicket]);

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
      closeNewTicket();
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
  const bodyLength = newTicket.body.length;
  const canSubmit = newTicket.body.trim().length > 0 && !creating;

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
              setSelectedRef('');
              setThread(null);
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
        <section className="support-new-ticket-panel zenith-page-enter" aria-labelledby="support-new-ticket-title">
          <form className="support-new-ticket-form" onSubmit={handleCreateTicket}>
            <header className="support-new-ticket-header">
              <div>
                <p className="support-new-ticket-kicker">New conversation</p>
                <h2 id="support-new-ticket-title" className="support-new-ticket-title">
                  Create a support ticket
                </h2>
                <p className="support-new-ticket-lead">
                  We typically reply within one business day. You&apos;ll get a reference code and can follow up here.
                </p>
              </div>
              <button
                type="button"
                className="support-new-ticket-close"
                onClick={closeNewTicket}
                aria-label="Close new ticket form"
              >
                <FaTimes aria-hidden />
              </button>
            </header>

            <fieldset className="support-new-ticket-fieldset">
              <legend className="support-new-ticket-legend">What do you need help with?</legend>
              <div className="support-category-grid" role="radiogroup" aria-label="Ticket category">
                {CATEGORIES.map(({ value, label, icon: Icon, hint }) => (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={newTicket.category === value}
                    className={`support-category-chip ${newTicket.category === value ? 'is-active' : ''}`}
                    onClick={() => setNewTicket((f) => ({ ...f, category: value }))}
                  >
                    <span className="support-category-chip__icon" aria-hidden>
                      <Icon />
                    </span>
                    <span className="support-category-chip__text">
                      <span className="support-category-chip__label">{label}</span>
                      <span className="support-category-chip__hint">{hint}</span>
                    </span>
                  </button>
                ))}
              </div>
            </fieldset>

            <div className="support-new-ticket-row">
              <div className="support-form-field support-form-field--grow">
                <label htmlFor="support-subject">Subject</label>
                <input
                  id="support-subject"
                  type="text"
                  className="support-field-input"
                  value={newTicket.subject}
                  onChange={(e) => setNewTicket((f) => ({ ...f, subject: e.target.value }))}
                  placeholder="e.g. Invoice question for March"
                  maxLength={120}
                  autoComplete="off"
                />
                <span className="support-field-hint">Optional — helps us route your ticket faster</span>
              </div>
            </div>

            <div className="support-form-field">
              <div className="support-form-field__label-row">
                <label htmlFor="support-body">Message</label>
                <span
                  className={`support-char-count ${bodyLength > MESSAGE_MAX * 0.9 ? 'is-warn' : ''}`}
                  aria-live="polite"
                >
                  {bodyLength.toLocaleString()} / {MESSAGE_MAX.toLocaleString()}
                </span>
              </div>
              <textarea
                id="support-body"
                ref={messageRef}
                className="support-field-textarea"
                rows={6}
                value={newTicket.body}
                onChange={(e) =>
                  setNewTicket((f) => ({
                    ...f,
                    body: e.target.value.slice(0, MESSAGE_MAX),
                  }))
                }
                placeholder="Describe what happened, what you expected, and any error messages you saw…"
                required
                maxLength={MESSAGE_MAX}
              />
            </div>

            <footer className="support-new-ticket-footer">
              <p className="support-new-ticket-footer-note">
                Billing questions? See{' '}
                <Link to="/help?topic=billing" className="support-inline-link">
                  billing help
                </Link>{' '}
                or check{' '}
                <Link to={PATHS.billing} className="support-inline-link">
                  your account billing
                </Link>
                .
              </p>
              <div className="support-new-ticket-actions">
                <button type="button" className="support-btn support-btn--ghost" onClick={closeNewTicket}>
                  Cancel
                </button>
                <button type="submit" className="support-btn support-btn--primary" disabled={!canSubmit}>
                  <FaPaperPlane aria-hidden />
                  {creating ? 'Submitting…' : 'Submit ticket'}
                </button>
              </div>
            </footer>
          </form>
        </section>
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
