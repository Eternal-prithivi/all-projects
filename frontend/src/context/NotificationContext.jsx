// =============================================================================
// CONTEXT: NotificationContext.jsx  (95 lines)
// PURPOSE: Real-time notification state — WebSocket connection to /ws/status
//   - Provides: notifications[], addNotification(), markRead(), unreadCount
//   - WebSocket URL: ws://localhost:8000/ws/status?token={token} (dev)
//   - On "job_complete" message: refreshes relevant page data via context callbacks
// USED BY: NotificationBell.jsx (display), SecurityPage.jsx (file job completion)
// DO NOT:
//   - Open additional WebSocket connections in individual pages — use this context
//   - Store notifications in localStorage — they're session-only in-memory state
//   - Change the "job_complete" message format without updating SecurityPage.jsx ws handler
// =============================================================================
import React, { createContext, useContext, useState, useCallback } from 'react';

const NotificationContext = createContext();

export const useNotificationCenter = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotificationCenter must be used within NotificationProvider');
  }
  return context;
};

export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  // Add a new notification to the center
  const addNotification = useCallback((notification) => {
    const newNotification = {
      id: notification.id || Date.now() + Math.random(), // Use provided ID or generate one
      timestamp: new Date(),
      read: false,
      ...notification,
    };

    setNotifications(prev => [newNotification, ...prev]); // Newest first
    setUnreadCount(prev => prev + 1);

    return newNotification.id;
  }, []);

  // Update an existing notification
  const updateNotification = useCallback((id, updates) => {
    setNotifications(prev => 
      prev.map(notif => 
        notif.id === id ? { ...notif, ...updates } : notif
      )
    );
  }, []);

  // Mark notification as read
  const markAsRead = useCallback((id) => {
    setNotifications(prev => 
      prev.map(notif => 
        notif.id === id ? { ...notif, read: true } : notif
      )
    );
    setUnreadCount(prev => Math.max(0, prev - 1));
  }, []);

  // Mark all as read
  const markAllAsRead = useCallback(() => {
    setNotifications(prev => 
      prev.map(notif => ({ ...notif, read: true }))
    );
    setUnreadCount(0);
  }, []);

  // Delete a notification
  const deleteNotification = useCallback((id) => {
    setNotifications(prev => {
      const notif = prev.find(n => n.id === id);
      if (notif && !notif.read) {
        setUnreadCount(count => Math.max(0, count - 1));
      }
      return prev.filter(n => n.id !== id);
    });
  }, []);

  // Clear all notifications
  const clearAll = useCallback(() => {
    setNotifications([]);
    setUnreadCount(0);
  }, []);

  const value = {
    notifications,
    unreadCount,
    addNotification,
    updateNotification,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};

export default NotificationContext;

