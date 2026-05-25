import React, { useState } from 'react';
import '../styles/encryption-modal.css';

const EncryptionChoiceModal = ({ file, onClose, onChoose }) => {
  const [selectedMethod, setSelectedMethod] = useState(null);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState({ level: 0, message: '' });

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
      message = 'Strong ✓';
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
  };

  const handleSubmit = async () => {
    if (!selectedMethod) {
      alert('Please select an encryption method');
      return;
    }

    if (selectedMethod === 'client-side') {
      if (!password) {
        alert('Please enter a password');
        return;
      }
      if (password.length < 12) {
        alert('Password must be at least 12 characters for strong encryption');
        return;
      }
      if (!passwordStrength.checks.uppercase || !passwordStrength.checks.number || !passwordStrength.checks.special) {
        alert('Password must contain at least:\n• One uppercase letter (A-Z)\n• One number (0-9)\n• One special character (!@#$%^&*)');
        return;
      }
      if (password !== confirmPassword) {
        alert('Passwords do not match');
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
          <h2>🔐 Choose Encryption Method</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="encryption-modal-body">
          <div className="file-info-banner">
            <p>File: <strong>{file.filename}</strong></p>
            <p className="sensitive-warning">
              ⚠️ This file contains sensitive data or requires encryption
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
                <h3>🛡️ Server-Side Encryption</h3>
              </div>
              <div className="option-description">
                <p><strong>AWS manages the encryption keys</strong></p>
                <ul>
                  <li>✅ Automatic encryption with AES-256</li>
                  <li>✅ No password needed</li>
                  <li>✅ Replicated to secondary region</li>
                  <li>⚠️ Platform administrators can access the file</li>
                  <li>💰 Standard cost</li>
                </ul>
                <p className="recommendation">
                  <strong>Best for:</strong> Compliance requirements, team collaboration
                </p>
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
                <h3>🔒 Client-Side Encryption</h3>
              </div>
              <div className="option-description">
                <p><strong>You control the encryption key</strong></p>
                <ul>
                  <li>✅ Maximum security - only you can decrypt</li>
                  <li>✅ AES-256 encryption with your password</li>
                  <li>✅ Replicated to secondary region</li>
                  <li>🔐 <strong>Even platform admins cannot read your file</strong></li>
                  <li>⚠️ If you lose your password, file is unrecoverable</li>
                  <li>💰 Standard cost</li>
                </ul>
                <p className="recommendation">
                  <strong>Best for:</strong> Highly sensitive personal data, maximum privacy
                </p>
              </div>
            </div>
          </div>

          {showPasswordForm && selectedMethod === 'client-side' && (
            <div className="password-form">
              <div className="password-warning">
                <strong>⚠️ IMPORTANT:</strong> You must remember this password. There is no way to recover 
                your file if you forget it. We recommend using a password manager.
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
                  <p className="error-text">❌ Passwords do not match</p>
                )}
              </div>
              {password && (
                <div className="password-strength">
                  <p>Password strength: {
                    password.length < 12 ? '❌ Too short' :
                    password.length < 16 ? '⚠️ Moderate' :
                    '✅ Strong'
                  }</p>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="encryption-modal-footer">
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button
            className="btn-encrypt"
            onClick={handleSubmit}
            disabled={!selectedMethod || isSubmitting}
          >
            {isSubmitting ? 'Encrypting...' : `Encrypt with ${selectedMethod || '...'}`}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EncryptionChoiceModal;
