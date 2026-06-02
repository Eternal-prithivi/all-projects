import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { useAuth } from './AuthContext.jsx';
import { apiClient } from '../api';

const NotificationContext = createContext();

export const useNotificationCenter = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotificationCenter must be used within NotificationProvider');
  }
  return context;
};

export const mapServerItem = (item) => ({
  id: item.id,
  title: item.title,
  message: item.message,
  type: item.type || 'info',
  link: item.link,
  read: Boolean(item.read),
  timestamp: item.created_at ? new Date(item.created_at) : new Date(),
});

export const NotificationProvider = ({ children }) => {
  const { token } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchRecent = useCallback(async () => {
    if (!token) return { items: [], unread: 0 };
    const res = await apiClient.get('/notifications/recent', { params: { limit: 8 } });
    const items = (res.data.notifications || []).map(mapServerItem);
    setNotifications(items);
    setUnreadCount(res.data.unread_count ?? 0);
    return { items, unread: res.data.unread_count ?? 0 };
  }, [token]);

  const fetchNotifications = useCallback(
    async ({ limit = 15, skip = 0, read = 'all', type = 'all' } = {}) => {
      if (!token) {
        return { items: [], total: 0, unread_count: 0, has_more: false };
      }
      const res = await apiClient.get('/notifications', {
        params: { limit, skip, read, type },
      });
      return {
        items: (res.data.notifications || []).map(mapServerItem),
        total: res.data.total ?? 0,
        unread_count: res.data.unread_count ?? 0,
        has_more: !!res.data.has_more,
        limit: res.data.limit,
        skip: res.data.skip,
      };
    },
    [token]
  );

  const refreshFromServer = useCallback(async () => {
    await fetchRecent();
  }, [fetchRecent]);

  useEffect(() => {
    if (token) {
      fetchRecent().catch(() => {});
    } else {
      setNotifications([]);
      setUnreadCount(0);
    }
  }, [token, fetchRecent]);

  const addNotification = useCallback(
    async (notification) => {
      const local = {
        id: notification.id || `local-${Date.now()}`,
        timestamp: new Date(),
        read: false,
        ...notification,
      };

      setNotifications((prev) => [local, ...prev].slice(0, 8));
      setUnreadCount((prev) => prev + 1);

      if (token && notification.persist !== false) {
        try {
          const res = await apiClient.post('/notifications', {
            title: notification.title || 'Notification',
            message: notification.message || '',
            type: notification.type || 'info',
            link: notification.link,
          });
          const serverId = res.data.id;
          if (serverId) {
            setNotifications((prev) =>
              prev.map((n) => (n.id === local.id ? { ...n, id: serverId } : n))
            );
          }
          await fetchRecent();
        } catch {
          /* keep local copy */
        }
      }

      return local.id;
    },
    [token, fetchRecent]
  );

  const updateNotification = useCallback((id, updates) => {
    setNotifications((prev) =>
      prev.map((notif) => (notif.id === id ? { ...notif, ...updates } : notif))
    );
  }, []);

  const markAsRead = useCallback(
    async (id) => {
      setNotifications((prev) =>
        prev.map((notif) => {
          if (notif.id === id && !notif.read) {
            setUnreadCount((c) => Math.max(0, c - 1));
            return { ...notif, read: true };
          }
          return notif;
        })
      );
      if (token && id && !String(id).startsWith('local-')) {
        try {
          await apiClient.patch(`/notifications/${id}/read`);
        } catch {
          /* ignore */
        }
      }
    },
    [token]
  );

  const markAllAsRead = useCallback(async () => {
    setNotifications((prev) => prev.map((notif) => ({ ...notif, read: true })));
    setUnreadCount(0);
    if (token) {
      try {
        await apiClient.post('/notifications/mark-all-read');
      } catch {
        /* ignore */
      }
    }
  }, [token]);

  const deleteNotification = useCallback(
    async (id) => {
      setNotifications((prev) => {
        const notif = prev.find((n) => n.id === id);
        if (notif && !notif.read) {
          setUnreadCount((count) => Math.max(0, count - 1));
        }
        return prev.filter((n) => n.id !== id);
      });
      if (token && id && !String(id).startsWith('local-')) {
        try {
          await apiClient.delete(`/notifications/${id}`);
        } catch {
          /* ignore */
        }
      }
    },
    [token]
  );

  const clearAll = useCallback(async () => {
    setNotifications([]);
    setUnreadCount(0);
    if (token) {
      try {
        await apiClient.delete('/notifications');
      } catch {
        /* ignore */
      }
    }
  }, [token]);

  const value = {
    notifications,
    unreadCount,
    addNotification,
    updateNotification,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
    refreshFromServer,
    fetchRecent,
    fetchNotifications,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

export default NotificationContext;
