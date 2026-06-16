// =============================================================================
// CONTEXT: AuthContext.jsx
// PURPOSE: Cookie-based auth state — httpOnly cookies on api.rajverse.me
// =============================================================================
import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { logoutUser, restoreSession } from '../api';
import { clearAuthTokens, getStoredAccessToken, shouldProbeSessionOnLoad } from '../utils/authTokens.js';
import { resetSessionExpiredGuard, triggerSessionExpired } from '../utils/sessionExpiry.js';

const AuthContext = createContext(null);

const getCachedUser = () => {
  try {
    const cached = sessionStorage.getItem('cachedUser');
    return cached ? JSON.parse(cached) : null;
  } catch {
    return null;
  }
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(getCachedUser);
  const [loading, setLoading] = useState(true);
  const [sessionKey, setSessionKey] = useState(0);

  useEffect(() => {
    localStorage.removeItem('authToken');
  }, []);

  const loadUser = useCallback(async ({ silent = false } = {}) => {
    if (!silent && !getCachedUser()) {
      setLoading(true);
    }
    try {
      const hadCachedUser = Boolean(getCachedUser());
      const userData = await restoreSession();
      if (!userData) {
        setUser(null);
        if (!silent && hadCachedUser) {
          triggerSessionExpired({ redirect: false });
        }
        return null;
      }
      setUser(userData);
      sessionStorage.setItem('cachedUser', JSON.stringify(userData));
      return userData;
    } catch (error) {
      const status = error?.response?.status;
      if (status === 403) {
        setUser(null);
        sessionStorage.removeItem('cachedUser');
        clearAuthTokens();
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!shouldProbeSessionOnLoad()) {
      setLoading(false);
      return;
    }
    loadUser({ silent: !!getCachedUser() });
  }, [loadUser, sessionKey]);

  const login = async () => {
    resetSessionExpiredGuard();
    setSessionKey((k) => k + 1);
    return loadUser();
  };

  const logout = async () => {
    try {
      await logoutUser();
    } catch {
      // Clear local state even if API call fails
    }
    setUser(null);
    sessionStorage.removeItem('cachedUser');
    clearAuthTokens();
    setSessionKey((k) => k + 1);
  };

  const refreshUser = async () => loadUser({ silent: true });

  const isAuthenticated = !!user;
  const token = user ? (getStoredAccessToken() || 'cookie') : null;

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, token, user, loading, login, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
