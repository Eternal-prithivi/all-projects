import { useCallback, useState } from 'react';
import { useNotifications } from './useNotifications';

/**
 * Standard page-level refresh with loading progress toast.
 */
export function usePageRefresh() {
  const { showLoading, updateSuccess, updateError } = useNotifications();
  const [refreshing, setRefreshing] = useState(false);

  const runPageRefresh = useCallback(
    async (
      fn,
      {
        loadingMessage = 'Refreshing page…',
        successMessage = 'Page refreshed.',
        getErrorMessage,
        errorMessage = 'Refresh failed.',
      } = {}
    ) => {
      setRefreshing(true);
      const toastId = showLoading(loadingMessage);
      try {
        await fn();
        updateSuccess(toastId, successMessage);
      } catch (error) {
        const msg = getErrorMessage
          ? getErrorMessage(error)
          : error?.message || error?.detail || errorMessage;
        updateError(toastId, typeof msg === 'string' ? msg : errorMessage);
        throw error;
      } finally {
        setRefreshing(false);
      }
    },
    [showLoading, updateSuccess, updateError]
  );

  return { runPageRefresh, pageRefreshing: refreshing };
}
