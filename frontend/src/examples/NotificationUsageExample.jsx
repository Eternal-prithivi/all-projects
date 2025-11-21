/**
 * Example: How to use Google Cloud-style notifications
 * 
 * This file demonstrates the different ways to use the notification system
 * similar to Google Cloud Console's notification panel.
 */

import React from 'react';
import { useNotifications } from '../hooks/useNotifications';
import apiClient from '../api'; // Your API client

const NotificationUsageExample = () => {
  const notifications = useNotifications();

  /**
   * Example 1: Simple usage with automatic loading/success/error
   * This is the easiest way - just wrap your async function
   */
  const handleSimpleRequest = async () => {
    await notifications.executeWithNotification(
      async () => {
        // Your API call
        const response = await apiClient.post('/api/some-endpoint', { data: 'value' });
        return response.data;
      },
      {
        loadingMessage: 'Requesting resource...',
        successMessage: 'Resource created successfully!',
        errorMessage: 'Failed to create resource',
      }
    );
  };

  /**
   * Example 2: With custom success/error message generation
   */
  const handleRequestWithCustomMessages = async () => {
    await notifications.executeWithNotification(
      async () => {
        const response = await apiClient.post('/api/vm/request', {
          workload_description: 'Web server',
        });
        return response.data;
      },
      {
        loadingMessage: 'Provisioning VM...',
        getSuccessMessage: (result) => `VM ${result.vm_name} assigned successfully!`,
        getErrorMessage: (error) => error?.response?.data?.detail || 'VM request failed',
      }
    );
  };

  /**
   * Example 3: Manual control (show loading, update later)
   * Useful when you need more control over when notifications update
   */
  const handleManualControl = async () => {
    const toastId = notifications.showLoading('Processing request...');

    try {
      // Do multiple operations
      const step1 = await apiClient.post('/api/step1');
      notifications.updateInfo(toastId, 'Step 1 complete. Processing step 2...');

      const step2 = await apiClient.post('/api/step2');
      notifications.updateInfo(toastId, 'Step 2 complete. Finalizing...');

      const step3 = await apiClient.post('/api/step3');
      notifications.updateSuccess(toastId, 'All steps completed successfully!');
    } catch (error) {
      notifications.updateError(toastId, error.message || 'Operation failed');
    }
  };

  /**
   * Example 4: Quick notifications (no loading state)
   * For simple feedback that doesn't need loading indication
   */
  const handleQuickNotification = () => {
    notifications.success('Operation completed!');
    // Or
    notifications.error('Something went wrong');
    // Or
    notifications.info('Information message');
    // Or
    notifications.warning('Warning message');
  };

  /**
   * Example 5: With callbacks
   */
  const handleWithCallbacks = async () => {
    await notifications.executeWithNotification(
      async () => {
        return await apiClient.get('/api/data');
      },
      {
        loadingMessage: 'Fetching data...',
        successMessage: 'Data loaded successfully',
        onSuccess: (data) => {
          console.log('Data received:', data);
          // Do something with the data
        },
        onError: (error) => {
          console.error('Error occurred:', error);
          // Handle error
        },
      }
    );
  };

  return (
    <div>
      <h2>Notification Usage Examples</h2>
      <button onClick={handleSimpleRequest}>Simple Request</button>
      <button onClick={handleRequestWithCustomMessages}>Custom Messages</button>
      <button onClick={handleManualControl}>Manual Control</button>
      <button onClick={handleQuickNotification}>Quick Notification</button>
      <button onClick={handleWithCallbacks}>With Callbacks</button>
    </div>
  );
};

export default NotificationUsageExample;

/**
 * HOW TO USE IN YOUR PAGES:
 * 
 * 1. Import the hook:
 *    import { useNotifications } from '../hooks/useNotifications';
 * 
 * 2. Get the notification functions:
 *    const notifications = useNotifications();
 * 
 * 3. Use in your handlers:
 *    const handleAction = async () => {
 *      await notifications.executeWithNotification(
 *        async () => {
 *          return await apiClient.post('/api/endpoint', data);
 *        },
 *        {
 *          loadingMessage: 'Processing...',
 *          successMessage: 'Done!',
 *          errorMessage: 'Failed!',
 *        }
 *      );
 *    };
 * 
 * That's it! The notification will automatically:
 * - Show a loading spinner when the request starts
 * - Update to success (green checkmark) when it completes
 * - Update to error (red X) if it fails
 */

