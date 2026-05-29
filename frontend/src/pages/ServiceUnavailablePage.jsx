import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/error-pages.css';

const ServiceUnavailablePage = () => {
  return (
    <div className="error-page">
      <div className="error-container">
        <div className="error-code">503</div>
        <h1 className="error-title">Scheduled Maintenance</h1>
        <p className="error-description">
          Zenith is temporarily offline while we upgrade infrastructure.
          <br />
          Please check back soon or contact support if you need help.
        </p>

        <div className="error-actions">
          <Link to="/" className="error-btn primary">
            Back to Home
          </Link>
          <Link to="/contact" className="error-btn secondary">
            Contact Support
          </Link>
        </div>

        <div className="error-help">
          <p>Recommended:</p>
          <ul>
            <li>Retry in a few minutes</li>
            <li>
              Check our <Link to="/status">status page</Link> or announcements
            </li>
            <li>Reach out if you have urgent needs</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ServiceUnavailablePage;
