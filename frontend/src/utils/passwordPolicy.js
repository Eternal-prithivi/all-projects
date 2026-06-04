/** Client-side vault password rules (browser encryption). */

const SPECIAL_CHAR_RE = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/;

export function checkPasswordStrength(pwd) {
  if (!pwd) {
    return { level: 0, message: "", checks: emptyChecks() };
  }

  const checks = {
    length: pwd.length >= 12,
    uppercase: /[A-Z]/.test(pwd),
    lowercase: /[a-z]/.test(pwd),
    number: /[0-9]/.test(pwd),
    special: SPECIAL_CHAR_RE.test(pwd),
  };

  let strength = 0;
  if (checks.length) strength++;
  if (checks.uppercase) strength++;
  if (checks.lowercase) strength++;
  if (checks.number) strength++;
  if (checks.special) strength++;

  const missing = [];
  if (!checks.length) missing.push("12+ characters");
  if (!checks.uppercase) missing.push("uppercase letter");
  if (!checks.lowercase) missing.push("lowercase letter");
  if (!checks.number) missing.push("number");
  if (!checks.special) missing.push("special character");

  let message = "";
  if (strength <= 2) {
    message = missing.length ? `Weak — add: ${missing.join(", ")}` : "Weak";
  } else if (strength <= 4) {
    message = missing.length ? `Almost there — add: ${missing.join(", ")}` : "Good";
  } else {
    message = "Strong password";
  }

  return { level: strength, message, checks };
}

function emptyChecks() {
  return {
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false,
  };
}

export function isClientPasswordValid(password, confirmPassword) {
  if (!password || !confirmPassword) return false;
  const { checks } = checkPasswordStrength(password);
  return (
    checks.length &&
    checks.uppercase &&
    checks.lowercase &&
    checks.number &&
    checks.special &&
    password === confirmPassword
  );
}
