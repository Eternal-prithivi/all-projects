import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { FaEnvelopeOpenText } from 'react-icons/fa';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/verify-email.css';

import { apiUrl } from '../config/apiBase.js';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [state, setState] = useState(token ? 'loading' : 'pending');

  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${apiUrl('/auth/verify-email')}?token=${encodeURIComponent(token)}`,
          { method: 'POST' }
        );
        const body = await res.json().catch(() => ({}));
        if (!cancelled) {
          if (res.ok) setState('success');
          else setState('error');
          if (!res.ok && body?.detail) {
            setState('error');
          }
        }
      } catch {
        if (!cancelled) setState('error');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <MarketingPageLayout>
      <div className="verify-email-page">
        <div className="verify-email-card reveal-item">
          <FaEnvelopeOpenText className="verify-email-icon" />
          {state === 'loading' && (
            <>
              <h1>Verifying your email…</h1>
              <p>Please wait a moment.</p>
            </>
          )}
          {state === 'pending' && (
            <>
              <h1>Check your inbox</h1>
              <p>
                If you just registered, we sent a verification link to your email. Click the link to
                activate your account.
              </p>
            </>
          )}
          {state === 'success' && (
            <>
              <h1>Email verified</h1>
              <p>Your email is confirmed. You can sign in to Zenith now.</p>
            </>
          )}
          {state === 'error' && (
            <>
              <h1>Verification failed</h1>
              <p>
                This link may be invalid or expired. Register again or contact{' '}
                <a href="mailto:support@rajverse.me">support</a>.
              </p>
            </>
          )}
          <div className="verify-email-actions">
            <Link to="/login" className="verify-email-btn verify-email-btn--primary">
              Sign in
            </Link>
            <Link to="/register" className="verify-email-btn verify-email-btn--secondary">
              Create account
            </Link>
          </div>
        </div>
      </div>
    </MarketingPageLayout>
  );
}
