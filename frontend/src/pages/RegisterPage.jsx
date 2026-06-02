import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { registerUser } from '../api';
import { getValidationErrorMessage, validateRegisterForm } from '../utils/formValidation.js';
import '../styles/auth.css';
import '../styles/auth-polish.css';
import ZenithLogo from '../components/brand/ZenithLogo.jsx';

function RegisterPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  const validation = validateRegisterForm({ username, email, password });
  const isSubmitDisabled = isLoading || !validation.isValid;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage('');
    setError('');

    setFieldErrors(validation.errors);

    if (!validation.isValid) {
      setError(getValidationErrorMessage(validation.errors) || 'Please fix the highlighted fields.');
      return;
    }

    setIsLoading(true);
    try {
      const userData = { username, email, password };
      const response = await registerUser(userData);
      const payload = response?.data?.data || response?.data || response;
      if (payload?.email_verification_required) {
        setMessage(response.message || 'Check your email to verify your account before signing in.');
        setTimeout(() => navigate('/verify-email'), 2000);
      } else {
        setMessage(response.message);
      }
    } catch (err) {
      setError(err.detail || 'An error occurred during registration.');
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
          <div className="brand-logo auth-brand-logo">
            <ZenithLogo size={56} />
            <span className="brand-logo-text">Zenith</span>
          </div>
          <h1 className="brand-tagline">
            Start optimizing <span>your cloud today.</span>
          </h1>
          <p className="brand-description">
            Create your free account and start managing resources across 
            AWS, GCP, and Azure — all from a single dashboard.
          </p>
          <div className="brand-features">
            <div className="brand-feature">
              <div className="feature-icon">🚀</div>
              <span className="feature-text">Get started in under 2 minutes</span>
            </div>
            <div className="brand-feature">
              <div className="feature-icon">💰</div>
              <span className="feature-text">Free tier — no credit card needed</span>
            </div>
            <div className="brand-feature">
              <div className="feature-icon">☁️</div>
              <span className="feature-text">Multi-cloud support included</span>
            </div>
          </div>

          <div className="brand-stats">
            <div className="brand-stat">
              <span className="stat-value">50k+</span>
              <span className="stat-label">Active Users</span>
            </div>
            <div className="brand-stat">
              <span className="stat-value">12M+</span>
              <span className="stat-label">Resources</span>
            </div>
            <div className="brand-stat">
              <span className="stat-value">3</span>
              <span className="stat-label">Cloud Providers</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right: Form Panel */}
      <div className="auth-form-panel">
        <div className="auth-form-wrapper">
          <div className="auth-form-header">
            <h2>Create your account</h2>
            <p>Already have an account? <Link to="/login">Sign in</Link></p>
          </div>

          <form onSubmit={handleSubmit} aria-label="Registration form">
            <div className="auth-input-group">
              <label htmlFor="reg-username">Username</label>
              <input
                type="text"
                id="reg-username"
                placeholder="Choose a username"
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
                aria-describedby={fieldErrors.username ? 'reg-username-error' : 'username-help'}
                minLength={3}
              />
              <small id="username-help" className="form-help">At least 3 characters</small>
              {fieldErrors.username && (
                <p className="form-field-error" id="reg-username-error" role="alert">
                  {fieldErrors.username}
                </p>
              )}
            </div>

            <div className="auth-input-group">
              <label htmlFor="reg-email">Email</label>
              <input
                type="email"
                id="reg-email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (fieldErrors.email) {
                    setFieldErrors((current) => ({ ...current, email: '' }));
                  }
                }}
                required
                aria-required="true"
                autoComplete="email"
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={fieldErrors.email ? 'reg-email-error' : 'email-help'}
              />
              <small id="email-help" className="form-help">We'll never share your email</small>
              {fieldErrors.email && (
                <p className="form-field-error" id="reg-email-error" role="alert">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            <div className="auth-input-group">
              <label htmlFor="reg-password">Password</label>
              <input
                type="password"
                id="reg-password"
                placeholder="Min. 8 characters"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (fieldErrors.password) {
                    setFieldErrors((current) => ({ ...current, password: '' }));
                  }
                }}
                required
                minLength="8"
                aria-required="true"
                autoComplete="new-password"
                aria-invalid={Boolean(fieldErrors.password)}
                aria-describedby={fieldErrors.password ? 'reg-password-error' : 'password-help'}
              />
              <small id="password-help" className="form-help">Minimum 8 characters</small>
              {fieldErrors.password && (
                <p className="form-field-error" id="reg-password-error" role="alert">
                  {fieldErrors.password}
                </p>
              )}
            </div>

            <button 
              type="submit" 
              className="auth-submit-btn" 
              disabled={isSubmitDisabled}
              aria-label="Submit registration form"
            >
              {isLoading ? 'Creating account...' : 'Create Account'}
            </button>

            {message && <p className="auth-success" role="status" aria-live="polite">{message}</p>}
            {error && <p className="auth-error" role="alert" aria-live="assertive">{error}</p>}
          </form>

          <div className="auth-footer-link">
            <p>By signing up, you agree to our <Link to="/legal/terms">Terms</Link> & <Link to="/legal/privacy">Privacy Policy</Link></p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;
