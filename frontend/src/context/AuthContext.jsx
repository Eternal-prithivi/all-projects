// =============================================================================
// CONTEXT: AuthContext.jsx  (84 lines)
// PURPOSE: JWT auth state — the backbone of every protected page
//   - Provides: isAuthenticated, user, token, login(), logout()
//   - token: stored in localStorage (key: "token")
//   - login(token): saves token, fetches user from /api/users/me, sets state
//   - logout(): clears localStorage token, resets state, redirects to /login
// USED BY: Every dashboard page via: const { token, user } = useAuth()
//          ProtectedRoute.jsx uses isAuthenticated to guard routes
// DO NOT:
//   - Store token in sessionStorage or cookies — localStorage is intentional
//   - Add extra fields to AuthContext without updating every page that destructures it
//   - Call getCurrentUser() from pages directly — let AuthContext manage it
// =============================================================================
import React, { createContext, useState, useContext, useEffect, useRef } from 'react';
import { getCurrentUser } from '../api';
import { resetSessionExpiredGuard, triggerSessionExpired } from '../utils/sessionExpiry.js';

const AuthContext = createContext(null);

// Helper to read cached user from sessionStorage
const getCachedUser = () => {
  try {
    const cached = sessionStorage.getItem('cachedUser');
    return cached ? JSON.parse(cached) : null;
  } catch {
    return null;
  }
};

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('authToken'));
  const [user, setUser] = useState(getCachedUser); // Restore cached user immediately
  // Only show full loading spinner if we have NO cached user at all
  const [loading, setLoading] = useState(() => !!localStorage.getItem('authToken') && !getCachedUser());
  const fetchedRef = useRef(false);

  // This effect runs when the app loads or when the token changes
  useEffect(() => {
    // Reset the fetch guard when token changes
    fetchedRef.current = false;

    const fetchUser = async () => {
      if (token) {
        // If we already have a cached user, don't block the UI
        const hasCachedUser = !!getCachedUser();
        if (!hasCachedUser) {
          setLoading(true);
        }
        try {
          const userData = await getCurrentUser(token);
          setUser(userData);
          // Cache user data for instant navigation
          sessionStorage.setItem('cachedUser', JSON.stringify(userData));
        } catch (error) {
          const status = error?.response?.status;
          console.error("❌ AuthContext: Failed to fetch user", error);
          // Only clear session when the token is rejected — not on network blips
          if (status === 401) {
            setToken(null);
            setUser(null);
            triggerSessionExpired();
          } else if (status === 403) {
            setToken(null);
            setUser(null);
            localStorage.removeItem('authToken');
            sessionStorage.removeItem('cachedUser');
          }
        } finally {
          setLoading(false);
          fetchedRef.current = true;
        }
      } else {
        setUser(null);
        sessionStorage.removeItem('cachedUser');
        setLoading(false);
      }
    };

    fetchUser();
  }, [token]);

  const login = (newToken) => {
    resetSessionExpiredGuard();
    setToken(newToken);
    localStorage.setItem('authToken', newToken);
  };

  const logout = () => {
    setToken(null);
    setUser(null); // Clear the user data on logout
    localStorage.removeItem('authToken');
    sessionStorage.removeItem('cachedUser');
  };

  const refreshUser = async () => {
    if (!token) return null;
    try {
      const userData = await getCurrentUser(token);
      setUser(userData);
      sessionStorage.setItem('cachedUser', JSON.stringify(userData));
      return userData;
    } catch (error) {
      console.error('AuthContext: failed to refresh user', error);
      return null;
    }
  };

  const isAuthenticated = !!token;

  // Provide the user object and loading state to the rest of the app
  return (
    <AuthContext.Provider value={{ isAuthenticated, token, user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};