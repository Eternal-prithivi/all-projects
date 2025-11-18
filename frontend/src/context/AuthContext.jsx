import React, { createContext, useState, useContext, useEffect } from 'react';
import { getCurrentUser } from '../api'; // Import the API function

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('authToken'));
  const [user, setUser] = useState(null); // Add state for the user object

  // This effect runs when the app loads or when the token changes
  useEffect(() => {
    const fetchUser = async () => {
      if (token) {
        try {
          const userData = await getCurrentUser(token);
          setUser(userData); // Save the fetched user data
        } catch (error) {
          console.error("Failed to fetch user on load", error);
          // If token is invalid, log the user out
          logout();
        }
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

  // Provide the user object to the rest of the app
  return (
    <AuthContext.Provider value={{ isAuthenticated, token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};