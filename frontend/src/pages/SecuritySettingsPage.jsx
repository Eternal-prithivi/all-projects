import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { apiClient } from '../api';
import LoadingSpinner from '../components/LoadingSpinner';
import AuditLogPanel from '../components/security/AuditLogPanel';
import {
  getValidationErrorMessage,
  validatePasswordChangeForm,
} from '../utils/formValidation';
import '../styles/security-settings.css';

const formatRelativeTime = (timestamp) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours} hr ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  return date.toLocaleString();
};

const getAuditIcon = (category) => {
  const icons = { auth: '🔐', security: '🛡️', account: '👤', other: '📋' };
  return icons[category] || icons.other;
};

const SecuritySettingsPage = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [activitySummary, setActivitySummary] = useState(null);
  const [showAuditPanel, setShowAuditPanel] = useState(false);
  const [showOtherSessions, setShowOtherSessions] = useState(false);
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });

  const passwordValidation = React.useMemo(
    () => validatePasswordChangeForm(passwordData),
    [passwordData]
  );

  useEffect(() => {
    fetchSecuritySettings();
  }, []);

  const fetchSecuritySettings = async () => {
    try {
      setIsLoading(true);
      const [twoFAResponse, sessionsResponse, summaryResponse] = await Promise.all([
        apiClient.get('/2fa/status-2fa'),
        apiClient.get('/profile/sessions'),
        apiClient.get('/profile/activity/summary', { params: { period_days: 30 } }),
      ]);

      setTwoFactorEnabled(twoFAResponse.data.enabled || false);
      setSessions(sessionsResponse.data || []);
      setActivitySummary(summaryResponse.data);
    } catch (error) {
      console.error('Failed to fetch security settings:', error);
      toast.error('Failed to load security settings');
    } finally {
      setIsLoading(false);
    }
  };

  const refreshActivitySummary = async () => {
    try {
      const summaryResponse = await apiClient.get('/profile/activity/summary', {
        params: { period_days: 30 },
      });
      setActivitySummary(summaryResponse.data);
    } catch {
      /* non-blocking */
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();

    if (!passwordValidation.isValid) {
      toast.error(getValidationErrorMessage(passwordValidation.errors));
      return;
    }

    setIsSavingPassword(true);
    try {
      await apiClient.put('/profile/change-password', {
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword,
      });

      toast.success('Password changed successfully');
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
      await refreshActivitySummary();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setIsSavingPassword(false);
    }
  };

  const handleToggle2FA = async () => {
    try {
      if (twoFactorEnabled) {
        await apiClient.post('/2fa/disable-2fa');
        setTwoFactorEnabled(false);
        toast.success('Two-factor authentication disabled');
        await refreshActivitySummary();
      } else {
        navigate('/dashboard/security');
        toast.info('Complete 2FA setup on the Security vault page');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update 2FA settings');
    }
  };

  const handleTerminateSession = async (sessionId) => {
    if (!window.confirm('Revoke this sign-in? That device will need to log in again.')) {
      return;
    }

    try {
      await apiClient.delete(`/profile/sessions/${sessionId}`);
      toast.success('Sign-in revoked');
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      await refreshActivitySummary();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to revoke sign-in');
    }
  };

  const currentSession = sessions.find((s) => s.current);
  const otherSessions = sessions.filter((s) => !s.current);

  if (isLoading) {
    return <LoadingSpinner size="large" text="Loading security settings..." />;
  }

  return (
    <div className="security-settings-page">
      <div className="security-header">
        <h2>Security Settings</h2>
        <p>Password, two-factor authentication, and sign-in overview</p>
      </div>

      <div className="security-bento">
        <div className="security-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2zm3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z" />
            </svg>
            Change Password
          </h3>
          <form onSubmit={handlePasswordChange} className="password-form">
            <div className="form-group">
              <label htmlFor="current-password">Current password</label>
              <input
                id="current-password"
                type="password"
                autoComplete="current-password"
                value={passwordData.currentPassword}
                onChange={(e) => setPasswordData({ ...passwordData, currentPassword: e.target.value })}
                required
                className="form-input"
                aria-invalid={!!passwordValidation.errors.currentPassword}
                aria-describedby={passwordValidation.errors.currentPassword ? 'current-password-error' : undefined}
              />
              {passwordValidation.errors.currentPassword && (
                <p id="current-password-error" className="form-field-error">{passwordValidation.errors.currentPassword}</p>
              )}
            </div>
            <div className="form-group">
              <label htmlFor="new-password">New password</label>
              <input
                id="new-password"
                type="password"
                autoComplete="new-password"
                value={passwordData.newPassword}
                onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
                required
                minLength={8}
                className="form-input"
                aria-invalid={!!passwordValidation.errors.newPassword}
                aria-describedby={passwordValidation.errors.newPassword ? 'new-password-error' : undefined}
              />
              <small className="hint-text">At least 8 characters</small>
              {passwordValidation.errors.newPassword && (
                <p id="new-password-error" className="form-field-error">{passwordValidation.errors.newPassword}</p>
              )}
            </div>
            <div className="form-group">
              <label htmlFor="confirm-password">Confirm new password</label>
              <input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                value={passwordData.confirmPassword}
                onChange={(e) => setPasswordData({ ...passwordData, confirmPassword: e.target.value })}
                required
                className="form-input"
                aria-invalid={!!passwordValidation.errors.confirmPassword}
                aria-describedby={passwordValidation.errors.confirmPassword ? 'confirm-password-error' : undefined}
              />
              {passwordValidation.errors.confirmPassword && (
                <p id="confirm-password-error" className="form-field-error">{passwordValidation.errors.confirmPassword}</p>
              )}
            </div>
            <button type="submit" className="btn-primary" disabled={isSavingPassword || !passwordValidation.isValid}>
              {isSavingPassword ? 'Saving…' : 'Update password'}
            </button>
          </form>
        </div>

        <div className="security-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M5.338 1.59a61.44 61.44 0 0 0-2.837.856.481.481 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188a10.725 10.725 0 0 0 2.287 2.233c.346.244.652.42.893.533.12.057.218.095.293.118a.55.55 0 0 0 .101.025.615.615 0 0 0 .1-.025c.076-.023.174-.061.294-.118.24-.113.547-.29.893-.533a10.726 10.726 0 0 0 2.287-2.233c1.527-1.997 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39c-.651-.213-1.75-.56-2.837-.855C9.552 1.29 8.531 1.067 8 1.067c-.53 0-1.552.223-2.662.524z" />
            </svg>
            Two-Factor Authentication
          </h3>
          <div className="security-item">
            <div className="security-info">
              <h4>Authenticator app (TOTP)</h4>
              <p>Required for the secure file vault. Use Google Authenticator or a similar app.</p>
              <span className={`status-badge ${twoFactorEnabled ? 'enabled' : 'disabled'}`}>
                {twoFactorEnabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <button
              type="button"
              className={twoFactorEnabled ? 'btn-danger-outline' : 'btn-primary'}
              onClick={handleToggle2FA}
            >
              {twoFactorEnabled ? 'Disable 2FA' : 'Set up 2FA'}
            </button>
          </div>
        </div>
      </div>

      <div className="security-card security-card--full">
        <h3>
          <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d="M0 1.5A.5.5 0 0 1 .5 1H2a.5.5 0 0 1 .485.379L2.89 3H14.5a.5.5 0 0 1 .491.592l-1.5 8A.5.5 0 0 1 13 12H4a.5.5 0 0 1-.491-.408L2.01 3.607 1.61 2H.5a.5.5 0 0 1-.5-.5z" />
          </svg>
          Sign-in &amp; activity
        </h3>
        <p className="security-card-subtitle">
          Your current device and a short summary of account activity. Full history is available on demand.
        </p>

        {currentSession && (
          <div className="current-device-card">
            <div className="current-device-icon" aria-hidden="true">💻</div>
            <div>
              <h4>This device — {currentSession.device}</h4>
              <p>Location: {currentSession.location}</p>
              <p>IP: {currentSession.ip}</p>
              {currentSession.device_fingerprint_short && (
                <p>Device ID: {currentSession.device_fingerprint_short}</p>
              )}
              <p>Last active: {formatRelativeTime(currentSession.last_active)}</p>
              <span className="current-badge">Active now</span>
            </div>
          </div>
        )}

        {otherSessions.length > 0 && (
          <>
            <button
              type="button"
              className="other-sessions-toggle"
              onClick={() => setShowOtherSessions((v) => !v)}
            >
              {showOtherSessions
                ? 'Hide other sign-ins'
                : `Manage ${otherSessions.length} other sign-in${otherSessions.length > 1 ? 's' : ''}`}
            </button>
            {showOtherSessions &&
              otherSessions.map((session) => (
                <div key={session.id} className="session-item">
                  <div>
                    <h4>{session.device}</h4>
                    <p className="session-meta">
                      {session.location} · IP {session.ip}
                      {session.device_fingerprint_short
                        ? ` · Device ${session.device_fingerprint_short}`
                        : ""}{" "}
                      · {formatRelativeTime(session.last_active)}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn-danger-outline"
                    onClick={() => handleTerminateSession(session.id)}
                  >
                    Revoke
                  </button>
                </div>
              ))}
          </>
        )}

        {activitySummary && (
          <div className="activity-summary-block">
            <div className="activity-stats">
              <div className="activity-stat">
                <span className="activity-stat-value">{activitySummary.total_events}</span>
                <span className="activity-stat-label">Events (30 days)</span>
              </div>
              <div className="activity-stat">
                <span className="activity-stat-value">{activitySummary.sign_ins}</span>
                <span className="activity-stat-label">Sign-ins</span>
              </div>
              <div className="activity-stat">
                <span className="activity-stat-value">{activitySummary.security_events}</span>
                <span className="activity-stat-label">Security</span>
              </div>
            </div>

            {activitySummary.recent?.length > 0 && (
              <div className="recent-activity-preview">
                <h4 className="recent-activity-title">Recent</h4>
                <ul className="recent-activity-list">
                  {activitySummary.recent.map((activity, index) => (
                    <li key={`${activity.timestamp}-${index}`} className="recent-activity-item">
                      <span className="recent-activity-icon" aria-hidden="true">
                        {getAuditIcon(activity.category)}
                      </span>
                      <div className="recent-activity-text">
                        <strong>{activity.action}</strong>
                        <span>{formatRelativeTime(activity.timestamp)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <button
              type="button"
              className="btn-secondary-outline audit-view-all-btn"
              onClick={() => setShowAuditPanel(true)}
            >
              View full activity history
            </button>
          </div>
        )}
      </div>

      {showAuditPanel && (
        <div className="audit-panel-overlay" onClick={() => setShowAuditPanel(false)}>
          <div className="audit-panel-wrap" onClick={(e) => e.stopPropagation()}>
            <AuditLogPanel onClose={() => setShowAuditPanel(false)} />
          </div>
        </div>
      )}
    </div>
  );
};

export default SecuritySettingsPage;
