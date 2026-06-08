import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import { FaSearch } from 'react-icons/fa';
import api from '../../api';
import PageHeader from '../../components/ui/PageHeader.jsx';
import '../../styles/admin-pages.css';
import '../../styles/support-tickets.css';

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function statusLabel(status) {
  return (status || '').replace(/_/g, ' ');
}

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'open', label: 'Open' },
  { value: 'waiting_on_customer', label: 'Waiting on customer' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
];

function AdminSupportPage() {
  const [tickets, setTickets] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set('status', statusFilter);
      if (search.trim()) params.set('search', search.trim());
      params.set('limit', '50');
      const res = await api.get(`/admin/support/tickets?${params}`);
      setTickets(res.data.tickets || []);
      setTotal(res.data.total || 0);
    } catch {
      toast.error('Failed to load support inbox');
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  const fetchDetail = useCallback(async (ticketId) => {
    if (!ticketId) {
      setDetail(null);
      return;
    }
    try {
      const res = await api.get(`/admin/support/tickets/${ticketId}`);
      setDetail(res.data);
    } catch {
      toast.error('Failed to load ticket');
      setDetail(null);
    }
  }, []);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  useEffect(() => {
    fetchDetail(selectedId);
  }, [selectedId, fetchDetail]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchTickets();
  };

  const handleReply = async (e) => {
    e.preventDefault();
    if (!reply.trim() || !selectedId) return;
    setSending(true);
    try {
      const res = await api.post(`/admin/support/tickets/${selectedId}/messages`, {
        body: reply.trim(),
      });
      setDetail(res.data);
      setReply('');
      toast.success('Reply sent to customer');
      fetchTickets();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send reply');
    } finally {
      setSending(false);
    }
  };

  const handleStatusChange = async (newStatus) => {
    if (!selectedId) return;
    try {
      await api.patch(`/admin/support/tickets/${selectedId}`, { status: newStatus });
      toast.success(`Ticket marked ${statusLabel(newStatus)}`);
      fetchDetail(selectedId);
      fetchTickets();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update status');
    }
  };

  const ticket = detail?.ticket;
  const messages = detail?.messages || [];

  return (
    <div className="admin-support-page">
      <PageHeader
        className="zenith-page-header--row"
        kicker="Admin"
        title="Support inbox"
        subtitle={`${total} ticket${total === 1 ? '' : 's'}`}
      />

      <div className="admin-search-section">
        <form className="search-input-group" onSubmit={handleSearch}>
          <FaSearch />
          <input
            type="text"
            placeholder="Search ref, email, or name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="zenith-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value || 'all'} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <button type="submit" className="btn-primary">
            Search
          </button>
        </form>
      </div>

      <div className="support-page-layout">
        <div className="admin-card" style={{ padding: 0 }}>
          {loading ? (
            <div className="admin-loading" style={{ padding: '2rem' }}>
              Loading…
            </div>
          ) : tickets.length === 0 ? (
            <div className="support-empty">No tickets match your filters</div>
          ) : (
            <div className="card-body no-padding">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Reference</th>
                    <th>Requester</th>
                    <th>Status</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((t) => (
                    <tr
                      key={t.id}
                      onClick={() => setSelectedId(t.id)}
                      className={selectedId === t.id ? 'selected-row' : ''}
                      style={{ cursor: 'pointer' }}
                    >
                      <td>
                        <span className="support-ref">{t.reference_code}</span>
                      </td>
                      <td>
                        <div>{t.requester_name}</div>
                        <div style={{ fontSize: '0.8rem', opacity: 0.7 }}>{t.requester_email}</div>
                      </td>
                      <td>
                        <span className={`support-status-pill support-status-pill--${t.status}`}>
                          {statusLabel(t.status)}
                        </span>
                      </td>
                      <td>{formatDate(t.last_message_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <section className="support-card admin-support-detail">
          {!selectedId ? (
            <div className="support-empty">Select a ticket to view the thread</div>
          ) : !ticket ? (
            <div className="support-empty">Loading…</div>
          ) : (
            <>
              <div className="support-thread-header">
                <div>
                  <span className="support-ref">{ticket.reference_code}</span>
                  <h2 style={{ margin: '0.35rem 0 0', fontSize: '1.1rem' }}>
                    {ticket.subject || ticket.category}
                  </h2>
                  <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', opacity: 0.75 }}>
                    {ticket.requester_name} · {ticket.requester_email}
                  </p>
                </div>
                <div className="admin-support-actions">
                  <select
                    className="zenith-select"
                    value={ticket.status}
                    onChange={(e) => handleStatusChange(e.target.value)}
                    aria-label="Ticket status"
                  >
                    {STATUS_OPTIONS.filter((o) => o.value).map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="support-messages" role="log" aria-live="polite">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`support-bubble support-bubble--${msg.author_type}`}
                  >
                    <div className="support-bubble-meta">
                      {msg.author_name} ({msg.author_type}) · {formatDate(msg.created_at)}
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap' }}>{msg.body}</div>
                  </div>
                ))}
              </div>

              <form className="admin-support-reply" onSubmit={handleReply}>
                <textarea
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  placeholder="Type your reply to the customer…"
                  required
                />
                <button type="submit" className="support-btn" disabled={sending || !reply.trim()}>
                  {sending ? 'Sending…' : 'Send reply'}
                </button>
              </form>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

export default AdminSupportPage;
