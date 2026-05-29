import React from 'react';
import { Link } from 'react-router-dom';
import { FaClock } from 'react-icons/fa';
import '../styles/error-pages.css';

export default function SessionExpiredPage() {
  return (
    <div className="error-page">
      <div className="error-container">
        <FaClock style={{ fontSize: '3rem', color: '#d4af37', marginBottom: '1rem' }} />
        <h1 className="error-title">Session expired</h1>
        <p className="error-description">
          For your security, you have been signed out. Please sign in again to continue.
        </p>
        <div className="error-actions">
          <Link to="/login" className="error-btn primary">
            Sign in
          </Link>
          <Link to="/" className="error-btn secondary">
            Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
