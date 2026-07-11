import React, { useMemo } from 'react';
import { checkPasswordStrength } from '../../utils/passwordPolicy.js';
import '../../styles/password-requirements.css';

const REQUIREMENTS = [
  { key: 'length', label: 'At least 8 characters' },
  { key: 'uppercase', label: 'One uppercase letter (A–Z)' },
  { key: 'lowercase', label: 'One lowercase letter (a–z)' },
  { key: 'number', label: 'One number (0–9)' },
  { key: 'special', label: 'One symbol (!@#$…)' },
];

/**
 * Live password rules for auth forms — matches backend password_policy (8+ + complexity).
 */
export default function PasswordRequirementsPanel({ password, id = 'password-requirements' }) {
  const strength = useMemo(() => checkPasswordStrength(password), [password]);
  const checks = strength.checks || {};
  const allMet = REQUIREMENTS.every((rule) => checks[rule.key]);

  return (
    <div className="auth-password-requirements" id={id} aria-live="polite">
      {!password ? (
        <p className="auth-password-requirements-intro">
          Choose a strong password: 8+ characters with uppercase, lowercase, a number, and a
          symbol. Example: <span className="auth-password-example">Zenith@1</span>
        </p>
      ) : (
        <>
          <div
            className={`auth-password-strength-bar strength-${strength.level}`}
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={5}
            aria-valuenow={strength.level}
            aria-label="Password strength"
          >
            <div className="auth-password-strength-fill" />
          </div>
          <p className={`auth-password-strength-text strength-${strength.level}`}>
            {allMet ? 'Strong password — you can use this' : strength.message}
          </p>
        </>
      )}

      <ul className="auth-password-checklist">
        {REQUIREMENTS.map((rule) => {
          const met = Boolean(checks[rule.key]);
          return (
            <li key={rule.key} className={met ? 'met' : 'unmet'}>
              <span className="auth-password-check-icon" aria-hidden="true">
                {met ? '✓' : '○'}
              </span>
              {rule.label}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
