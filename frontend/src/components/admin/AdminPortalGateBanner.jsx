import React from 'react';
import { Link } from 'react-router-dom';

const SECURITY_SETTINGS_PATH = '/dashboard/security-settings';

const AdminPortalGateBanner = ({ gateError }) => {
  if (!gateError) return null;

  const isVerify = gateError.code === 'ADMIN_2FA_VERIFY';
  const setupPath = gateError.setupPath || SECURITY_SETTINGS_PATH;

  return (
    <div className="admin-portal-gate-banner" role="alert">
      <div className="admin-portal-gate-banner__content">
        <h3>{isVerify ? 'Two-factor verification required' : 'Two-factor authentication required'}</h3>
        <p>{gateError.message}</p>
        <Link to={setupPath} className="btn-primary">
          {isVerify ? 'Complete 2FA verification' : 'Set up 2FA in Security Settings'}
        </Link>
      </div>
    </div>
  );
};

export default AdminPortalGateBanner;

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
