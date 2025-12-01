import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/error-pages.css';

const ServerErrorPage = () => {
  const navigate = useNavigate();

  const handleRefresh = () => {
    window.location.reload();
  };

  return (
    <div className="error-page">
      <div className="error-container">
        {/* Error Code */}
        <div className="error-code">500</div>

        {/* Error Title */}
        <h1 className="error-title">Server Error</h1>

        {/* Error Description */}
        <p className="error-description">
          Oops! Something went wrong on our end.
          <br />
          Our team has been notified and we're working on a fix.
        </p>

        {/* Illustration */}
        <div className="error-illustration">
          <svg
            width="300"
            height="200"
            viewBox="0 0 300 200"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Server with error */}
            <g transform="translate(100, 40)">
              {/* Server rack */}
              <rect x="0" y="0" width="100" height="120" rx="4" fill="#1a1f35" opacity="0.3" />
              <rect x="5" y="5" width="90" height="110" rx="2" fill="#667eea" opacity="0.1" />
              
              {/* Server panels */}
              <rect x="10" y="15" width="80" height="25" rx="2" fill="#667eea" opacity="0.3" />
              <rect x="10" y="50" width="80" height="25" rx="2" fill="#667eea" opacity="0.3" />
              <rect x="10" y="85" width="80" height="25" rx="2" fill="#ef4444" opacity="0.4" />
              
              {/* Indicator lights */}
              <circle cx="20" cy="27" r="3" fill="#10b981" />
              <circle cx="30" cy="27" r="3" fill="#10b981" />
              <circle cx="20" cy="62" r="3" fill="#10b981" />
              <circle cx="30" cy="62" r="3" fill="#10b981" />
              <circle cx="20" cy="97" r="3" fill="#ef4444" />
              <circle cx="30" cy="97" r="3" fill="#ef4444" />
              
              {/* Error lines */}
              <line x1="50" y1="97" x2="80" y2="97" stroke="#ef4444" strokeWidth="2" />
              <line x1="50" y1="103" x2="75" y2="103" stroke="#ef4444" strokeWidth="2" opacity="0.6" />
            </g>

            {/* Warning symbols */}
            <g transform="translate(60, 100)">
              <path d="M 0 10 L 5 0 L 10 10 Z" fill="#ef4444" opacity="0.6" />
              <text x="3" y="9" fill="#fff" fontSize="8" fontWeight="bold">!</text>
            </g>
            <g transform="translate(210, 80)">
              <path d="M 0 10 L 5 0 L 10 10 Z" fill="#ef4444" opacity="0.6" />
              <text x="3" y="9" fill="#fff" fontSize="8" fontWeight="bold">!</text>
            </g>
          </svg>
        </div>

        {/* Action Buttons */}
        <div className="error-actions">
          <button onClick={handleRefresh} className="error-btn secondary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 4v6h-6M1 20v-6h6" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            Try Again
          </button>
          <Link to="/" className="error-btn primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            Back to Home
          </Link>
        </div>

        {/* Error Details (for development) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="error-details">
            <details>
              <summary>Technical Details</summary>
              <div className="error-details-content">
                <p><strong>Error Type:</strong> Internal Server Error</p>
                <p><strong>Status Code:</strong> 500</p>
                <p><strong>Timestamp:</strong> {new Date().toISOString()}</p>
                <p><strong>Suggestion:</strong> Check backend logs or contact administrator</p>
              </div>
            </details>
          </div>
        )}

        {/* Help Section */}
        <div className="error-help">
          <p>If the problem persists, please:</p>
          <ul>
            <li>Check your internet connection</li>
            <li>Clear your browser cache</li>
            <li><Link to="/contact">Contact our support team</Link></li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ServerErrorPage;
