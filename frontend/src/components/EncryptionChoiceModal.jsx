import React, { useState } from 'react';
import { toast } from 'react-toastify';
import '../styles/encryption-modal.css';

const EncryptionChoiceModal = ({ file, onClose, onChoose }) => {
  const [selectedMethod, setSelectedMethod] = useState(null);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState({ level: 0, message: '' });
  const [skipAcknowledged, setSkipAcknowledged] = useState(false);
  const [formError, setFormError] = useState('');

  const checkPasswordStrength = (pwd) => {
    if (!pwd) {
      return { level: 0, message: '' };
    }

    let strength = 0;
    const checks = {
      length: pwd.length >= 12,
      uppercase: /[A-Z]/.test(pwd),
      lowercase: /[a-z]/.test(pwd),
      number: /[0-9]/.test(pwd),
      special: /[!@#$%^&*()_+\-=\\{};':"\\|,.<>?]/.test(pwd),
    };

    // Calculate strength
    if (checks.length) strength++;
    if (checks.uppercase) strength++;
    if (checks.lowercase) strength++;
    if (checks.number) strength++;
    if (checks.special) strength++;

    let message = '';
    const missing = [];
    if (!checks.length) missing.push('12+ characters');
    if (!checks.uppercase) missing.push('uppercase letter');
    if (!checks.number) missing.push('number');
    if (!checks.special) missing.push('special character');

    if (strength <= 2) {
      message = `Weak - Add: ${missing.join(', ')}`;
    } else if (strength === 3 || strength === 4) {
      message = `Medium - Add: ${missing.join(', ')}`;
    } else if (strength === 5) {
      message = 'Strong';
    }

    return { level: strength, message, checks };
  };

  const handlePasswordChange = (value) => {
    setPassword(value);
    setPasswordStrength(checkPasswordStrength(value));
  };

  const handleMethodSelect = (method) => {
    setSelectedMethod(method);
    if (method === 'client-side') {
      setShowPasswordForm(true);
    } else {
      setShowPasswordForm(false);
    }
    if (method !== 'none') {
      setSkipAcknowledged(false);
    }
  };

  const handleSubmit = async () => {
    setFormError('');
    if (!selectedMethod) {
      setFormError('Please select an encryption method.');
      toast.error('Please select an encryption method.');
      return;
    }

    if (selectedMethod === 'none' && !skipAcknowledged) {
      setFormError('Confirm you accept storing this file without Zenith encryption.');
      toast.error('Confirm you accept storing this file without Zenith encryption.');
      return;
    }

    if (selectedMethod === 'client-side') {
      if (!password) {
        setFormError('Please enter a password.');
        toast.error('Please enter a password.');
        return;
      }
      if (password.length < 12) {
        setFormError('Password must be at least 12 characters for strong encryption.');
        toast.error('Password must be at least 12 characters for strong encryption.');
        return;
      }
      if (!passwordStrength.checks.uppercase || !passwordStrength.checks.number || !passwordStrength.checks.special) {
        const msg = 'Password must include an uppercase letter, a number, and a special character.';
        setFormError(msg);
        toast.error(msg);
        return;
      }
      if (password !== confirmPassword) {
        setFormError('Passwords do not match.');
        toast.error('Passwords do not match.');
        return;
      }
    }

    setIsSubmitting(true);
    await onChoose(selectedMethod, password);
    setIsSubmitting(false);
  };

  return (
    <div className="encryption-modal-overlay">
      <div className="encryption-modal">
        <div className="encryption-modal-header">
          <h2>Choose Encryption Method</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="encryption-modal-body">
          <div className="file-info-banner">
            <p>File: <strong>{file.filename}</strong></p>
            <p className="sensitive-warning" role="alert">
              This file contains sensitive data or requires encryption.
            </p>
          </div>

          <div className="encryption-options">
            <div
              className={`encryption-option ${selectedMethod === 'server-side' ? 'selected' : ''}`}
              onClick={() => handleMethodSelect('server-side')}
            >
              <div className="option-header">
                <input
                  type="radio"
                  name="encryption"
                  checked={selectedMethod === 'server-side'}
                  onChange={() => handleMethodSelect('server-side')}
                />
                <h3>Cloud-managed encryption</h3>
              </div>
              <div className="option-description">
                <p><strong>Your cloud encrypts at rest with managed keys (AES-256)</strong></p>
                <ul>
                  <li className="pro">No password to remember</li>
                  <li className="pro">Fast upload — encryption handled by the provider</li>
                  <li className="pro">Optional replica region on AWS when configured</li>
                  <li className="caution">Zenith operators could access plaintext via cloud controls</li>
                </ul>
                <p className="recommendation">
                  <strong>Best for:</strong> Convenience, compliance, shared team access
                </p>
              </div>
            </div>

            <div
              className={`encryption-option ${selectedMethod === 'none' ? 'selected' : ''}`}
              onClick={() => handleMethodSelect('none')}
            >
              <div className="option-header">
                <input
                  type="radio"
                  name="encryption"
                  checked={selectedMethod === 'none'}
                  onChange={() => handleMethodSelect('none')}
                />
                <h3>Store without encryption</h3>
              </div>
              <div className="option-description">
                <p><strong>Vault + 2FA only — no Zenith encryption layer</strong></p>
                <ul>
                  <li className="caution">Sensitive scan flagged this file — skipping encryption is risky</li>
                  <li className="caution">Anyone with vault or cloud access may read plaintext</li>
                </ul>
              </div>
            </div>

            <div
              className={`encryption-option ${selectedMethod === 'client-side' ? 'selected' : ''}`}
              onClick={() => handleMethodSelect('client-side')}
            >
              <div className="option-header">
                <input
                  type="radio"
                  name="encryption"
                  checked={selectedMethod === 'client-side'}
                  onChange={() => handleMethodSelect('client-side')}
                />
                <h3>Client-Side Encryption (browser)</h3>
              </div>
              <div className="option-description">
                <p><strong>Encrypted in your browser before upload — zero-knowledge</strong></p>
                <ul>
                  <li className="pro">Password never sent to Zenith servers</li>
                  <li className="pro">AES-256-CBC + PBKDF2 (100k iterations) in Web Crypto</li>
                  <li className="pro">Ciphertext stored on S3 + replica bucket</li>
                  <li className="pro"><strong>Only your password can decrypt</strong></li>
                  <li className="caution">If you lose your password, the file cannot be recovered</li>
                </ul>
                <p className="recommendation">
                  <strong>Best for:</strong> Credentials, secrets, maximum privacy
                </p>
              </div>
            </div>
          </div>

          {showPasswordForm && selectedMethod === 'client-side' && (
            <div className="password-form">
              <div className="password-warning">
                <strong>Important:</strong> Encryption happens locally in your browser. Your password
                is not stored on our servers. If you forget it, the file cannot be recovered.
              </div>
              <div className="form-group">
                <label>Encryption Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => handlePasswordChange(e.target.value)}
                  placeholder="Min 12 chars, uppercase, number, special char"
                  className="password-input"
                  minLength={12}
                />
                {password && (
                  <div className="password-strength-container">
                    <div className={`password-strength-bar strength-${passwordStrength.level}`}>
                      <div className="strength-fill"></div>
                    </div>
                    <p className={`strength-text strength-${passwordStrength.level}`}>
                      {passwordStrength.message}
                    </p>
                    <div className="password-requirements">
                      <small className={passwordStrength.checks?.length ? 'met' : 'unmet'}>
                        {passwordStrength.checks?.length ? '✓' : '○'} 12+ characters
                      </small>
                      <small className={passwordStrength.checks?.uppercase ? 'met' : 'unmet'}>
                        {passwordStrength.checks?.uppercase ? '✓' : '○'} Uppercase letter
                      </small>
                      <small className={passwordStrength.checks?.number ? 'met' : 'unmet'}>
                        {passwordStrength.checks?.number ? '✓' : '○'} Number
                      </small>
                      <small className={passwordStrength.checks?.special ? 'met' : 'unmet'}>
                        {passwordStrength.checks?.special ? '✓' : '○'} Special character
                      </small>
                    </div>
                  </div>
                )}
              </div>
              <div className="form-group">
                <label>Confirm Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter password"
                  className="password-input"
                />
                {confirmPassword && password !== confirmPassword && (
                  <p className="error-text">Passwords do not match</p>
                )}
              </div>
              {password && (
                <div className="password-strength">
                  <p>Password strength: {
                    password.length < 12 ? 'Too short' :
                    password.length < 16 ? 'Moderate' :
                    'Strong'
                  }</p>
                </div>
              )}
            </div>
          )}

          {selectedMethod === 'none' && (
            <label className="security-skip-encrypt-ack encryption-skip-ack">
              <input
                type="checkbox"
                checked={skipAcknowledged}
                onChange={(e) => setSkipAcknowledged(e.target.checked)}
              />
              <span>
                I understand this file may contain sensitive data and I accept storing it without
                Zenith encryption.
              </span>
            </label>
          )}
        </div>

        {formError ? (
          <p className="encryption-form-error" role="alert">{formError}</p>
        ) : null}

        <div className="encryption-modal-footer">
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button
            className="btn-encrypt"
            onClick={handleSubmit}
            disabled={
              !selectedMethod ||
              isSubmitting ||
              (selectedMethod === 'none' && !skipAcknowledged)
            }
          >
            {isSubmitting
              ? 'Uploading...'
              : selectedMethod === 'none'
                ? 'Store without encryption'
                : `Encrypt with ${selectedMethod || '...'}`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EncryptionChoiceModal;
