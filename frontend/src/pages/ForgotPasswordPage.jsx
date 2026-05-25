import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { requestPasswordReset } from '../api';
import { getValidationErrorMessage, validateForgotPasswordForm } from '../utils/formValidation.js';
import '../styles/auth.css';

function ForgotPasswordPage() {
  const [identifier, setIdentifier] = useState('');
  const [method, setMethod] = useState('email');
  const [message, setMessage] = useState('');
  const [hint, setHint] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  const validation = validateForgotPasswordForm({ identifier });
  const isSubmitDisabled = isLoading || !validation.isValid;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage('');
    setHint('');
    setError('');

    setFieldErrors(validation.errors);

    if (!validation.isValid) {
      setError(getValidationErrorMessage(validation.errors) || 'Please fix the highlighted field.');
      return;
    }

    setIsLoading(true);
    try {
      const data = await requestPasswordReset(identifier.trim(), method);
      if (data.hint) {
        setHint(data.hint);
        setMessage(data.sent ? data.message : '');
      } else {
        setMessage(data.message || 'If an account exists, you will receive instructions shortly.');
        setIdentifier('');
      }
    } catch (err) {
      setError(err.detail || 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-brand-panel">
        <Link to="/login" className="auth-back-link">← Back to sign in</Link>
        <div className="brand-content">
          <div className="brand-logo">Zenith</div>
          <h1 className="brand-tagline">
            Reset your <span>password.</span>
          </h1>
          <p className="brand-description">
            Enter your username, login email, or recovery email. Add recovery contacts under Profile before using forgot password.
          </p>
        </div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-form-wrapper">
          <div className="auth-form-header">
            <h2>Forgot password</h2>
            <p>Remember it? <Link to="/login">Sign in</Link></p>
          </div>

          <form onSubmit={handleSubmit} aria-label="Forgot password form">
            <div className="auth-method-toggle" role="group" aria-label="Reset method">
              <button
                type="button"
                className={method === 'email' ? 'active' : ''}
                onClick={() => setMethod('email')}
              >
                Email link
              </button>
              <button
                type="button"
                className={method === 'sms' ? 'active' : ''}
                onClick={() => setMethod('sms')}
              >
                SMS code
              </button>
            </div>

            <div className="auth-input-group">
              <label htmlFor="forgot-identifier">Email or username</label>
              <input
                type="text"
                id="forgot-identifier"
                placeholder="you@example.com"
                value={identifier}
                onChange={(e) => {
                  setIdentifier(e.target.value);
                  if (fieldErrors.identifier) {
                    setFieldErrors((current) => ({ ...current, identifier: '' }));
                  }
                }}
                required
                autoComplete="email"
                aria-invalid={Boolean(fieldErrors.identifier)}
                aria-describedby={fieldErrors.identifier ? 'forgot-identifier-error' : undefined}
              />
              {fieldErrors.identifier && (
                <p className="form-field-error" id="forgot-identifier-error" role="alert">
                  {fieldErrors.identifier}
                </p>
              )}
            </div>

            <p className="auth-hint">
              {method === 'email'
                ? 'Link goes to your recovery email if set in Profile; otherwise your login email.'
                : 'Code is sent to the mobile saved in Profile (primary, then alternate). Use +country code, e.g. +919876543210.'}
            </p>

            <button type="submit" className="auth-submit-btn" disabled={isSubmitDisabled}>
              {isLoading ? 'Sending…' : method === 'email' ? 'Send reset link' : 'Send SMS code'}
            </button>

            {message && <p className="auth-success" role="status">{message}</p>}
            {hint && <p className="auth-error" role="alert">{hint}</p>}
            {error && <p className="auth-error" role="alert">{error}</p>}
          </form>

          {method === 'sms' && message && (
            <p className="auth-footer-link">
              <Link to="/reset-password">Enter your code and new password →</Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default ForgotPasswordPage;
