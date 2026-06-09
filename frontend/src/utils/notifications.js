import React from 'react';
import { toast } from 'react-toastify';
import IndeterminateProgressBar from '../components/IndeterminateProgressBar.jsx';

/**
 * Notification system: loading toast (top-right) + notification center (bell).
 * Success/error/info appear only in the bell — loading toast is dismissed when done.
 */

let notificationCenterRef = null;

export const setNotificationCenter = (centerRef) => {
  notificationCenterRef = centerRef;
};

const dismissLoadingToast = (toastId) => {
  if (toastId != null) {
    toast.dismiss(toastId);
  }
};

/**
 * Show a loading notification and return an ID that can be used to update it
 */
export const showLoadingNotification = (message, options = {}) => {
  const {
    toastId: existingToastId = null,
    autoClose = false,
    title = null,
  } = options;

  const loadingToastId = toast.loading(
    React.createElement(
      'div',
      { className: 'toast-loading-content' },
      React.createElement('span', { className: 'toast-loading-message' }, message),
      React.createElement(IndeterminateProgressBar, { label: message })
    ),
    {
      toastId: existingToastId,
      autoClose,
      hideProgressBar: true,
      icon: false,
      position: 'top-right',
      theme: 'dark',
      className: 'toast-loading',
      bodyClassName: 'toast-loading-body',
      containerId: 'main-toast-container',
    }
  );

  if (notificationCenterRef) {
    notificationCenterRef.addNotification({
      id: loadingToastId,
      type: 'loading',
      title: title,
      message: message,
    });
  }

  return loadingToastId;
};

/**
 * Finalize a loading notification as success (bell only — dismiss loading toast)
 */
export const updateToSuccess = (toastId, message, options = {}) => {
  const { onClose = null, title = null } = options;

  dismissLoadingToast(toastId);

  if (notificationCenterRef) {
    notificationCenterRef.updateNotification(toastId, {
      type: 'success',
      title: title,
      message: message,
    });
  }

  if (onClose) onClose();
};

/**
 * Finalize a loading notification as error (bell only — dismiss loading toast)
 */
export const updateToError = (toastId, message, options = {}) => {
  const { onClose = null, title = null } = options;

  dismissLoadingToast(toastId);

  if (notificationCenterRef) {
    notificationCenterRef.updateNotification(toastId, {
      type: 'error',
      title: title,
      message: message,
    });
  }

  if (onClose) onClose();
};

/**
 * Finalize a loading notification as info (bell only — dismiss loading toast)
 */
export const updateToInfo = (toastId, message, options = {}) => {
  const { onClose = null, title = null } = options;

  dismissLoadingToast(toastId);

  if (notificationCenterRef) {
    notificationCenterRef.updateNotification(toastId, {
      type: 'info',
      title: title,
      message: message,
    });
  }

  if (onClose) onClose();
};

/**
 * Execute an async operation with loading toast + bell notification
 */
export const withLoadingNotification = async (asyncFn, options = {}) => {
  const {
    loadingMessage = 'Loading...',
    successMessage = 'Operation completed successfully',
    errorMessage = 'Operation failed',
    onSuccess = null,
    onError = null,
    getSuccessMessage = null,
    getErrorMessage = null,
    title = null,
  } = options;

  const toastId = showLoadingNotification(loadingMessage, { title });

  try {
    const result = await asyncFn();

    const finalSuccessMessage = getSuccessMessage
      ? getSuccessMessage(result)
      : successMessage;

    updateToSuccess(toastId, finalSuccessMessage, {
      title,
      onClose: onSuccess ? () => onSuccess(result) : null,
    });

    return result;
  } catch (error) {
    const finalErrorMessage = getErrorMessage
      ? getErrorMessage(error)
      : error?.response?.data?.detail || error?.message || errorMessage;

    updateToError(toastId, finalErrorMessage, {
      title,
      onClose: onError ? () => onError(error) : null,
    });

    throw error;
  }
};

/**
 * Quick notification helpers — notification center only (no toast banners)
 */
export const notifySuccess = (message, options = {}) => {
  if (notificationCenterRef) {
    notificationCenterRef.addNotification({
      type: 'success',
      title: options.title || null,
      message: message,
    });
  }
  return null;
};

export const notifyError = (message, options = {}) => {
  if (notificationCenterRef) {
    notificationCenterRef.addNotification({
      type: 'error',
      title: options.title || null,
      message: message,
    });
  }
  return null;
};

export const notifyInfo = (message, options = {}) => {
  if (notificationCenterRef) {
    notificationCenterRef.addNotification({
      type: 'info',
      title: options.title || null,
      message: message,
    });
  }
  return null;
};

export const notifyWarning = (message, options = {}) => {
  if (notificationCenterRef) {
    notificationCenterRef.addNotification({
      type: 'warning',
      title: options.title || null,
      message: message,
    });
  }
  return null;
};
