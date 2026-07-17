import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { registerUser, getApiErrorMessage } from '../api';
import { getValidationErrorMessage, validateRegisterForm } from '../utils/formValidation.js';
import TurnstileWidget from '../components/auth/TurnstileWidget.jsx';
import PasswordRequirementsPanel from '../components/auth/PasswordRequirementsPanel.jsx';
import { turnstileSiteKey } from '../config/turnstile.js';
import { useAuth } from '../context/AuthContext.jsx';
import '../styles/auth.css';
import '../styles/auth-polish.css';
import ZenithLogo from '../components/brand/ZenithLogo.jsx';

function RegisterPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [registrationComplete, setRegistrationComplete] = useState(false);
  const [captchaToken, setCaptchaToken] = useState('');
  const [turnstileResetKey, setTurnstileResetKey] = useState(0);

  // Ref to track redirect timeout so we can cancel on unmount
  const redirectTimerRef = useRef(null);

  const captchaRequired = Boolean(turnstileSiteKey());

  // Guard: redirect already-authenticated users to dashboard
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // Cleanup: cancel any pending redirect timer on unmount
  useEffect(() => {
    return () => {
      if (redirectTimerRef.current) {
        clearTimeout(redirectTimerRef.current);
        redirectTimerRef.current = null;
      }
    };
  }, []);

  const handleCaptchaToken = useCallback((token) => {
    setCaptchaToken(token || '');
  }, []);

  const handleCaptchaExpire = useCallback(() => {
    setCaptchaToken('');
  }, []);

  const resetCaptcha = useCallback(() => {
    setCaptchaToken('');
    setTurnstileResetKey((key) => key + 1);
  }, []);

  const validation = validateRegisterForm({ username, email, password, confirmPassword });
  const passwordHint = useMemo(() => {
    if (!password) return '';
    return validation.errors.password || '';
  }, [password, validation.errors.password]);
  const isSubmitDisabled =
    isLoading || !validation.isValid || (captchaRequired && !captchaToken) || registrationComplete;

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
      const userData = {
        username: username.trim(),
        email: email.trim(),
        password: password.trim(),
      };
      if (captchaToken) {
        userData.captcha_token = captchaToken;
      }
      const response = await registerUser(userData);
      const emailVerificationRequired = response?.data?.email_verification_required ?? false;

      // Mark registration as complete to disable the form
      setRegistrationComplete(true);

      if (emailVerificationRequired) {
        setMessage(response.message || 'Check your email to verify your account before signing in.');
        redirectTimerRef.current = setTimeout(() => {
          navigate('/verify-email', { replace: true });
        }, 2000);
      } else {
        setMessage(response.message || 'Account created! Redirecting to sign in…');
        redirectTimerRef.current = setTimeout(() => {
          navigate('/login', { replace: true, state: { registered: true, registeredUsername: username.trim() } });
        }, 2000);
      }
    } catch (err) {
      resetCaptcha();
      setError(getApiErrorMessage(err, 'An error occurred during registration. Please try again.'));
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
            <ZenithLogo variant="full" size={56} badge="Cloud" textLayout="inline" />
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
            <fieldset disabled={registrationComplete} style={{ border: 'none', padding: 0, margin: 0 }}>
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
                <div className="auth-password-wrapper">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    id="reg-password"
                    placeholder="Create a strong password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (fieldErrors.password) {
                        setFieldErrors((current) => ({ ...current, password: '' }));
                      }
                    }}
                    required
                    minLength={8}
                    aria-required="true"
                    autoComplete="new-password"
                    aria-invalid={Boolean(fieldErrors.password || passwordHint)}
                    aria-describedby="password-requirements"
                  />
                  <button
                    type="button"
                    className="auth-password-toggle"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    tabIndex={-1}
                  >
                    {showPassword ? '🙈' : '👁️'}
                  </button>
                </div>
                <PasswordRequirementsPanel password={password} id="password-requirements" />
                {(fieldErrors.password || passwordHint) && (
                  <p className="form-field-error" id="reg-password-error" role="alert">
                    {fieldErrors.password || passwordHint}
                  </p>
                )}
              </div>

              <div className="auth-input-group">
                <label htmlFor="reg-confirm-password">Confirm Password</label>
                <div className="auth-password-wrapper">
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    id="reg-confirm-password"
                    placeholder="Re-enter your password"
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (fieldErrors.confirmPassword) {
                        setFieldErrors((current) => ({ ...current, confirmPassword: '' }));
                      }
                    }}
                    required
                    minLength={8}
                    aria-required="true"
                    autoComplete="new-password"
                    aria-invalid={Boolean(fieldErrors.confirmPassword)}
                    aria-describedby={fieldErrors.confirmPassword ? 'reg-confirm-password-error' : undefined}
                  />
                  <button
                    type="button"
                    className="auth-password-toggle"
                    onClick={() => setShowConfirmPassword((v) => !v)}
                    aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? '🙈' : '👁️'}
                  </button>
                </div>
                {fieldErrors.confirmPassword && (
                  <p className="form-field-error" id="reg-confirm-password-error" role="alert">
                    {fieldErrors.confirmPassword}
                  </p>
                )}
              </div>

              <TurnstileWidget
                onToken={handleCaptchaToken}
                onExpire={handleCaptchaExpire}
                resetKey={turnstileResetKey}
              />

              <button 
                type="submit" 
                className="auth-submit-btn" 
                disabled={isSubmitDisabled}
                aria-label="Submit registration form"
              >
                {isLoading ? 'Creating account...' : registrationComplete ? 'Account Created ✓' : 'Create Account'}
              </button>
            </fieldset>

            {!isLoading && password && !validation.isValid && validation.errors.password && (
              <p className="auth-password-hint-blocked" role="status">
                Complete all password requirements above to create your account.
              </p>
            )}

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
