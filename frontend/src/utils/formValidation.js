const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const USERNAME_PATTERN = /^[a-zA-Z0-9._-]+$/;
const PHONE_PATTERN = /^\+?[1-9]\d{7,14}$/;
const trimValue = (value) => value.trim();

const buildResult = (errors) => ({
  isValid: Object.keys(errors).length === 0,
  errors,
});

const getFirstErrorMessage = (errors) => Object.values(errors)[0] || '';

export const isValidEmail = (value) => EMAIL_PATTERN.test(trimValue(value));

export const validateUsername = (value) => {
  const trimmedValue = trimValue(value);

  if (!trimmedValue) {
    return 'Username is required.';
  }

  if (trimmedValue.length < 3) {
    return 'Username must be at least 3 characters.';
  }

  if (trimmedValue.length > 32) {
    return 'Username must be 32 characters or fewer.';
  }

  if (!USERNAME_PATTERN.test(trimmedValue)) {
    return 'Use letters, numbers, dots, underscores, or hyphens only.';
  }

  return '';
};

export const validatePassword = (value, options = {}) => {
  const { minLength = 12 } = options;
  const trimmedValue = value.trim();

  if (!trimmedValue) {
    return 'Password is required.';
  }

  if (trimmedValue.length < minLength) {
    return `Password must be at least ${minLength} characters.`;
  }

  if (!/[a-z]/.test(trimmedValue) || !/[A-Z]/.test(trimmedValue) || !/\d/.test(trimmedValue) || !/[^A-Za-z0-9]/.test(trimmedValue)) {
    return 'Password must include uppercase, lowercase, a number, and a symbol.';
  }

  return '';
};

export const validatePhoneNumber = (value) => {
  const trimmedValue = trimValue(value);

  if (!trimmedValue) {
    return '';
  }

  if (!PHONE_PATTERN.test(trimmedValue)) {
    return 'Enter a valid phone number with country code.';
  }

  return '';
};

export const validateLoginForm = ({ username, password }) => {
  const errors = {};

  // Login only checks for non-empty fields — the server validates credentials.
  // Password strength / username format rules belong to registration, not login.
  if (!username.trim()) {
    errors.username = 'Username is required.';
  }

  if (!password) {
    errors.password = 'Password is required.';
  }

  return buildResult(errors);
};

export const validateRegisterForm = ({ username, email, password }) => {
  const errors = {};
  const usernameError = validateUsername(username);
  const emailValue = trimValue(email);
  const passwordError = validatePassword(password);

  if (usernameError) {
    errors.username = usernameError;
  }

  if (!emailValue) {
    errors.email = 'Email is required.';
  } else if (!isValidEmail(emailValue)) {
    errors.email = 'Enter a valid email address.';
  }

  if (passwordError) {
    errors.password = passwordError;
  }

  return buildResult(errors);
};

export const validateForgotPasswordForm = ({ identifier }) => {
  const errors = {};
  const identifierValue = trimValue(identifier);

  if (!identifierValue) {
    errors.identifier = 'Enter your username or email.';
  } else if (identifierValue.includes('@')) {
    if (!isValidEmail(identifierValue)) {
      errors.identifier = 'Enter a valid email address.';
    }
  } else if (validateUsername(identifierValue)) {
    errors.identifier = 'Username must be at least 3 characters and use valid characters only.';
  }

  return buildResult(errors);
};

export const validateResetPasswordForm = ({
  token,
  identifier,
  otp,
  newPassword,
  confirmPassword,
  isEmailFlow,
}) => {
  const errors = {};
  const passwordError = validatePassword(newPassword);
  const confirmPasswordValue = confirmPassword.trim();

  if (!isEmailFlow) {
    if (!trimValue(identifier)) {
      errors.identifier = 'Enter your username or email.';
    }

    if (!trimValue(otp)) {
      errors.otp = 'Enter the 6-digit code from SMS.';
    } else if (trimValue(otp).length !== 6) {
      errors.otp = 'SMS codes must be 6 digits.';
    }
  } else if (!token) {
    errors.form = 'Open the email reset link first or request a new one.';
  }

  if (passwordError) {
    errors.newPassword = passwordError;
  }

  if (!confirmPasswordValue) {
    errors.confirmPassword = 'Confirm your new password.';
  } else if (newPassword !== confirmPassword) {
    errors.confirmPassword = 'Passwords do not match.';
  }

  return buildResult(errors);
};

export const validateContactForm = ({ name, email, subject, message }) => {
  const errors = {};
  const nameValue = trimValue(name);
  const emailValue = trimValue(email);
  const messageValue = trimValue(message);

  if (nameValue.length < 2) {
    errors.name = 'Enter your full name.';
  }

  if (!emailValue) {
    errors.email = 'Email is required.';
  } else if (!isValidEmail(emailValue)) {
    errors.email = 'Enter a valid email address.';
  }

  if (!subject) {
    errors.subject = 'Choose a subject.';
  }

  if (messageValue.length < 20) {
    errors.message = 'Please add a bit more detail so we can help.';
  }

  return buildResult(errors);
};

export const validateProfileForm = ({ username, email, fullName, company }) => {
  const errors = {};
  const usernameError = validateUsername(username);
  const emailValue = trimValue(email);
  const fullNameValue = trimValue(fullName);
  const companyValue = trimValue(company);

  if (usernameError) {
    errors.username = usernameError;
  }

  if (!emailValue) {
    errors.email = 'Email is required.';
  } else if (!isValidEmail(emailValue)) {
    errors.email = 'Enter a valid email address.';
  }

  if (!fullNameValue) {
    errors.full_name = 'Full name is required.';
  } else if (fullNameValue.length < 2) {
    errors.full_name = 'Full name must be at least 2 characters.';
  }

  if (companyValue && companyValue.length < 2) {
    errors.company = 'Company name must be at least 2 characters.';
  }

  return buildResult(errors);
};

export const validateRecoveryContactsForm = ({ recoveryEmail, phone, recoveryPhone }) => {
  const errors = {};
  const recoveryEmailValue = trimValue(recoveryEmail);
  const phoneValue = trimValue(phone);
  const recoveryPhoneValue = trimValue(recoveryPhone);

  if (recoveryEmailValue && !isValidEmail(recoveryEmailValue)) {
    errors.recovery_email = 'Enter a valid recovery email address.';
  }

  const phoneError = validatePhoneNumber(phoneValue);
  if (phoneError) {
    errors.phone = phoneError;
  }

  const recoveryPhoneError = validatePhoneNumber(recoveryPhoneValue);
  if (recoveryPhoneError) {
    errors.recovery_phone = recoveryPhoneError;
  }

  if (!recoveryEmailValue && !phoneValue && !recoveryPhoneValue) {
    errors.form = 'Add at least one recovery email or phone number.';
  }

  return buildResult(errors);
};

export const validatePasswordChangeForm = ({ currentPassword, newPassword, confirmPassword }) => {
  const errors = {};
  const currentPasswordValue = trimValue(currentPassword);
  const newPasswordError = validatePassword(newPassword);
  const confirmPasswordValue = confirmPassword.trim();

  if (!currentPasswordValue) {
    errors.currentPassword = 'Enter your current password.';
  }

  if (newPasswordError) {
    errors.newPassword = newPasswordError;
  }

  if (!confirmPasswordValue) {
    errors.confirmPassword = 'Confirm your new password.';
  } else if (newPassword !== confirmPassword) {
    errors.confirmPassword = 'Passwords do not match.';
  }

  return buildResult(errors);
};

export const validateByocAwsStep1 = ({ method, awsForm = {} }) => {
  const errors = {};
  if (method === 'access_keys') {
    if (!trimValue(awsForm.access_key_id || '')) {
      errors.access_key_id = 'Access key ID is required.';
    }
    if (!trimValue(awsForm.secret_access_key || '')) {
      errors.secret_access_key = 'Secret access key is required.';
    }
  } else if (method === 'iam_role') {
    if (!trimValue(awsForm.role_arn || '')) {
      errors.role_arn = 'Role ARN is required.';
    }
  }
  if (!trimValue(awsForm.region || '')) {
    errors.region = 'Choose a primary region.';
  }
  return buildResult(errors);
};

export const validateByocAwsStep2 = ({ awsForm = {} }) => {
  const errors = {};
  const storage = trimValue(awsForm.storage_bucket_name || awsForm.bucket_name || '');
  const secure = trimValue(awsForm.secure_bucket_name || '');
  const replica = trimValue(awsForm.replica_bucket_name || '');

  if (!storage) {
    errors.storage_bucket_name = 'Storage bucket name is required.';
  }
  if (!secure) {
    errors.secure_bucket_name = 'Secure bucket name is required.';
  }
  if (awsForm.secure_dual_write !== false && !replica) {
    errors.replica_bucket_name = 'Replica bucket name is required for secure replication.';
  }
  return buildResult(errors);
};

export const validateByocGcpStep1 = ({ gcpForm = {} }) => {
  const errors = {};
  const serviceAccountJson = trimValue(gcpForm.service_account_json || '');
  if (!serviceAccountJson) {
    errors.service_account_json = 'Service account JSON is required.';
  } else {
    try {
      JSON.parse(serviceAccountJson);
    } catch {
      errors.service_account_json = 'Paste valid service account JSON.';
    }
  }
  return buildResult(errors);
};

export const validateByocGcpStep2 = ({ gcpForm = {} }) => {
  const errors = {};
  const storage = trimValue(gcpForm.storage_bucket_name || gcpForm.gcp_bucket_name || '');
  const secure = trimValue(gcpForm.secure_bucket_name || '');
  const replica = trimValue(gcpForm.replica_bucket_name || '');
  if (!storage) errors.storage_bucket_name = 'Storage bucket name is required.';
  if (!secure) errors.secure_bucket_name = 'Secure bucket name is required.';
  if (gcpForm.secure_dual_write !== false && !replica) {
    errors.replica_bucket_name = 'Replica bucket name is required for secure replication.';
  }
  return buildResult(errors);
};

export const validateByocAzureStep1 = ({ azureForm = {} }) => {
  const errors = {};
  if (!trimValue(azureForm.account_name || '')) {
    errors.account_name = 'Storage account name is required.';
  }
  if (!trimValue(azureForm.account_key || '')) {
    errors.account_key = 'Storage account key is required.';
  }
  return buildResult(errors);
};

export const validateByocAzureStep2 = ({ azureForm = {} }) => {
  const errors = {};
  const storage = trimValue(azureForm.storage_container_name || azureForm.container_name || '');
  const secure = trimValue(azureForm.secure_container_name || '');
  const replica = trimValue(azureForm.replica_container_name || '');
  if (!storage) errors.storage_container_name = 'Storage container name is required.';
  if (!secure) errors.secure_container_name = 'Secure container name is required.';
  if (azureForm.secure_dual_write !== false && !replica) {
    errors.replica_container_name = 'Replica container name is required for secure replication.';
  }
  return buildResult(errors);
};

export const validateByocConnectionForm = ({ csp, method, awsForm = {}, gcpForm = {}, azureForm = {}, awsStep = null, gcpStep = null, azureStep = null }) => {
  const errors = {};

  if (!csp) {
    return buildResult(errors);
  }

  if (csp === 'AWS') {
    if (awsStep === 1) {
      return validateByocAwsStep1({ method, awsForm });
    }
    if (awsStep === 2) {
      return validateByocAwsStep2({ awsForm });
    }
    if (method === 'access_keys') {
      if (!trimValue(awsForm.access_key_id || '')) {
        errors.access_key_id = 'Access key ID is required.';
      }

      if (!trimValue(awsForm.secret_access_key || '')) {
        errors.secret_access_key = 'Secret access key is required.';
      }
    } else if (method === 'iam_role') {
      if (!trimValue(awsForm.role_arn || '')) {
        errors.role_arn = 'Role ARN is required.';
      }
    }

    if (!trimValue(awsForm.storage_bucket_name || awsForm.bucket_name || '')) {
      errors.storage_bucket_name = 'Storage bucket name is required.';
    }

    if (!trimValue(awsForm.region || '')) {
      errors.region = 'Choose a region.';
    }
  }

  if (csp === 'GCP') {
    if (gcpStep === 1) return validateByocGcpStep1({ gcpForm });
    if (gcpStep === 2) return validateByocGcpStep2({ gcpForm });
    return validateByocGcpStep2({ gcpForm });
  }

  if (csp === 'Azure') {
    if (azureStep === 1) return validateByocAzureStep1({ azureForm });
    if (azureStep === 2) return validateByocAzureStep2({ azureForm });
    return validateByocAzureStep2({ azureForm });
  }

  return buildResult(errors);
};

export const getValidationErrorMessage = (errors) => getFirstErrorMessage(errors);