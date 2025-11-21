# Google Cloud-Style Notification System

This notification system provides Google Cloud Console-style notifications that show loading states and automatically update to success/error messages.

## Features

✅ **Loading Notifications** - Shows a spinner and "Loading..." message when operations start  
✅ **Auto-Updates** - Automatically changes to success (green) or error (red) when operations complete  
✅ **Progress Indicators** - Visual progress bars and animated borders  
✅ **Platform-Style Icons** - Circular icons with checkmarks, X marks, info, and warning symbols  
✅ **Easy to Use** - Simple hook-based API that wraps your async functions  

## Quick Start

### 1. Import the Hook

```jsx
import { useNotifications } from '../hooks/useNotifications';
```

### 2. Use in Your Component

```jsx
function MyComponent() {
  const notifications = useNotifications();

  const handleAction = async () => {
    await notifications.executeWithNotification(
      async () => {
        // Your API call here
        const response = await apiClient.post('/api/endpoint', data);
        return response.data;
      },
      {
        loadingMessage: 'Processing request...',
        successMessage: 'Operation completed successfully!',
        errorMessage: 'Operation failed',
      }
    );
  };

  return <button onClick={handleAction}>Do Something</button>;
}
```

## API Reference

### `useNotifications()` Hook

Returns an object with the following methods:

#### `executeWithNotification(asyncFn, options)`

Wraps an async function and automatically shows loading/success/error notifications.

**Parameters:**
- `asyncFn` - Async function to execute
- `options` - Configuration object:
  - `loadingMessage` (string) - Message to show while loading
  - `successMessage` (string) - Message to show on success
  - `errorMessage` (string) - Message to show on error
  - `getSuccessMessage` (function) - Generate success message from result: `(result) => string`
  - `getErrorMessage` (function) - Generate error message from error: `(error) => string`
  - `onSuccess` (function) - Callback when successful: `(result) => void`
  - `onError` (function) - Callback on error: `(error) => void`

**Returns:** Promise with the result of `asyncFn`

#### `showLoading(message, options)`

Show a loading notification manually.

**Returns:** Toast ID (for updating later)

#### `updateSuccess(toastId, message, options)`

Update a loading notification to success.

#### `updateError(toastId, message, options)`

Update a loading notification to error.

#### `updateInfo(toastId, message, options)`

Update a loading notification to info.

#### Quick Notification Methods

- `success(message, options)` - Show a success notification (no loading state)
- `error(message, options)` - Show an error notification (no loading state)
- `info(message, options)` - Show an info notification (no loading state)
- `warning(message, options)` - Show a warning notification (no loading state)

## Examples

### Example 1: Simple API Call

```jsx
const handleSubmit = async () => {
  await notifications.executeWithNotification(
    async () => {
      return await apiClient.post('/api/users', formData);
    },
    {
      loadingMessage: 'Creating user...',
      successMessage: 'User created successfully!',
      errorMessage: 'Failed to create user',
    }
  );
};
```

### Example 2: Custom Messages from Response

```jsx
const handleRequestVM = async () => {
  await notifications.executeWithNotification(
    async () => {
      return await apiClient.post('/api/vm/request', data);
    },
    {
      loadingMessage: 'Provisioning VM...',
      getSuccessMessage: (result) => `VM ${result.vm_name} assigned!`,
      getErrorMessage: (error) => error?.response?.data?.detail || 'VM request failed',
    }
  );
};
```

### Example 3: Manual Control (Multi-Step)

```jsx
const handleComplexOperation = async () => {
  const toastId = notifications.showLoading('Starting operation...');

  try {
    await apiClient.post('/api/step1');
    notifications.updateInfo(toastId, 'Step 1 complete. Processing step 2...');

    await apiClient.post('/api/step2');
    notifications.updateInfo(toastId, 'Step 2 complete. Finalizing...');

    await apiClient.post('/api/step3');
    notifications.updateSuccess(toastId, 'All steps completed!');
  } catch (error) {
    notifications.updateError(toastId, error.message);
  }
};
```

### Example 4: Quick Notifications (No Loading)

```jsx
const handleQuickAction = () => {
  notifications.success('Settings saved!');
  // or
  notifications.error('Something went wrong');
  // or
  notifications.info('Information message');
  // or
  notifications.warning('Warning message');
};
```

## Styling

The notifications use Google Cloud Console-inspired styling:

- **Loading**: Blue border with animated spinner
- **Success**: Green border with checkmark icon
- **Error**: Red border with X icon
- **Info**: Blue border with info icon
- **Warning**: Yellow border with warning icon

All styles are in `src/styles/toast-custom.css`.

## Global Setup

The `ToastContainer` is already set up in `DashboardLayout.jsx`. It will display notifications at the top-right of the screen.

## Migration Guide

To migrate existing code:

**Before:**
```jsx
const handleAction = async () => {
  setIsLoading(true);
  try {
    await apiClient.post('/api/endpoint');
    toast.success('Success!');
  } catch (error) {
    toast.error('Failed!');
  } finally {
    setIsLoading(false);
  }
};
```

**After:**
```jsx
const notifications = useNotifications();

const handleAction = async () => {
  await notifications.executeWithNotification(
    async () => await apiClient.post('/api/endpoint'),
    {
      loadingMessage: 'Processing...',
      successMessage: 'Success!',
      errorMessage: 'Failed!',
    }
  );
};
```

This removes the need for manual loading state management!

