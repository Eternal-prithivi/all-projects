import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '../api';
import { useAuth } from '../context/AuthContext.jsx';
import MarketingPageLayout from '../components/layout/MarketingPageLayout.jsx';
import '../styles/verify-email.css';

export default function AcceptInvitePage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [accepting, setAccepting] = useState(false);

  useEffect(() => {
    if (!token) return;
    apiClient
      .get(`/organizations/invites/${token}`)
      .then((res) => setPreview(res.data))
      .catch(() => setError('This invite is invalid or has expired.'));
  }, [token]);

  const accept = async () => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: `/invite/${token}` } });
      return;
    }
    setAccepting(true);
    try {
      await apiClient.post(`/organizations/invites/${token}/accept`);
      navigate('/dashboard/team');
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not accept invite');
    } finally {
      setAccepting(false);
    }
  };

  return (
    <MarketingPageLayout>
      <div className="verify-email-page">
        <div className="verify-email-card">
          {error && (
            <>
              <h1>Invite unavailable</h1>
              <p>{error}</p>
            </>
          )}
          {preview && !error && (
            <>
              <h1>Join {preview.org_name}</h1>
              <p>
                You have been invited as <strong>{preview.role}</strong> for{' '}
                <strong>{preview.email}</strong>.
              </p>
              <div className="verify-email-actions">
                <button
                  type="button"
                  className="verify-email-btn verify-email-btn--primary"
                  onClick={accept}
                  disabled={accepting}
                >
                  {accepting ? 'Joining…' : isAuthenticated ? 'Accept invite' : 'Sign in to accept'}
                </button>
                {!isAuthenticated && (
                  <Link to="/register" className="verify-email-btn verify-email-btn--secondary">
                    Create account
                  </Link>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </MarketingPageLayout>
  );
}
