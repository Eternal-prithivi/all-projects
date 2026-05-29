import React from 'react';
import { Link } from 'react-router-dom';
import { FaCheckCircle } from 'react-icons/fa';
import '../styles/error-pages.css';

export default function BillingSuccessPage() {
  return (
    <div className="error-page">
      <div className="error-container">
        <FaCheckCircle style={{ fontSize: '3rem', color: '#27ae60', marginBottom: '1rem' }} />
        <h1 className="error-title">Payment successful</h1>
        <p className="error-description">
          Thank you — your subscription is being activated. It may take a minute to reflect in billing.
        </p>
        <div className="error-actions">
          <Link to="/dashboard/billing" className="error-btn primary">
            View billing
          </Link>
          <Link to="/dashboard" className="error-btn secondary">
            Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
