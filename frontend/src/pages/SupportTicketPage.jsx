import React, { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import { apiUrl } from '../config/apiBase.js';
import '../styles/support-tickets.css';

const GUEST_TOKEN_KEY = 'zenith_guest_ticket_token';

function formatDate(value) {
  if (!value) return '';
  return new Date(value).toLocaleString();
}

function SupportTicketPage() {
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState('lookup');
  const [referenceCode, setReferenceCode] = useState(
    searchParams.get('ref') || ''
  );
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [guestToken, setGuestToken] = useState(
    () => sessionStorage.getItem(GUEST_TOKEN_KEY) || ''
  );
  const [thread, setThread] = useState(null);
  const [reply, setReply] = useState('');
  const [loading, setLoading] = useState(false);

  const loadThread = useCallback(async (ref, token) => {
    const res = await fetch(apiUrl(`/support/guest/tickets/${encodeURIComponent(ref)}`), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Could not load ticket');
    }
    return res.json();
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
      toast.success('Verification code sent — check your email.');
      setStep('otp');
    } catch (err) {
      toast.error(err.message || 'Could not send code');
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
      toast.success('Verified — you can view your ticket.');
    } catch (err) {
      toast.error(err.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReply = async (e) => {
    e.preventDefault();
    if (!reply.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(
        apiUrl(`/support/guest/tickets/${encodeURIComponent(referenceCode)}/messages`),
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${guestToken}`,
          },
          body: JSON.stringify({ body: reply.trim() }),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Reply failed');
      }
      const data = await res.json();
      setThread(data);
      setReply('');
      toast.success('Reply sent');
    } catch (err) {
      toast.error(err.message || 'Could not send reply');
    } finally {
      setLoading(false);
    }
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
          <div className="support-card">
            <div className="support-thread-header">
              <div>
                <span className="support-ref">{ticket.reference_code}</span>
                <h2 style={{ margin: '0.35rem 0 0', fontSize: '1.1rem' }}>
                  {ticket.subject || ticket.category}
                </h2>
              </div>
              <span className={`support-status-pill support-status-pill--${ticket.status}`}>
                {ticket.status?.replace(/_/g, ' ')}
              </span>
            </div>

            <div className="support-messages" role="log" aria-live="polite">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`support-bubble support-bubble--${msg.author_type}`}
                >
                  <div className="support-bubble-meta">
                    {msg.author_name} · {formatDate(msg.created_at)}
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.body}</div>
                </div>
              ))}
            </div>

            {ticket.status !== 'closed' && ticket.status !== 'resolved' && (
              <form className="support-form" onSubmit={handleReply}>
                <div className="form-group">
                  <label htmlFor="reply">Your reply</label>
                  <textarea
                    id="reply"
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    placeholder="Type your message…"
                    required
                  />
                </div>
                <button type="submit" className="support-btn" disabled={loading || !reply.trim()}>
                  {loading ? 'Sending…' : 'Send reply'}
                </button>
              </form>
            )}

            <p style={{ marginTop: '1.25rem', fontSize: '0.85rem', opacity: 0.7 }}>
              Need a new request? <Link to="/contact">Contact us</Link>
            </p>
          </div>
        )}
      </div>
    </MarketingPageLayout>
  );
}

export default SupportTicketPage;
