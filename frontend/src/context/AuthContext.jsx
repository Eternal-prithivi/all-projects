import React, { createContext, useState, useContext, useEffect, useRef } from 'react';
import { getCurrentUser } from '../api'; // Import the API function

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
          console.error("❌ AuthContext: Failed to fetch user", error);
          // If token is invalid, log the user out
          setToken(null);
          setUser(null);
          localStorage.removeItem('authToken');
          sessionStorage.removeItem('cachedUser');
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
    setToken(newToken);
    localStorage.setItem('authToken', newToken);
  };

  const logout = () => {
    setToken(null);
    setUser(null); // Clear the user data on logout
    localStorage.removeItem('authToken');
    sessionStorage.removeItem('cachedUser');
  };

  const isAuthenticated = !!token;

  // Provide the user object and loading state to the rest of the app
  return (
    <AuthContext.Provider value={{ isAuthenticated, token, user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};