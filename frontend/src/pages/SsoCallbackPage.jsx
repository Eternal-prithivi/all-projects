import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import '../styles/error-pages.css';

export default function SsoCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setError('Missing sign-in token. Try logging in again.');
      return;
    }
    login(token);
    navigate('/dashboard', { replace: true });
  }, [searchParams, login, navigate]);

  if (error) {
    return (
      <div className="error-page">
        <div className="error-container">
          <h1 className="error-title">SSO sign-in failed</h1>
          <p className="error-description">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="error-page">
      <div className="error-container">
        <p className="error-description">Completing sign-in…</p>
      </div>
    </div>
  );
}
