import React from 'react';
import { toast } from 'react-toastify';
import IndeterminateProgressBar from '../components/IndeterminateProgressBar.jsx';

/**
 * Notification system: visible top-right toasts + notification center (bell).
 * Loading operations show a progress toast, then a success/error banner when done.
 */

export const MAIN_TOAST_CONTAINER_ID = 'main-toast-container';
export const ADMIN_TOAST_CONTAINER_ID = 'admin-toast-container';

let notificationCenterRef = null;

export const setNotificationCenter = (centerRef) => {
  notificationCenterRef = centerRef;
};

const TOAST_DEFAULTS = {
  success: 'Success',
  error: 'Something went wrong',
  info: 'Notice',
  warning: 'Warning',
};

function resolveToastText(message, title, type) {
  if (typeof message === 'string' && message.trim()) return message.trim();
  if (typeof title === 'string' && title.trim()) return title.trim();
  return TOAST_DEFAULTS[type] || 'Notice';
}

function bellMessage(message, title, type) {
  if (typeof message === 'string') return message;
  return title || resolveToastText(message, title, type);
}

/**
 * Visible top-right toast banner. Omit containerId on public pages (App root ToastContainer).
 */
export function showBannerToast(type, message, options = {}) {
  const { title = null, containerId, autoClose = 4000 } = options;
  const text = resolveToastText(message, title, type);
  if (!text) return;

  const toastOptions = {
    autoClose,
    hideProgressBar: false,
  };
  if (containerId) {
    toastOptions.containerId = containerId;
  }
  toast[type](text, toastOptions);
}

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
    containerId = MAIN_TOAST_CONTAINER_ID,
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
      containerId,
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
 * Finalize a loading notification as success (bell + success banner)
 */
export const updateToSuccess = (toastId, message, options = {}) => {
  const {
    onClose = null,
    title = null,
    containerId = MAIN_TOAST_CONTAINER_ID,
    autoClose,
  } = options;

  dismissLoadingToast(toastId);

  const bellText = bellMessage(message, title, 'success');
  if (notificationCenterRef) {
    notificationCenterRef.updateNotification(toastId, {
      type: 'success',
      title: title,
      message: bellText,
    });
  }

  showBannerToast('success', message, { title, containerId, autoClose });

  if (onClose) onClose();
};

/**
 * Finalize a loading notification as error (bell + error banner)
 */
export const updateToError = (toastId, message, options = {}) => {
  const {
    onClose = null,
    title = null,
    containerId = MAIN_TOAST_CONTAINER_ID,
    autoClose,
  } = options;

  dismissLoadingToast(toastId);

  const bellText = bellMessage(message, title, 'error');
  if (notificationCenterRef) {
    notificationCenterRef.updateNotification(toastId, {
      type: 'error',
      title: title,
      message: bellText,
    });
  }

  showBannerToast('error', message, { title, containerId, autoClose });

  if (onClose) onClose();
};

/**
 * Finalize a loading notification as info (bell + info banner)
 */
export const updateToInfo = (toastId, message, options = {}) => {
  const {
    onClose = null,
    title = null,
    containerId = MAIN_TOAST_CONTAINER_ID,
    autoClose,
  } = options;

  dismissLoadingToast(toastId);

  const bellText = bellMessage(message, title, 'info');
  if (notificationCenterRef) {
    notificationCenterRef.updateNotification(toastId, {
      type: 'info',
      title: title,
      message: bellText,
    });
  }

  showBannerToast('info', message, { title, containerId, autoClose });

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
    containerId = MAIN_TOAST_CONTAINER_ID,
  } = options;

  const toastId = showLoadingNotification(loadingMessage, { title, containerId });

  try {
    const result = await asyncFn();

    const finalSuccessMessage = getSuccessMessage
      ? getSuccessMessage(result)
      : successMessage;

    updateToSuccess(toastId, finalSuccessMessage, {
      title,
      containerId,
      onClose: onSuccess ? () => onSuccess(result) : null,
    });

    return result;
  } catch (error) {
    const finalErrorMessage = getErrorMessage
      ? getErrorMessage(error)
      : error?.response?.data?.detail || error?.message || errorMessage;

    updateToError(toastId, finalErrorMessage, {
      title,
      containerId,
      onClose: onError ? () => onError(error) : null,
    });

    throw error;
  }
};

function notify(type, message, options = {}) {
  const {
    title = null,
    containerId = MAIN_TOAST_CONTAINER_ID,
    banner = true,
    autoClose,
  } = options;

  if (notificationCenterRef) {
    notificationCenterRef.addNotification({
      type,
      title,
      message: bellMessage(message, title, type),
    });
  }

  if (banner) {
    showBannerToast(type, message, { title, containerId, autoClose });
  }

  return null;
}

/** Quick helpers — bell + visible toast banner */
export const notifySuccess = (message, options = {}) => notify('success', message, options);
export const notifyError = (message, options = {}) => notify('error', message, options);
export const notifyInfo = (message, options = {}) => notify('info', message, options);
export const notifyWarning = (message, options = {}) => notify('warning', message, options);

/** Admin layout uses a separate toast container */
export const notifyAdminSuccess = (message, options = {}) =>
  notifySuccess(message, { ...options, containerId: ADMIN_TOAST_CONTAINER_ID });
export const notifyAdminError = (message, options = {}) =>
  notifyError(message, { ...options, containerId: ADMIN_TOAST_CONTAINER_ID });
export const notifyAdminInfo = (message, options = {}) =>
  notifyInfo(message, { ...options, containerId: ADMIN_TOAST_CONTAINER_ID });
