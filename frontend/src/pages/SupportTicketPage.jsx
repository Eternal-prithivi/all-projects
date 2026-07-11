import React, { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import SupportThreadPanel from '../components/support/SupportThreadPanel.jsx';
import { useSupportThreadPoll } from '../hooks/useSupportThreadPoll.js';
import { apiUrl } from '../config/apiBase.js';
import { showBannerToast } from '../utils/notifications.js';
import '../styles/support-tickets.css';

const GUEST_TOKEN_KEY = 'zenith_guest_ticket_token';

function SupportTicketPage() {
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState('lookup');
  const [referenceCode, setReferenceCode] = useState(searchParams.get('ref') || '');
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [guestToken, setGuestToken] = useState(
    () => sessionStorage.getItem(GUEST_TOKEN_KEY) || ''
  );
  const [thread, setThread] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadThread = useCallback(async (ref, token, { silent = false } = {}) => {
    const res = await fetch(apiUrl(`/support/guest/tickets/${encodeURIComponent(ref)}`), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Could not load ticket');
    }
    const data = await res.json();
    if (!silent) setThread(data);
    else setThread(data);
    return data;
  }, []);

  useEffect(() => {
    const ref = searchParams.get('ref');
    if (ref) setReferenceCode(ref);
  }, [searchParams]);

  useEffect(() => {
    if (!guestToken || !referenceCode) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await loadThread(referenceCode, guestToken);
        if (!cancelled) {
          setThread(data);
          setStep('thread');
        }
      } catch {
        sessionStorage.removeItem(GUEST_TOKEN_KEY);
        setGuestToken('');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [guestToken, referenceCode, loadThread]);

  const refreshThread = useCallback(() => {
    if (guestToken && referenceCode) {
      loadThread(referenceCode, guestToken, { silent: true }).catch(() => {});
    }
  }, [guestToken, referenceCode, loadThread]);

  useSupportThreadPoll(refreshThread, {
    enabled: step === 'thread' && Boolean(guestToken && referenceCode),
  });

  const handleRequestOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(apiUrl('/support/guest/request-otp'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reference_code: referenceCode.trim().toUpperCase(),
          email: email.trim(),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Request failed');
      }
      showBannerToast('success', 'Verification code sent — check your email.');
      setStep('otp');
    } catch (err) {
      showBannerToast('error', err.message || 'Could not send code');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(apiUrl('/support/guest/verify-otp'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reference_code: referenceCode.trim().toUpperCase(),
          email: email.trim(),
          code: otp.trim(),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Invalid code');
      }
      const data = await res.json();
      sessionStorage.setItem(GUEST_TOKEN_KEY, data.guest_token);
      setGuestToken(data.guest_token);
      setThread(data);
      setStep('thread');
      showBannerToast('success', 'Verified — you can view your ticket.');
    } catch (err) {
      showBannerToast('error', err.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (body) => {
    const res = await fetch(
      apiUrl(`/support/guest/tickets/${encodeURIComponent(referenceCode)}/messages`),
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${guestToken}`,
        },
        body: JSON.stringify({ body }),
      }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Reply failed');
    }
    const data = await res.json();
    setThread(data);
  };

  const ticket = thread?.ticket;
  const messages = thread?.messages || [];

  return (
    <MarketingPageLayout>
      <div className="support-ticket-page">
        <p className="marketing-page-hero__eyebrow">Support</p>
        <h1>Track your request</h1>
        <p className="lead">
          Enter your reference number and email to view your conversation with Zenith Support.
        </p>

        {step === 'lookup' && (
          <div className="support-card">
            <form className="support-form" onSubmit={handleRequestOtp}>
              <div className="form-group">
                <label htmlFor="ref">Reference number</label>
                <input
                  id="ref"
                  value={referenceCode}
                  onChange={(e) => setReferenceCode(e.target.value)}
                  placeholder="ZN-12345678"
                  required
                  autoComplete="off"
                />
              </div>
              <div className="form-group">
                <label htmlFor="email">Email used on the request</label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                />
              </div>
              <button type="submit" className="support-btn" disabled={loading}>
                {loading ? 'Sending…' : 'Send verification code'}
              </button>
            </form>
          </div>
        )}

        {step === 'otp' && (
          <div className="support-card">
            <form className="support-form" onSubmit={handleVerifyOtp}>
              <p style={{ marginBottom: '1rem', fontSize: '0.9rem' }}>
                We sent a 6-digit code to <strong>{email}</strong>. It expires in 15 minutes.
              </p>
              <div className="form-group">
                <label htmlFor="otp">Verification code</label>
                <input
                  id="otp"
                  className="support-otp-input"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000000"
                  inputMode="numeric"
                  maxLength={6}
                  required
                />
              </div>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button type="submit" className="support-btn" disabled={loading || otp.length !== 6}>
                  {loading ? 'Verifying…' : 'Verify & view ticket'}
                </button>
                <button
                  type="button"
                  className="support-btn support-btn--ghost"
                  onClick={() => setStep('lookup')}
                >
                  Back
                </button>
              </div>
            </form>
          </div>
        )}

        {step === 'thread' && ticket && (
          <div className="support-card support-card--chat">
            <SupportThreadPanel
              ticket={ticket}
              messages={messages}
              onSend={handleSend}
            />
            <p className="support-guest-footer-link">
              Need a new request? <Link to="/contact">Contact us</Link>
            </p>
          </div>
        )}
      </div>
    </MarketingPageLayout>
  );
}

export default SupportTicketPage;
