import { useCallback, useEffect } from 'react';
import {
  showLoadingNotification,
  updateToSuccess,
  updateToError,
  updateToInfo,
  withLoadingNotification,
  notifySuccess,
  notifyError,
  notifyInfo,
  notifyWarning,
  setNotificationCenter,
} from '../utils/notifications';
import { useNotificationCenter } from '../context/NotificationContext';

/**
 * React hook for Google Cloud-style notifications
 * Provides easy access to notification functions
 */
export const useNotifications = () => {
  const notificationCenter = useNotificationCenter();

  // Set the notification center reference so utils can access it
  useEffect(() => {
    setNotificationCenter(notificationCenter);
  }, [notificationCenter]);
  /**
   * Execute an async function with automatic loading/success/error notifications
   */
  const executeWithNotification = useCallback(async (
    asyncFn,
    options = {}
  ) => {
    return withLoadingNotification(asyncFn, options);
  }, []);

  /**
   * Show a loading notification
   */
  const showLoading = useCallback((message, options) => {
    return showLoadingNotification(message, options);
  }, []);

  /**
   * Update notification to success
   */
  const updateSuccess = useCallback((toastId, message, options) => {
    updateToSuccess(toastId, message, options);
  }, []);

  /**
   * Update notification to error
   */
  const updateError = useCallback((toastId, message, options) => {
    updateToError(toastId, message, options);
  }, []);

  /**
   * Update notification to info
   */
  const updateInfo = useCallback((toastId, message, options) => {
    updateToInfo(toastId, message, options);
  }, []);

  return {
    // Main function for API calls
    executeWithNotification,
    
    // Loading notification controls
    showLoading,
    updateSuccess,
    updateError,
    updateInfo,
    
    // Quick notifications (no loading state)
    success: notifySuccess,
    error: notifyError,
    info: notifyInfo,
    warning: notifyWarning,
  };
};

