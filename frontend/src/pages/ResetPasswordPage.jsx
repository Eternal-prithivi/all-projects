import React, { useState, useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { resetPasswordWithToken } from '../api';
import { getValidationErrorMessage, validateResetPasswordForm } from '../utils/formValidation.js';
import PasswordRequirementsPanel from '../components/auth/PasswordRequirementsPanel.jsx';
import '../styles/auth.css';
import '../styles/auth-polish.css';
import ZenithLogo from '../components/brand/ZenithLogo.jsx';

function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const tokenFromUrl = searchParams.get('token');

  const [method, setMethod] = useState(tokenFromUrl ? 'email' : 'sms');
  const [identifier, setIdentifier] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);

  const isEmailFlow = useMemo(() => Boolean(tokenFromUrl) || method === 'email', [tokenFromUrl, method]);
  const validation = useMemo(() => validateResetPasswordForm({
    token: tokenFromUrl,
    identifier,
    otp,
    newPassword,
    confirmPassword,
    isEmailFlow,
  }), [tokenFromUrl, identifier, otp, newPassword, confirmPassword, isEmailFlow]);
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
      await resetPasswordWithToken({
        newPassword,
        method: isEmailFlow ? 'email' : 'sms',
        token: tokenFromUrl,
        otp: isEmailFlow ? null : otp.trim(),
        identifier: isEmailFlow ? null : identifier.trim(),
      });
      setMessage('Password updated! Redirecting to sign in…');
      setTimeout(() => navigate('/login', { replace: true }), 2000);
    } catch (err) {
      setError(err.detail || 'Could not reset password. The link or code may have expired.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-brand-panel">
        <Link to="/login" className="auth-back-link">← Back to sign in</Link>
        <div className="brand-content">
          <div className="brand-logo auth-brand-logo">
            <ZenithLogo variant="full" size={56} badge="Cloud" textLayout="inline" />
          </div>
          <h1 className="brand-tagline">
            Choose a new <span>password.</span>
          </h1>
        </div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-form-wrapper">
          <div className="auth-form-header">
            <h2>Set new password</h2>
            <p>
              <Link to="/forgot-password">Request a new link or code</Link>
            </p>
          </div>

          <form onSubmit={handleSubmit} aria-label="Reset password form">
            {!tokenFromUrl && (
              <>
                <div className="auth-method-toggle" role="group" aria-label="Reset method">
                  <button
                    type="button"
                    className={method === 'email' ? 'active' : ''}
                    onClick={() => setMethod('email')}
                    disabled
                    title="Use the link from your email"
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

                {method === 'sms' && (
                  <>
                    <div className="auth-input-group">
                      <label htmlFor="reset-identifier">Email or username</label>
                      <input
                        type="text"
                        id="reset-identifier"
                        value={identifier}
                        onChange={(e) => {
                          setIdentifier(e.target.value);
                          if (fieldErrors.identifier) {
                            setFieldErrors((current) => ({ ...current, identifier: '' }));
                          }
                        }}
                        required
                        aria-invalid={Boolean(fieldErrors.identifier)}
                        aria-describedby={fieldErrors.identifier ? 'reset-identifier-error' : undefined}
                      />
                      {fieldErrors.identifier && (
                        <p className="form-field-error" id="reset-identifier-error" role="alert">
                          {fieldErrors.identifier}
                        </p>
                      )}
                    </div>
                    <div className="auth-input-group">
                      <label htmlFor="reset-otp">6-digit code</label>
                      <input
                        type="text"
                        id="reset-otp"
                        inputMode="numeric"
                        maxLength={6}
                        placeholder="000000"
                        value={otp}
                        onChange={(e) => {
                          setOtp(e.target.value.replace(/\D/g, ''));
                          if (fieldErrors.otp) {
                            setFieldErrors((current) => ({ ...current, otp: '' }));
                          }
                        }}
                        required
                        aria-invalid={Boolean(fieldErrors.otp)}
                        aria-describedby={fieldErrors.otp ? 'reset-otp-error' : undefined}
                      />
                      {fieldErrors.otp && (
                        <p className="form-field-error" id="reset-otp-error" role="alert">
                          {fieldErrors.otp}
                        </p>
                      )}
                    </div>
                  </>
                )}
              </>
            )}

            {tokenFromUrl && (
              <p className="auth-hint">You opened a valid reset link. Enter your new password below.</p>
            )}

            <div className="auth-input-group">
              <label htmlFor="reset-new-password">New password</label>
              <input
                type="password"
                id="reset-new-password"
                value={newPassword}
                onChange={(e) => {
                  setNewPassword(e.target.value);
                  if (fieldErrors.newPassword) {
                    setFieldErrors((current) => ({ ...current, newPassword: '' }));
                  }
                }}
                required
                minLength={8}
                autoComplete="new-password"
                placeholder="Create a strong password"
                aria-invalid={Boolean(fieldErrors.newPassword)}
                aria-describedby="reset-password-requirements"
              />
              <PasswordRequirementsPanel password={newPassword} id="reset-password-requirements" />
              {fieldErrors.newPassword && (
                <p className="form-field-error" id="reset-new-password-error" role="alert">
                  {fieldErrors.newPassword}
                </p>
              )}
            </div>
            <div className="auth-input-group">
              <label htmlFor="reset-confirm-password">Confirm password</label>
              <input
                type="password"
                id="reset-confirm-password"
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  if (fieldErrors.confirmPassword) {
                    setFieldErrors((current) => ({ ...current, confirmPassword: '' }));
                  }
                }}
                required
                minLength={8}
                autoComplete="new-password"
                aria-invalid={Boolean(fieldErrors.confirmPassword)}
                aria-describedby={fieldErrors.confirmPassword ? 'reset-confirm-password-error' : undefined}
              />
              {fieldErrors.confirmPassword && (
                <p className="form-field-error" id="reset-confirm-password-error" role="alert">
                  {fieldErrors.confirmPassword}
                </p>
              )}
            </div>

            {fieldErrors.form && <p className="auth-error" role="alert">{fieldErrors.form}</p>}

            <button type="submit" className="auth-submit-btn" disabled={isSubmitDisabled}>
              {isLoading ? 'Updating…' : 'Update password'}
            </button>

            {message && <p className="auth-success" role="status">{message}</p>}
            {error && <p className="auth-error" role="alert">{error}</p>}
          </form>
        </div>
      </div>
    </div>
  );
}

export default ResetPasswordPage;
