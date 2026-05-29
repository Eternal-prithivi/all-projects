import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { loginUser, getApiErrorMessage } from '../api';
import { useAuth } from '../context/AuthContext.jsx';
import { getValidationErrorMessage, validateLoginForm } from '../utils/formValidation.js';
import { getDeviceFingerprint } from '../utils/deviceFingerprint.js';
import '../styles/auth.css';
import '../styles/auth-polish.css';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [ssoProviders, setSsoProviders] = useState([]);
  const { login, isAuthenticated } = useAuth();

  const apiRoot = useMemo(
    () =>
      import.meta.env.MODE === 'production'
        ? 'https://zenith-backend-707i.onrender.com'
        : 'http://localhost:8000',
    []
  );
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

  useEffect(() => {
    fetch(`${apiRoot}/api/auth/sso/providers`)
      .then((r) => r.json())
      .then((data) => setSsoProviders(data.providers || []))
      .catch(() => setSsoProviders([]));
  }, [apiRoot]);

  const startSso = (providerId) => {
    window.location.href = `${apiRoot}/api/auth/sso/${providerId}/login`;
  };

  const validation = validateLoginForm({ username, password });
  const isSubmitDisabled = isLoading || !validation.isValid;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setFieldErrors(validation.errors);

    if (!validation.isValid) {
      setError(getValidationErrorMessage(validation.errors) || 'Please fix the highlighted fields.');
      return;
    }

    setIsLoading(true);
    try {
      const credentials = { username: username.trim(), password };
      let fingerprint = null;
      try {
        fingerprint = await getDeviceFingerprint();
      } catch {
        fingerprint = null;
      }
      const data = await loginUser(credentials, fingerprint);
      login(data.access_token);
      // After login, AuthContext will fetch user data
      // The useEffect above will handle the redirect once isAuthenticated is true
    } catch (err) {
      setError(getApiErrorMessage(err, 'An error occurred during login.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      {/* Left: Brand Panel */}
      <div className="auth-brand-panel">
        <Link to="/" className="auth-back-link">← Back to home</Link>
        <div className="brand-content">
          <div className="brand-logo">Zenith</div>
          <h1 className="brand-tagline">
            Welcome back to <span>your cloud.</span>
          </h1>
          <p className="brand-description">
            Sign in to manage your multi-cloud infrastructure, monitor costs, 
            and optimize resources across AWS, GCP, and Azure.
          </p>
          <div className="brand-features">
            <div className="brand-feature">
              <div className="feature-icon">📊</div>
              <span className="feature-text">Real-time cost analytics</span>
            </div>
            <div className="brand-feature">
              <div className="feature-icon">🔒</div>
              <span className="feature-text">Enterprise-grade security</span>
            </div>
            <div className="brand-feature">
              <div className="feature-icon">⚡</div>
              <span className="feature-text">AI-powered optimization</span>
            </div>
          </div>

          <div className="brand-stats">
            <div className="brand-stat">
              <span className="stat-value">$2M+</span>
              <span className="stat-label">Cloud Savings</span>
            </div>
            <div className="brand-stat">
              <span className="stat-value">99.9%</span>
              <span className="stat-label">Uptime</span>
            </div>
            <div className="brand-stat">
              <span className="stat-value">24/7</span>
              <span className="stat-label">Monitoring</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right: Form Panel */}
      <div className="auth-form-panel">
        <div className="auth-form-wrapper">
          <div className="auth-form-header">
            <h2>Sign in</h2>
            <p>Don't have an account? <Link to="/register">Create one free</Link></p>
          </div>

          <form onSubmit={handleSubmit} aria-label="Login form">
            <div className="auth-input-group">
              <label htmlFor="login-username">Username</label>
              <input
                type="text"
                id="login-username"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  if (fieldErrors.username) {
                    setFieldErrors((current) => ({ ...current, username: '' }));
                  }
                }}
                required
                aria-required="true"
                autoComplete="username"
                aria-invalid={Boolean(fieldErrors.username)}
                aria-describedby={fieldErrors.username ? 'login-username-error' : error ? 'login-error' : undefined}
              />
              {fieldErrors.username && (
                <p className="form-field-error" id="login-username-error" role="alert">
                  {fieldErrors.username}
                </p>
              )}
            </div>

            <div className="auth-input-group">
              <div className="auth-label-row">
                <label htmlFor="login-password">Password</label>
                <Link to="/forgot-password" className="auth-forgot-link">
                  Forgot password?
                </Link>
              </div>
              <input
                type="password"
                id="login-password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (fieldErrors.password) {
                    setFieldErrors((current) => ({ ...current, password: '' }));
                  }
                }}
                required
                aria-required="true"
                autoComplete="current-password"
                aria-invalid={Boolean(fieldErrors.password)}
                aria-describedby={fieldErrors.password ? 'login-password-error' : error ? 'login-error' : undefined}
              />
              {fieldErrors.password && (
                <p className="form-field-error" id="login-password-error" role="alert">
                  {fieldErrors.password}
                </p>
              )}
            </div>

            <button 
              type="submit" 
              className="auth-submit-btn" 
              disabled={isSubmitDisabled}
              aria-label="Submit login form"
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>

            {error && <p className="auth-error" id="login-error" role="alert">{error}</p>}
          </form>

          {ssoProviders.length > 0 && (
            <div className="auth-sso">
              <p className="auth-sso__divider">or continue with</p>
              <div className="auth-sso__buttons">
                {ssoProviders.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className="auth-sso__btn"
                    onClick={() => startSso(p.id)}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="auth-footer-link">
            <p>Protected by enterprise-grade encryption</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
