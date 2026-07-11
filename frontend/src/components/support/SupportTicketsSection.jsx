import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  FaTimes,
  FaQuestionCircle,
  FaDollarSign,
  FaWrench,
  FaUser,
  FaEllipsisH,
  FaPaperPlane,
  FaPlus,
} from 'react-icons/fa';
import api from '../../api';
import { useNotifications } from '../../hooks/useNotifications.js';
import SupportThreadPanel from './SupportThreadPanel.jsx';
import { useSupportThreadPoll } from '../../hooks/useSupportThreadPoll.js';
import { useSupportThreadWs } from '../../hooks/useSupportThreadWs.js';
import { formatDateTime, statusLabel } from '../../utils/supportFormat.js';
import { PATHS } from '../../data/productFacts.js';
import '../../styles/support-tickets.css';

const MESSAGE_MAX = 8000;

const CATEGORIES = [
  { value: 'general', label: 'General', icon: FaQuestionCircle, hint: 'Platform questions' },
  { value: 'billing', label: 'Billing', icon: FaDollarSign, hint: 'Plans & payments' },
  { value: 'technical', label: 'Technical', icon: FaWrench, hint: 'Bugs & cloud issues' },
  { value: 'account', label: 'Account', icon: FaUser, hint: 'Login & profile' },
  { value: 'others', label: 'Others', icon: FaEllipsisH, hint: 'Anything else' },
];

function mergeTicketSearchParams(prev, patch) {
  const next = new URLSearchParams(prev);
  next.set('tab', 'tickets');
  Object.entries(patch).forEach(([key, value]) => {
    if (value == null || value === '') next.delete(key);
    else next.set(key, value);
  });
  return next;
}

export default function SupportTicketsSection() {
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
  const notifications = useNotifications();

  const updateParams = useCallback(
    (patch) => {
      setSearchParams((prev) => mergeTicketSearchParams(prev, patch), { replace: true });
    },
    [setSearchParams]
  );

  const closeNewTicket = useCallback(() => {
    setShowNewTicket(false);
    updateParams({ new: null });
  }, [updateParams]);

  const openNewTicket = useCallback(() => {
    setShowNewTicket(true);
    setSelectedRef('');
    setThread(null);
    updateParams({ new: '1', ref: null });
  }, [updateParams]);

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
      notifications.error('Could not load support tickets');
    } finally {
      setLoadingList(false);
    }
  }, [notifications]);

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
        notifications.error('Could not load ticket thread');
        setThread(null);
      }
    } finally {
      if (!silent) setLoadingThread(false);
    }
  }, [notifications]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  useEffect(() => {
    const ref = searchParams.get('ref');
    const isNew = searchParams.get('new') === '1';
    setShowNewTicket(isNew);
    if (ref) {
      setSelectedRef(ref);
      return;
    }
    if (tickets.length > 0 && !selectedRef && !isNew) {
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
    setShowNewTicket(false);
    setSelectedRef(ref);
    updateParams({ ref, new: null });
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
      notifications.error('Please enter a message');
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
        updateParams({ ref, new: null });
        setThread(res.data);
      }
      notifications.success('Support ticket created');
    } catch (err) {
      notifications.error(err.response?.data?.detail || 'Could not create ticket');
    } finally {
      setCreating(false);
    }
  };

  const ticket = thread?.ticket;
  const messages = thread?.messages || [];
  const bodyLength = newTicket.body.length;
  const canSubmit = newTicket.body.trim().length > 0 && !creating;

  return (
    <div className="support-tickets-embedded">
      <div className="support-tickets-embedded__toolbar">
        <p className="support-tickets-embedded__lead">
          Open a ticket and track replies from Zenith Support in one place.
        </p>
        <button type="button" className="support-btn" onClick={openNewTicket}>
          <FaPlus aria-hidden />
          New ticket
        </button>
      </div>

      {showNewTicket && (
        <section className="support-new-ticket-panel zenith-page-enter" aria-labelledby="help-support-new-ticket-title">
          <form className="support-new-ticket-form" onSubmit={handleCreateTicket}>
            <header className="support-new-ticket-header">
              <div>
                <p className="support-new-ticket-kicker">New conversation</p>
                <h2 id="help-support-new-ticket-title" className="support-new-ticket-title">
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
                {CATEGORIES.map((category) => {
                  const { value, label, icon: CategoryIcon, hint } = category;
                  return (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={newTicket.category === value}
                      className={`support-category-chip ${newTicket.category === value ? 'is-active' : ''}`}
                      onClick={() => setNewTicket((f) => ({ ...f, category: value }))}
                    >
                      <span className="support-category-chip__icon" aria-hidden>
                        <CategoryIcon />
                      </span>
                      <span className="support-category-chip__text">
                        <span className="support-category-chip__label">{label}</span>
                        <span className="support-category-chip__hint">{hint}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </fieldset>

            <div className="support-new-ticket-row">
              <div className="support-form-field support-form-field--grow">
                <label htmlFor="help-support-subject">Subject</label>
                <input
                  id="help-support-subject"
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
                <label htmlFor="help-support-body">Message</label>
                <span
                  className={`support-char-count ${bodyLength > MESSAGE_MAX * 0.9 ? 'is-warn' : ''}`}
                  aria-live="polite"
                >
                  {bodyLength.toLocaleString()} / {MESSAGE_MAX.toLocaleString()}
                </span>
              </div>
              <textarea
                id="help-support-body"
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
          <button type="button" className="support-btn" style={{ marginTop: '1rem' }} onClick={openNewTicket}>
            Create your first ticket
          </button>
        </div>
      ) : tickets.length > 0 ? (
        <div className="support-page-layout support-page-layout--embedded">
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
