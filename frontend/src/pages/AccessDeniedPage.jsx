import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FaShieldAlt, FaLock, FaHome } from 'react-icons/fa';
import '../styles/access-denied.css';

const AccessDeniedPage = () => {
  const navigate = useNavigate();

  return (
    <div className="access-denied-page">
      <div className="access-denied-container">
        <div className="denied-icon-wrapper">
          <FaShieldAlt className="denied-shield" />
          <FaLock className="denied-lock" />
        </div>
        
        <h1 className="denied-title">Access Restricted</h1>
        
        <p className="denied-message">
          You do not have permission to access the Admin Portal.
        </p>
        
        <p className="denied-description">
          This area is restricted to administrators only. If you believe you should have access, 
          please contact your system administrator.
        </p>

        <div className="denied-actions">
          <button 
            onClick={() => navigate('/dashboard')} 
            className="btn-back-dashboard"
          >
            <FaHome /> Go to Dashboard
          </button>
        </div>

        <div className="denied-footer">
          <p>Need help? Contact support at <a href="mailto:aangatla957@gmail.com">aangatla957@gmail.com</a></p>
        </div>
      </div>
    </div>
  );
};

export default AccessDeniedPage;
