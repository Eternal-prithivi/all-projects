import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/error-pages.css';

const NotFoundPage = () => {
  const navigate = useNavigate();

  return (
    <div className="error-page">
      <div className="error-container">
        {/* Error Code */}
        <div className="error-code">404</div>

        {/* Error Title */}
        <h1 className="error-title">Page Not Found</h1>

        {/* Error Description */}
        <p className="error-description">
          The page you're looking for doesn't exist or has been moved.
          <br />
          Let's get you back on track.
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
            {/* Lost in space illustration */}
            <circle cx="150" cy="100" r="80" fill="#1a1f35" opacity="0.3" />
            <circle cx="150" cy="100" r="60" fill="#667eea" opacity="0.2" />
            <circle cx="150" cy="100" r="40" fill="#667eea" opacity="0.4" />
            
            {/* Floating astronaut */}
            <g transform="translate(130, 70)">
              {/* Helmet */}
              <circle cx="20" cy="20" r="18" fill="#667eea" opacity="0.8" />
              <circle cx="20" cy="20" r="12" fill="#1a1f35" opacity="0.6" />
              {/* Body */}
              <rect x="12" y="35" width="16" height="25" rx="8" fill="#667eea" opacity="0.8" />
              {/* Arms */}
              <rect x="3" y="40" width="12" height="4" rx="2" fill="#667eea" opacity="0.8" />
              <rect x="25" y="40" width="12" height="4" rx="2" fill="#667eea" opacity="0.8" />
            </g>

            {/* Stars */}
            <circle cx="50" cy="30" r="2" fill="#667eea" />
            <circle cx="250" cy="50" r="2" fill="#667eea" />
            <circle cx="80" cy="160" r="2" fill="#667eea" />
            <circle cx="220" cy="160" r="2" fill="#667eea" />
            <circle cx="270" cy="120" r="2" fill="#667eea" />
          </svg>
        </div>

        {/* Action Buttons */}
        <div className="error-actions">
          <button onClick={() => navigate(-1)} className="error-btn secondary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Go Back
          </button>
          <Link to="/" className="error-btn primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            Back to Home
          </Link>
        </div>

        {/* Quick Links */}
        <div className="error-suggestions">
          <p className="suggestions-title">Suggested Pages:</p>
          <div className="suggestions-links">
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/vm-cluster">VM Cluster</Link>
            <Link to="/storage">Storage</Link>
            <Link to="/contact">Contact Support</Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotFoundPage;
