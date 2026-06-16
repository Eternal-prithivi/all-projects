// =============================================================================
// CONTEXT: AuthContext.jsx
// PURPOSE: Cookie-based auth state — httpOnly cookies on api.rajverse.me
// =============================================================================
import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { getCurrentUser, logoutUser } from '../api';
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
    sessionStorage.removeItem('refreshToken');
  }, []);

  const loadUser = useCallback(async ({ silent = false } = {}) => {
    if (!silent && !getCachedUser()) {
      setLoading(true);
    }
    try {
      const userData = await getCurrentUser();
      setUser(userData);
      sessionStorage.setItem('cachedUser', JSON.stringify(userData));
      return userData;
    } catch (error) {
      const status = error?.response?.status;
      if (status === 401) {
        setUser(null);
        sessionStorage.removeItem('cachedUser');
        if (!silent) {
          triggerSessionExpired({ redirect: false });
        }
      } else if (status === 403) {
        setUser(null);
        sessionStorage.removeItem('cachedUser');
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
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
    setSessionKey((k) => k + 1);
  };

  const refreshUser = async () => loadUser({ silent: true });

  const isAuthenticated = !!user;
  const token = user ? 'cookie' : null;

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, token, user, loading, login, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
