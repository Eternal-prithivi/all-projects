import React from 'react';
import { Link } from 'react-router-dom';
import { ADMIN_SECURITY_SETTINGS_PATH } from '../../utils/adminPortalGate.js';

const AdminPortalGateBanner = ({ gateError }) => {
  if (!gateError) return null;

  const isVerify = gateError.code === 'ADMIN_2FA_VERIFY';
  const setupPath = gateError.setupPath || ADMIN_SECURITY_SETTINGS_PATH;

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
