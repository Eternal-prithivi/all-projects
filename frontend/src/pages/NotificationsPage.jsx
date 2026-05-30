import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/ui/PageHeader.jsx';
import { useNotificationCenter } from '../context/NotificationContext.jsx';
import '../styles/notifications-page.css';

export default function NotificationsPage() {
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
    refreshFromServer,
  } = useNotificationCenter();
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      await refreshFromServer?.();
    } finally {
      setLoading(false);
    }
  }, [refreshFromServer]);

  useEffect(() => {
    load();
  }, [load]);

  const formatTime = (ts) => {
    if (!ts) return '';
    const d = new Date(ts);
    return d.toLocaleString();
  };

  return (
    <div className="notifications-page zenith-page-enter">
      <PageHeader
        kicker="Account"
        title="Notifications"
        subtitle={`${unreadCount} unread`}
        actions={
          <div className="notifications-page__actions">
            {unreadCount > 0 && (
              <button type="button" className="btn-secondary" onClick={markAllAsRead}>
                Mark all read
              </button>
            )}
            {notifications.length > 0 && (
              <button type="button" className="btn-secondary" onClick={clearAll}>
                Clear all
              </button>
            )}
          </div>
        }
      />

      {loading ? (
        <p className="notifications-page__empty">Loading…</p>
      ) : notifications.length === 0 ? (
        <p className="notifications-page__empty">No notifications yet.</p>
      ) : (
        <ul className="notifications-page__list">
          {notifications.map((n) => (
            <li key={n.id} className={`notifications-page__item ${!n.read ? 'unread' : ''}`}>
              <div className="notifications-page__body">
                {n.title && <strong>{n.title}</strong>}
                <p>{n.message}</p>
                <time>{formatTime(n.timestamp)}</time>
                {n.link && (
                  <Link to={n.link} className="notifications-page__link">
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
    </div>
  );
}
