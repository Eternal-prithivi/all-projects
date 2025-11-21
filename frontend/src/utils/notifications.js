import { toast } from 'react-toastify';

/**
 * Google Cloud-style notification system
 * Shows loading notifications that update to success/error
 * Also stores notifications in the notification center (bell icon)
 */

// Global reference to notification center (will be set by useNotifications hook)
let notificationCenterRef = null;

export const setNotificationCenter = (centerRef) => {
  notificationCenterRef = centerRef;
};

/**
 * Show a loading notification and return an ID that can be used to update it
 * @param {string} message - Loading message
 * @param {object} options - Additional options
 * @returns {string|number} - Toast ID
 */
export const showLoadingNotification = (message, options = {}) => {
  const {
    toastId: existingToastId = null,
    autoClose = false,
    hideProgressBar = false,
    title = null,
  } = options;
  
  const loadingToastId = toast.loading(message, {
    toastId: existingToastId,
    autoClose,
    hideProgressBar,
    position: 'top-right',
    theme: 'dark',
    className: 'toast-loading',
    bodyClassName: 'toast-loading-body',
    containerId: 'main-toast-container',
  });
  
  // Also add loading notification to the notification center
  if (notificationCenterRef) {
    notificationCenterRef.addNotification({
      id: loadingToastId, // Use same ID so we can update it later
      type: 'loading',
      title: title,
      message: message,
    });
  }
  
  return loadingToastId;
};

/**
 * Update a loading notification to success
 * @param {string|number} toastId - Toast ID from showLoadingNotification
 * @param {string} message - Success message
 * @param {object} options - Additional options
 */
export const updateToSuccess = (toastId, message, options = {}) => {
  const {
    autoClose = 5000,
    onClose = null,
    title = null,
  } = options;

  toast.update(toastId, {
    render: message,
    type: 'success',
    isLoading: false,
    autoClose,
    hideProgressBar: false,
    containerId: 'main-toast-container',
    onClose,
  });

  // Update the notification in the bell (don't create new one)
  if (notificationCenterRef) {
    notificationCenterRef.updateNotification(toastId, {
      type: 'success',
      title: title,
      message: message,
    });
  }
};

/**
 * Update a loading notification to error
 * @param {string|number} toastId - Toast ID from showLoadingNotification
 * @param {string} message - Error message
 * @param {object} options - Additional options
 */
export const updateToError = (toastId, message, options = {}) => {
  const {
    autoClose = 7000, // Errors stay longer
    onClose = null,
    title = null,
  } = options;

  toast.update(toastId, {
    render: message,
    type: 'error',
    isLoading: false,
    autoClose,
    hideProgressBar: false,
    containerId: 'main-toast-container',
    onClose,
  });

  // Update the notification in the bell (don't create new one)
  if (notificationCenterRef) {
    notificationCenterRef.updateNotification(toastId, {
      type: 'error',
      title: title,
      message: message,
    });
  }
};

/**
 * Update a loading notification to info
 * @param {string|number} toastId - Toast ID from showLoadingNotification
 * @param {string} message - Info message
 * @param {object} options - Additional options
 */
export const updateToInfo = (toastId, message, options = {}) => {
  const {
    autoClose = 5000,
    onClose = null,
  } = options;

  toast.update(toastId, {
    render: message,
    type: 'info',
    isLoading: false,
    autoClose,
    hideProgressBar: false,
    onClose,
  });
};

/**
 * Wrapper function to execute an async operation with automatic loading notifications
 * @param {Function} asyncFn - Async function to execute
 * @param {object} options - Notification options
 * @returns {Promise} - Result of asyncFn
 */
export const withLoadingNotification = async (
  asyncFn,
  options = {}
) => {
  const {
    loadingMessage = 'Loading...',
    successMessage = 'Operation completed successfully',
    errorMessage = 'Operation failed',
    onSuccess = null,
    onError = null,
    getSuccessMessage = null, // Function to generate success message from result
    getErrorMessage = null, // Function to generate error message from error
  } = options;

  const toastId = showLoadingNotification(loadingMessage);

  try {
    const result = await asyncFn();
    
    const finalSuccessMessage = getSuccessMessage 
      ? getSuccessMessage(result) 
      : successMessage;

    updateToSuccess(toastId, finalSuccessMessage, {
      onClose: onSuccess ? () => onSuccess(result) : null,
    });

    return result;
  } catch (error) {
    const finalErrorMessage = getErrorMessage
      ? getErrorMessage(error)
      : error?.response?.data?.detail || error?.message || errorMessage;

    updateToError(toastId, finalErrorMessage, {
      onClose: onError ? () => onError(error) : null,
    });

    throw error;
  }
};

/**
 * Quick notification helpers (without loading states)
 */
export const notifySuccess = (message, options = {}) => {
  // Add to notification center
  if (notificationCenterRef) {
    notificationCenterRef.addNotification({
      type: 'success',
      title: options.title || null,
      message: message,
    });
  }
  
  return toast.success(message, {
    position: 'top-right',
    theme: 'dark',
    autoClose: options.autoClose || 5000,
    containerId: 'main-toast-container',
    ...options,
  });
};

export const notifyError = (message, options = {}) => {
  // Add to notification center
  if (notificationCenterRef) {
    notificationCenterRef.addNotification({
      type: 'error',
      title: options.title || null,
      message: message,
    });
  }
  
  return toast.error(message, {
    position: 'top-right',
    theme: 'dark',
    autoClose: options.autoClose || 7000,
    containerId: 'main-toast-container',
    ...options,
  });
};

export const notifyInfo = (message, options = {}) => {
  // Add to notification center
  if (notificationCenterRef) {
    notificationCenterRef.addNotification({
      type: 'info',
      title: options.title || null,
      message: message,
    });
  }
  
  return toast.info(message, {
    position: 'top-right',
    theme: 'dark',
    autoClose: options.autoClose || 5000,
    containerId: 'main-toast-container',
    ...options,
  });
};

export const notifyWarning = (message, options = {}) => {
  // Add to notification center
  if (notificationCenterRef) {
    notificationCenterRef.addNotification({
      type: 'warning',
      title: options.title || null,
      message: message,
    });
  }
  
  return toast.warning(message, {
    position: 'top-right',
    theme: 'dark',
    autoClose: options.autoClose || 6000,
    containerId: 'main-toast-container',
    ...options,
  });
};

