import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import api from '../api';
import '../styles/error-pages.css';

export default function SsoCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState('');

  useEffect(() => {
    const legacyToken = searchParams.get('token');
    const code = searchParams.get('code');

    (async () => {
      try {
        if (code) {
          await api.post('/auth/sso/exchange', { code });
          await login();
          navigate('/dashboard', { replace: true });
          return;
        }
        if (legacyToken) {
          await login();
          navigate('/dashboard', { replace: true });
          return;
        }
        setError('Missing sign-in code. Try logging in again.');
      } catch {
        setError('SSO sign-in failed. Try logging in again.');
      }
    })();
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
