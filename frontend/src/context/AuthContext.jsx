import React, { createContext, useState, useContext, useEffect } from 'react';
import { getCurrentUser } from '../api'; // Import the API function

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('authToken'));
  const [user, setUser] = useState(null); // Add state for the user object
  const [loading, setLoading] = useState(true); // Track if we're still loading user data

  // This effect runs when the app loads or when the token changes
  useEffect(() => {
    const fetchUser = async () => {
      if (token) {
        console.log('🔐 AuthContext: Fetching user with token:', token.substring(0, 20) + '...');
        setLoading(true);
        try {
          const userData = await getCurrentUser(token);
          console.log('✅ AuthContext: User fetched successfully:', userData);
          setUser(userData); // Save the fetched user data
        } catch (error) {
          console.error("❌ AuthContext: Failed to fetch user", error);
          // If token is invalid, log the user out
          setToken(null);
          setUser(null);
          localStorage.removeItem('authToken');
        } finally {
          setLoading(false);
        }
      } else {
        console.log('⚠️ AuthContext: No token found, user will be null');
        setUser(null);
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