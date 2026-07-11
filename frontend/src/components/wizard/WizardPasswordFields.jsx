import React, { useMemo } from "react";
import { checkPasswordStrength } from "../../utils/passwordPolicy";

export default function WizardPasswordFields({
  password,
  confirmPassword,
  onPasswordChange,
  onConfirmChange,
}) {
  const strength = useMemo(() => checkPasswordStrength(password), [password]);
  const passwordsMatch =
    confirmPassword.length > 0 && password.length > 0 && password === confirmPassword;
  const passwordsMismatch =
    confirmPassword.length > 0 && password.length > 0 && password !== confirmPassword;

  return (
    <div className="zenith-wizard-password-form">
      <div className="zenith-wizard-password-field">
        <label htmlFor="wizard-encrypt-password">Encryption password</label>
        <input
          id="wizard-encrypt-password"
          type="password"
          className="zenith-wizard-password-input"
          value={password}
          onChange={(e) => onPasswordChange(e.target.value)}
          autoComplete="new-password"
        />
      </div>

      <div className="password-strength-container" aria-live="polite">
        <div className={`password-strength-bar strength-${strength.level}`}>
          <div className="strength-fill" />
        </div>
        <p className={`strength-text strength-${strength.level}`}>
          {password ? strength.message : "Enter a password to see strength"}
        </p>
        <div className="password-requirements">
          <small className={strength.checks?.length ? "met" : "unmet"}>
            {strength.checks?.length ? "✓" : "○"} 8+ characters
          </small>
          <small className={strength.checks?.uppercase ? "met" : "unmet"}>
            {strength.checks?.uppercase ? "✓" : "○"} Uppercase (A–Z)
          </small>
          <small className={strength.checks?.lowercase ? "met" : "unmet"}>
            {strength.checks?.lowercase ? "✓" : "○"} Lowercase (a–z)
          </small>
          <small className={strength.checks?.number ? "met" : "unmet"}>
            {strength.checks?.number ? "✓" : "○"} Number
          </small>
          <small className={strength.checks?.special ? "met" : "unmet"}>
            {strength.checks?.special ? "✓" : "○"} Special character
          </small>
        </div>
      </div>

      <div className="zenith-wizard-password-field">
        <label htmlFor="wizard-confirm-password">Confirm password</label>
        <input
          id="wizard-confirm-password"
          type="password"
          className={`zenith-wizard-password-input${
            passwordsMismatch ? " zenith-wizard-password-input--error" : ""
          }${passwordsMatch ? " zenith-wizard-password-input--ok" : ""}`}
          value={confirmPassword}
          onChange={(e) => onConfirmChange(e.target.value)}
          autoComplete="new-password"
        />
        {passwordsMatch && (
          <p className="zenith-wizard-password-hint zenith-wizard-password-hint--ok">
            Passwords match
          </p>
        )}
        {passwordsMismatch && (
          <p className="zenith-wizard-password-hint zenith-wizard-password-hint--error">
            Passwords do not match
          </p>
        )}
      </div>
    </div>
  );
}
