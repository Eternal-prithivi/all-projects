// =============================================================================
// CONTEXT: PreferencesContext.jsx  (184 lines)
// PURPOSE: User display preferences — currency, timezone, date format, language
//   - Loads from /api/settings on login (synced to MongoDB)
//   - Provides: currency, currencySymbol, timezone, dateFormat, language, setPreference()
//   - currencySymbol is derived from the currency code (USD→$, EUR→€, GBP→£, INR→₹)
// USED BY: DashboardPage.jsx (cost display), CostAnalysisPage.jsx, BillingPage.jsx
// DO NOT:
//   - Hardcode "$" in any page — always use PreferencesContext.currencySymbol
//   - Add theme to this context — theme lives in ThemeContext.jsx
//   - Rename exported fields — every consuming page destructures exact field names
// =============================================================================
import React, { createContext, useState, useContext, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from './AuthContext';
import { apiClient } from '../api';

const PreferencesContext = createContext(null);

const STORAGE_KEY = 'zenith-preferences';

const DEFAULT_PREFERENCES = {
  currency: 'USD',
  dateFormat: 'MM/DD/YYYY',
  timezone: 'UTC+5:30',
};

/** Currency symbol map */
const CURRENCY_SYMBOLS = {
  USD: '$',
  INR: '₹',
  EUR: '€',
  GBP: '£',
};

/** Date format options for Intl.DateTimeFormat */
const DATE_FORMAT_OPTIONS = {
  'MM/DD/YYYY': { month: '2-digit', day: '2-digit', year: 'numeric' },
  'DD/MM/YYYY': { day: '2-digit', month: '2-digit', year: 'numeric' },
  'YYYY-MM-DD': { year: 'numeric', month: '2-digit', day: '2-digit' },
};

/** Locale map for date formatting */
const DATE_FORMAT_LOCALE = {
  'MM/DD/YYYY': 'en-US',
  'DD/MM/YYYY': 'en-GB',
  'YYYY-MM-DD': 'sv-SE', // ISO format
};

export const PreferencesProvider = ({ children }) => {
  const { isAuthenticated } = useAuth();

  // Read from localStorage as initial default, then override from API
  const [preferences, setPreferencesState] = useState(() => {
    try {
      const cached = localStorage.getItem(STORAGE_KEY);
      return cached ? { ...DEFAULT_PREFERENCES, ...JSON.parse(cached) } : DEFAULT_PREFERENCES;
    } catch {
      return DEFAULT_PREFERENCES;
    }
  });

  const [isLoaded, setIsLoaded] = useState(false);

  // Fetch preferences from backend when authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoaded(true);
      return;
    }

    const fetchPreferences = async () => {
      try {
        const response = await apiClient.get('/settings/');
        const serverPrefs = response.data?.preferences;
        if (serverPrefs) {
          const merged = {
            currency: serverPrefs.currency || DEFAULT_PREFERENCES.currency,
            dateFormat: serverPrefs.date_format || serverPrefs.dateFormat || DEFAULT_PREFERENCES.dateFormat,
            timezone: serverPrefs.timezone || DEFAULT_PREFERENCES.timezone,
          };
          setPreferencesState(merged);
          try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
          } catch {
            // localStorage not available
          }
        }
      } catch {
        console.warn('PreferencesContext: Failed to fetch preferences, using cached/defaults');
      } finally {
        setIsLoaded(true);
      }
    };

    fetchPreferences();
  }, [isAuthenticated]);

  /**
   * Update preferences locally and persist to localStorage.
   * Call this from SettingsPage after successfully saving to backend.
   */
  const updatePreferences = useCallback((newPrefs) => {
    setPreferencesState((prev) => {
      const updated = { ...prev, ...newPrefs };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      } catch {
        // localStorage not available
      }
      return updated;
    });
  }, []);

  /**
   * Format a number as currency using the user's chosen currency.
   * @param {number} amount
   * @param {number} decimals - decimal places (default 2)
   * @returns {string} e.g. "$1,234.56" or "₹1,234.56"
   */
  const formatCurrency = useCallback((amount, decimals = 2) => {
    const symbol = CURRENCY_SYMBOLS[preferences.currency] || '$';
    const num = Number(amount);
    if (isNaN(num)) return `${symbol}0.00`;
    return `${symbol}${num.toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })}`;
  }, [preferences.currency]);

  /**
   * Format a date string or Date object using the user's chosen format.
   * @param {string|Date} date
   * @param {object} extraOptions - additional Intl.DateTimeFormat options
   * @returns {string}
   */
  const formatDate = useCallback((date, extraOptions = {}) => {
    try {
      const d = date instanceof Date ? date : new Date(date);
      if (isNaN(d.getTime())) return String(date);

      const locale = DATE_FORMAT_LOCALE[preferences.dateFormat] || 'en-US';
      const options = {
        ...DATE_FORMAT_OPTIONS[preferences.dateFormat],
        ...extraOptions,
      };

      return d.toLocaleDateString(locale, options);
    } catch {
      return String(date);
    }
  }, [preferences.dateFormat]);

  /**
   * Format a date for friendly display (e.g., "Saturday, May 24")
   */
  const formatDateFriendly = useCallback((date) => {
    try {
      const d = date instanceof Date ? date : new Date(date);
      if (isNaN(d.getTime())) return String(date);

      return d.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return String(date);
    }
  }, []);

  const value = useMemo(() => ({
    ...preferences,
    isLoaded,
    updatePreferences,
    formatCurrency,
    formatDate,
    formatDateFriendly,
    currencySymbol: CURRENCY_SYMBOLS[preferences.currency] || '$',
  }), [preferences, isLoaded, updatePreferences, formatCurrency, formatDate, formatDateFriendly]);

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
};

export const usePreferences = () => {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error('usePreferences must be used within a PreferencesProvider');
  }
  return context;
};

export default PreferencesContext;
