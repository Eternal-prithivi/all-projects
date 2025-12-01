import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { loginUser } from '../api';
import { useAuth } from '../context/AuthContext.jsx';
import Footer from '../components/layout/Footer.jsx';
import '../styles/login.css';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Get the redirect path from location state, default to /dashboard
  const from = location.state?.from || '/dashboard';

  // If already logged in, redirect
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    try {
      const credentials = { username, password };
      const data = await loginUser(credentials);
      login(data.access_token);
      // After login, AuthContext will fetch user data
      // The useEffect above will handle the redirect once isAuthenticated is true
    } catch (err) {
      setError(err.detail || 'An error occurred during login.');
    }
  };

  return (
    <>
      <div className="login-page-container">
        <div className="login-form-container">
          <form onSubmit={handleSubmit} aria-label="Login form">
            <h2>Login</h2>
            <div className="input-group">
              <label htmlFor="login-username">Username</label>
              <input 
                type="text" 
                id="login-username" 
                value={username} 
                onChange={(e) => setUsername(e.target.value)} 
                required 
                aria-required="true"
                autoComplete="username"
                aria-describedby={error ? "login-error" : undefined}
              />
            </div>
            <div className="input-group">
              <label htmlFor="login-password">Password</label>
              <input 
                type="password" 
                id="login-password" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                required 
                aria-required="true"
                autoComplete="current-password"
                aria-describedby={error ? "login-error" : undefined}
              />
            </div>
            <button type="submit" className="login-button" aria-label="Submit login form">Log In</button>
            {error && <p className="error-message" id="login-error" role="alert">{error}</p>}
            <div className="navigation-link">
              <p>Not registered yet? <Link to="/register">Create an account</Link></p>
            </div>
          </form>
        </div>
      </div>
      <Footer />
    </>
  );
}

export default LoginPage;
