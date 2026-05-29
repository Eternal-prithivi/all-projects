import React from 'react';
import { Link } from 'react-router-dom';
import { FaTimesCircle } from 'react-icons/fa';
import '../styles/error-pages.css';

export default function BillingCancelPage() {
  return (
    <div className="error-page">
      <div className="error-container">
        <FaTimesCircle style={{ fontSize: '3rem', color: '#f1c40f', marginBottom: '1rem' }} />
        <h1 className="error-title">Payment cancelled</h1>
        <p className="error-description">
          No charge was made. You can try again anytime from the billing or pricing page.
        </p>
        <div className="error-actions">
          <Link to="/dashboard/pricing" className="error-btn primary">
            View plans
          </Link>
          <Link to="/pricing" className="error-btn secondary">
            Public pricing
          </Link>
        </div>
      </div>
    </div>
  );
}
