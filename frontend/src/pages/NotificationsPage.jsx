import React, { useCallback, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import PageHeader from '../components/ui/PageHeader.jsx';
import { usePageRefresh } from '../hooks/usePageRefresh.js';
import { useNotificationCenter } from '../context/NotificationContext.jsx';
import '../styles/notifications-page.css';

const READ_TABS = [
  { id: 'all', label: 'All' },
  { id: 'unread', label: 'Unread' },
];

const TYPE_CHIPS = [
  { id: 'all', label: 'All types' },
  { id: 'info', label: 'Info' },
  { id: 'success', label: 'Success' },
  { id: 'warning', label: 'Warning' },
  { id: 'error', label: 'Error' },
];

const formatTime = (ts) => {
  if (!ts) return '';
  const d = new Date(ts);
  const now = new Date();
  const diffDays = Math.floor((now - d) / 86400000);
  if (diffDays < 1) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  if (diffDays < 7) return d.toLocaleDateString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' });
  return d.toLocaleString();
};

export default function NotificationsPage() {
  const location = useLocation();
  const isAdminRoute = location.pathname.startsWith('/admin');

  const {
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
    fetchNotifications,
  } = useNotificationCenter();

  const [readTab, setReadTab] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [page, setPage] = useState(0);
  const [data, setData] = useState({ items: [], total: 0, unread_count: 0, has_more: false });
  const [loading, setLoading] = useState(true);
  const { runPageRefresh, pageRefreshing } = usePageRefresh();

  const limit = 15;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchNotifications({
        limit,
        skip: page * limit,
        read: readTab,
        type: typeFilter,
      });
      setData(result);
    } finally {
      setLoading(false);
    }
  }, [fetchNotifications, page, readTab, typeFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setPage(0);
  }, [readTab, typeFilter]);

  const totalPages = Math.max(1, Math.ceil(data.total / limit));

  return (
    <div className="notifications-page zenith-page-enter">
      <PageHeader
        kicker={isAdminRoute ? 'Admin' : 'Account'}
        title="Notifications"
        subtitle={
          data.unread_count > 0
            ? `${data.unread_count} unread · ${data.total} in this view`
            : `${data.total} notification${data.total !== 1 ? 's' : ''}`
        }
        actions={
          <div className="notifications-page__actions">
            {data.unread_count > 0 && (
              <button type="button" className="btn-secondary" onClick={markAllAsRead}>
                Mark all read
              </button>
            )}
            {data.total > 0 && (
              <button type="button" className="btn-secondary" onClick={clearAll}>
                Clear all
              </button>
            )}
          </div>
        }
        onRefresh={() =>
          runPageRefresh(load, {
            loadingMessage: 'Refreshing notifications…',
            successMessage: 'Notifications refreshed.',
            errorMessage: 'Failed to refresh notifications.',
          })
        }
        refreshing={pageRefreshing || loading}
      />

      <div className="notifications-page__tabs" role="tablist">
        {READ_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={readTab === tab.id}
            className={`notifications-page__tab ${readTab === tab.id ? 'active' : ''}`}
            onClick={() => setReadTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="notifications-page__filters">
        {TYPE_CHIPS.map((chip) => (
          <button
            key={chip.id}
            type="button"
            className={`notifications-page__chip ${typeFilter === chip.id ? 'active' : ''}`}
            onClick={() => setTypeFilter(chip.id)}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {loading && data.items.length === 0 ? (
        <p className="notifications-page__empty">Loading…</p>
      ) : data.items.length === 0 ? (
        <div className="notifications-page__empty-state">
          <p>No notifications match this filter.</p>
          <p className="notifications-page__empty-hint">Alerts from deployments, budgets, and security appear here.</p>
        </div>
      ) : (
        <ul className="notifications-page__list">
          {data.items.map((n) => (
            <li
              key={n.id}
              className={`notifications-page__item type-${n.type || 'info'} ${!n.read ? 'unread' : ''}`}
            >
              <div className="notifications-page__accent" aria-hidden />
              <div className="notifications-page__body">
                {n.title && <strong>{n.title}</strong>}
                <p>{n.message}</p>
                <time>{formatTime(n.timestamp)}</time>
                {n.link && (
                  <Link to={n.link} className="notifications-page__link" onClick={() => markAsRead(n.id)}>
                    View details
                  </Link>
                )}
              </div>
              <div className="notifications-page__item-actions">
                {!n.read && (
                  <button type="button" onClick={() => markAsRead(n.id)}>
                    Mark read
                  </button>
                )}
                <button type="button" onClick={() => deleteNotification(n.id)}>
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {data.total > limit && (
        <div className="notifications-page__pagination">
          <button
            type="button"
            className="btn-secondary"
            disabled={page === 0 || loading}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Previous
          </button>
          <span>Page {page + 1} of {totalPages}</span>
          <button
            type="button"
            className="btn-secondary"
            disabled={!data.has_more || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
