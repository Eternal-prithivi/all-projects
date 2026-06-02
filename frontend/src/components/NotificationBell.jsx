import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useNotificationCenter } from '../context/NotificationContext';
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
    default:
      return (
        <svg className="notif-icon info" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
        </svg>
      );
  }
};

const NotificationBell = () => {
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    fetchRecent,
  } = useNotificationCenter();
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

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

  const handleItemClick = async (notification) => {
    if (!notification.read) {
      await markAsRead(notification.id);
    }
    if (notification.link) {
      setIsOpen(false);
      navigate(notification.link);
    }
  };

  const todayItems = notifications.filter((n) => isToday(n.timestamp));
  const earlierItems = notifications.filter((n) => !isToday(n.timestamp));

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
              <div className="notification-item-timestamp">
                {formatTimestamp(notification.timestamp)}
              </div>
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
        className="notification-bell-button"
        onClick={toggleDropdown}
        title="Notifications"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
          <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
        </svg>
        {unreadCount > 0 && (
          <span className="notification-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
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
              <div className="notification-empty">
                <p>Loading…</p>
              </div>
            ) : notifications.length === 0 ? (
              <div className="notification-empty">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="currentColor" opacity="0.3" aria-hidden>
                  <path d="M24 4C22.895 4 22 4.895 22 6V8.19C17.923 9.062 15 12.701 15 17V26.586L12.707 28.879C11.526 30.06 12.379 32 14.086 32H33.914C35.621 32 36.474 30.06 35.293 28.879L33 26.586V17C33 12.701 30.077 9.062 26 8.19V6C26 4.895 25.105 4 24 4ZM24 38C21.791 38 20 39.791 20 42H28C28 39.791 26.209 38 24 38Z" />
                </svg>
                <p>You're all caught up</p>
              </div>
            ) : (
              <>
                {renderGroup('Today', todayItems)}
                {renderGroup('Earlier', earlierItems)}
              </>
            )}
          </div>

          <div className="notification-dropdown-footer">
            <Link to="/dashboard/notifications" className="view-all-btn" onClick={() => setIsOpen(false)}>
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
