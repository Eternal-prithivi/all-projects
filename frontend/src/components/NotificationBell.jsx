import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useNotificationCenter } from '../context/NotificationContext';
import { storageLifecycleAction, securityVaultAction } from '../api';
import { useAuth } from '../context/AuthContext';
import IndeterminateProgressBar from './IndeterminateProgressBar.jsx';
import '../styles/notification-bell.css';

const formatTimestamp = (timestamp) => {
  const now = new Date();
  const notifTime = new Date(timestamp);
  const diffMs = now - notifTime;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return notifTime.toLocaleDateString();
};

const isToday = (timestamp) => {
  const d = new Date(timestamp);
  const now = new Date();
  return d.toDateString() === now.toDateString();
};

const getNotificationIcon = (type) => {
  switch (type) {
    case 'success':
      return (
        <svg className="notif-icon success" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
        </svg>
      );
    case 'error':
      return (
        <svg className="notif-icon error" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
        </svg>
      );
    case 'warning':
      return (
        <svg className="notif-icon warning" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      );
    case 'loading':
      return (
        <span className="notif-icon-loading" aria-hidden="true">
          <IndeterminateProgressBar variant="gold" />
        </span>
      );
    default:
      return (
        <svg className="notif-icon info" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
      );
  }
};

const NotificationBell = ({ viewAllPath = '/dashboard/notifications' }) => {
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
    fetchRecent,
  } = useNotificationCenter();
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();
  const { token } = useAuth();

  const lifecycleActionLabels = {
    keep_hot: 'Keep hot',
    snooze: 'Snooze 30d',
    approve: 'Move now',
    encrypt_now: 'Encrypt now',
    dismiss_encryption: 'Dismiss',
    archive: 'Archive',
    restore: 'Restore',
    snooze_stale: 'Snooze 30d',
    approve_delete: 'Delete',
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    const handleEscape = (event) => {
      if (event.key === 'Escape') setIsOpen(false);
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscape);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      fetchRecent().finally(() => setLoading(false));
    }
  }, [isOpen, fetchRecent]);

  const toggleDropdown = () => setIsOpen((open) => !open);

  const handleClearAll = async () => {
    await clearAll();
  };

  const handleItemClick = async (notification) => {
    const cat = notification.metadata?.category;
    if (cat === 'lifecycle_pending' || cat === 'security_encryption_pending' || cat === 'security_stale_pending') {
      return;
    }
    if (!notification.read) {
      await markAsRead(notification.id);
    }
    if (notification.link) {
      setIsOpen(false);
      navigate(notification.link);
    }
  };

  const handleLifecycleAction = async (notification, action) => {
    const filename = notification.metadata?.filename;
    if (!filename) return;
    setActionLoading(`${notification.id}-${action}`);
    try {
      await storageLifecycleAction(filename, action);
      await markAsRead(notification.id);
      await fetchRecent();
    } catch (err) {
      console.error('Lifecycle action failed', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSecurityAction = async (notification, action) => {
    const filename = notification.metadata?.filename;
    if (!filename || !token) return;
    setActionLoading(`${notification.id}-${action}`);
    try {
      if (action === 'dismiss_encryption') {
        await markAsRead(notification.id);
        await fetchRecent();
        return;
      }
      const result = await securityVaultAction(token, filename, action);
      await markAsRead(notification.id);
      await fetchRecent();
      if (action === 'encrypt_now' || result?.open_encryption) {
        setIsOpen(false);
        navigate('/dashboard/security');
      }
    } catch (err) {
      console.error('Security vault action failed', err);
    } finally {
      setActionLoading(null);
    }
  };

  const todayItems = notifications.filter((n) => isToday(n.timestamp));
  const earlierItems = notifications.filter((n) => !isToday(n.timestamp));

  const hasUrgentUnread = notifications.some(
    (n) => !n.read && (n.type === 'error' || n.type === 'warning')
  );
  const badgeLabel = unreadCount > 99 ? '99+' : String(unreadCount);

  const renderGroup = (label, items) => {
    if (items.length === 0) return null;
    return (
      <div className="notification-group">
        <div className="notification-group-label">{label}</div>
        {items.map((notification) => (
          <div
            key={notification.id}
            className={`notification-item type-${notification.type || 'info'} ${!notification.read ? 'unread' : ''}`}
            onClick={() => handleItemClick(notification)}
            onKeyDown={(e) => e.key === 'Enter' && handleItemClick(notification)}
            role="button"
            tabIndex={0}
          >
            <div className="notification-item-icon">
              {getNotificationIcon(notification.type)}
            </div>
            <div className="notification-item-content">
              {notification.title && (
                <div className="notification-item-title">{notification.title}</div>
              )}
              <div className="notification-item-message">{notification.message}</div>
              {notification.type === 'loading' && (
                <IndeterminateProgressBar
                  variant="gold"
                  className="notification-item-progress"
                  label={notification.message}
                />
              )}
              <div className="notification-item-timestamp">
                {formatTimestamp(notification.timestamp)}
              </div>
              {notification.metadata?.category === 'lifecycle_pending' &&
                Array.isArray(notification.metadata.actions) && (
                  <div className="notification-lifecycle-actions">
                    {notification.metadata.actions.map((action) => (
                      <button
                        key={action}
                        type="button"
                        className="notification-lifecycle-btn"
                        disabled={actionLoading === `${notification.id}-${action}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleLifecycleAction(notification, action);
                        }}
                      >
                        {lifecycleActionLabels[action] || action}
                      </button>
                    ))}
                  </div>
                )}
              {(notification.metadata?.category === 'security_encryption_pending' ||
                notification.metadata?.category === 'security_stale_pending') &&
                Array.isArray(notification.metadata.actions) && (
                  <div className="notification-lifecycle-actions">
                    {notification.metadata.actions.map((action) => (
                      <button
                        key={action}
                        type="button"
                        className="notification-lifecycle-btn"
                        disabled={actionLoading === `${notification.id}-${action}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSecurityAction(notification, action);
                        }}
                      >
                        {lifecycleActionLabels[action] || action}
                      </button>
                    ))}
                  </div>
                )}
            </div>
            <button
              type="button"
              className="notification-item-delete"
              onClick={(e) => {
                e.stopPropagation();
                deleteNotification(notification.id);
              }}
              title="Delete notification"
              aria-label="Delete notification"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
                <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z" />
                <path fillRule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="notification-bell-container" ref={dropdownRef}>
      <button
        type="button"
        className={[
          'notification-bell-button',
          unreadCount > 0 ? 'notification-bell-button--has-unread' : '',
          hasUrgentUnread ? 'notification-bell-button--urgent' : '',
        ]
          .filter(Boolean)
          .join(' ')}
        onClick={toggleDropdown}
        title={unreadCount > 0 ? `${unreadCount} unread notifications` : 'Notifications'}
        aria-label={unreadCount > 0 ? `Notifications, ${unreadCount} unread` : 'Notifications'}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <span className="notification-bell-icon" aria-hidden>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
          </svg>
        </span>
        {unreadCount > 0 && (
          <span
            className={[
              'notification-badge',
              hasUrgentUnread ? 'notification-badge--urgent' : '',
              unreadCount > 9 ? 'notification-badge--many' : 'notification-badge--single',
            ]
              .filter(Boolean)
              .join(' ')}
            aria-hidden
          >
            {badgeLabel}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="notification-dropdown" role="dialog" aria-label="Notifications">
          <div className="notification-dropdown-header">
            <div>
              <h3>Notifications</h3>
              {unreadCount > 0 && (
                <p className="notification-dropdown-subtitle">{unreadCount} unread</p>
              )}
            </div>
            <div className="notification-header-actions">
              {unreadCount > 0 && (
                <button type="button" onClick={markAllAsRead} className="mark-all-read-btn">
                  Mark all read
                </button>
              )}
            </div>
          </div>

          <div className="notification-list">
            {loading ? (
              <div className="notification-loading-panel" aria-busy="true">
                <p>Loading notifications…</p>
                <IndeterminateProgressBar variant="gold" label="Loading notifications" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="notification-empty">
                <span className="notification-empty-icon" aria-hidden="true">
                  <svg viewBox="0 0 20 20" fill="currentColor">
                    <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
                  </svg>
                </span>
                <p>You're all caught up</p>
              </div>
            ) : (
              <>
                {renderGroup('Today', todayItems)}
                {renderGroup('Earlier', earlierItems)}
              </>
            )}
          </div>

          <div
            className={[
              'notification-dropdown-footer',
              notifications.length > 0 ? 'notification-dropdown-footer--split' : '',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            {notifications.length > 0 && (
              <button
                type="button"
                className="notification-footer-btn notification-footer-btn--clear"
                onClick={handleClearAll}
              >
                Clear all
              </button>
            )}
            <Link
              to={viewAllPath}
              className="notification-footer-btn notification-footer-btn--view"
              onClick={() => setIsOpen(false)}
            >
              View all
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
