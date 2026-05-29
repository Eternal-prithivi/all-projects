// Syncs theme preference from MongoDB when user is authenticated.
import { useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { apiClient } from '../api';

const VALID_THEMES = new Set(['dark', 'light', 'auto']);

export default function ThemeSync() {
  const { isAuthenticated } = useAuth();
  const { setTheme } = useTheme();

  useEffect(() => {
    if (!isAuthenticated) return;

    let cancelled = false;

    (async () => {
      try {
        const response = await apiClient.get('/settings/');
        const serverTheme = response.data?.preferences?.theme;
        if (!cancelled && serverTheme && VALID_THEMES.has(serverTheme)) {
          setTheme(serverTheme);
        }
      } catch {
        // Keep localStorage theme on failure
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, setTheme]);

  return null;
}
