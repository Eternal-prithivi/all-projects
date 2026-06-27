const SECURITY_SETTINGS_PATH = '/dashboard/security-settings';

export const parseAdminPortalGateError = (error) => {
  const detail = error?.response?.data?.detail;
  if (!detail) return null;

  if (typeof detail === 'string') {
    if (/two-factor|2fa/i.test(detail)) {
      return {
        code: 'ADMIN_2FA_REQUIRED',
        message: detail,
        setupPath: SECURITY_SETTINGS_PATH,
      };
    }
    return null;
  }

  if (typeof detail === 'object' && detail.code?.startsWith('ADMIN_2FA')) {
    return {
      code: detail.code,
      message: detail.message || 'Admin portal access requires two-factor authentication.',
      setupPath: detail.setup_path || SECURITY_SETTINGS_PATH,
    };
  }

  return null;
};

export const ADMIN_SECURITY_SETTINGS_PATH = SECURITY_SETTINGS_PATH;
