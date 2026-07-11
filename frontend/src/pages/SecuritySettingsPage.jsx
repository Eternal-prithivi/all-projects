import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api';
import LoadingSpinner from '../components/LoadingSpinner';
import { SettingsPageSkeleton } from '../components/Skeletons.jsx';
import AuditLogPanel from '../components/security/AuditLogPanel';
import {
  getValidationErrorMessage,
  validatePasswordChangeForm,
} from '../utils/formValidation';
import '../styles/security-settings.css';
import TwoFADialog from '../components/TwoFADialog.jsx';
import PageHeader from '../components/ui/PageHeader.jsx';
import PageContainer from '../components/ui/PageContainer.jsx';
import { usePageRefresh } from '../hooks/usePageRefresh.js';
import AccountHubNav from '../components/account/AccountHubNav.jsx';
import PasswordRequirementsPanel from '../components/auth/PasswordRequirementsPanel.jsx';
import { useConfirm } from '../context/ConfirmContext.jsx';
import { useNotifications } from '../hooks/useNotifications.js';

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
  const { confirm } = useConfirm();
  const notifications = useNotifications();
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [activitySummary, setActivitySummary] = useState(null);
  const [showAuditPanel, setShowAuditPanel] = useState(false);
  const [showOtherSessions, setShowOtherSessions] = useState(false);
  const [showDisable2FA, setShowDisable2FA] = useState(false);
  const [disable2FACode, setDisable2FACode] = useState('');
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [passwordTouched, setPasswordTouched] = useState({
    currentPassword: false,
    newPassword: false,
    confirmPassword: false,
  });
  const [passwordSubmitAttempted, setPasswordSubmitAttempted] = useState(false);
  const [linkedAccounts, setLinkedAccounts] = useState({ google_linked: false, password_set: true });
  const [unlinkPassword, setUnlinkPassword] = useState('');
  const { runPageRefresh, pageRefreshing } = usePageRefresh();

  const passwordValidation = React.useMemo(
    () => validatePasswordChangeForm(passwordData),
    [passwordData]
  );

  const showPasswordFieldError = (field) =>
    (passwordSubmitAttempted || passwordTouched[field]) && passwordValidation.errors[field];

  const markPasswordFieldTouched = (field) => {
    setPasswordTouched((prev) => ({ ...prev, [field]: true }));
  };

  const fetchSecuritySettings = useCallback(async () => {
    try {
      setIsLoading(true);
      const [twoFAResponse, sessionsResponse, summaryResponse, linkedResponse] = await Promise.all([
        apiClient.get('/2fa/status-2fa'),
        apiClient.get('/profile/sessions'),
        apiClient.get('/profile/activity/summary', { params: { period_days: 30 } }),
        apiClient.get('/auth/linked-accounts'),
      ]);

      const enabled = twoFAResponse.data.enabled || false;
      setTwoFactorEnabled(enabled);
      try {
        sessionStorage.setItem(
          'cache_2faStatus',
          JSON.stringify({
            enabled,
            verified: twoFAResponse.data.verified || false,
            secret_exists: twoFAResponse.data.secret_exists || false,
          }),
        );
      } catch {
        /* ignore */
      }
      setSessions(sessionsResponse.data || []);
      setActivitySummary(summaryResponse.data);
      setLinkedAccounts(linkedResponse.data || { google_linked: false, password_set: true });
    } catch (error) {
      console.error('Failed to fetch security settings:', error);
      notifications.error('Failed to load security settings');
    } finally {
      setIsLoading(false);
    }
  }, [notifications]);

  useEffect(() => {
    fetchSecuritySettings();
  }, [fetchSecuritySettings]);

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
    setPasswordSubmitAttempted(true);

    if (!passwordValidation.isValid) {
      notifications.error(getValidationErrorMessage(passwordValidation.errors));
      return;
    }

    setIsSavingPassword(true);
    try {
      await apiClient.put('/profile/change-password', {
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword,
      });

      notifications.success('Password changed successfully');
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
      setPasswordTouched({
        currentPassword: false,
        newPassword: false,
        confirmPassword: false,
      });
      setPasswordSubmitAttempted(false);
      await refreshActivitySummary();
    } catch (error) {
      notifications.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setIsSavingPassword(false);
    }
  };

  const handleDownloadActivityCsv = async () => {
    try {
      const response = await apiClient.get('/profile/activity/export', {
        params: { period_days: 30 },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `zenith-activity-${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      notifications.success('Activity log downloaded');
    } catch (error) {
      notifications.error(error.response?.data?.detail || 'Failed to download activity log');
    }
  };

  const handleRevokeAllOtherSessions = async () => {
    if (otherSessions.length === 0) return;
    const ok = await confirm({
      title: 'Sign out all other devices',
      message: `Revoke ${otherSessions.length} other sign-in(s)? Those devices will need to log in again.`,
      confirmLabel: 'Sign out all',
      variant: 'danger',
    });
    if (!ok) return;
    try {
      const response = await apiClient.delete('/profile/sessions/others');
      notifications.success(response.data?.message || 'Other sessions revoked');
      const sessionsResponse = await apiClient.get('/profile/sessions');
      setSessions(sessionsResponse.data || []);
      setShowOtherSessions(false);
      await refreshActivitySummary();
    } catch (error) {
      notifications.error(error.response?.data?.detail || 'Failed to revoke sessions');
    }
  };

  const handleUnlinkGoogle = async () => {
    if (!unlinkPassword.trim()) {
      notifications.error('Enter your password to unlink Google sign-in');
      return;
    }
    try {
      await apiClient.post('/auth/linked-accounts/google/unlink', {
        current_password: unlinkPassword,
      });
      notifications.success('Google sign-in unlinked');
      setUnlinkPassword('');
      setLinkedAccounts((prev) => ({ ...prev, google_linked: false }));
      await refreshActivitySummary();
    } catch (error) {
      notifications.error(error.response?.data?.detail || 'Failed to unlink Google');
    }
  };

  const handleToggle2FA = () => {
    if (twoFactorEnabled) {
      setDisable2FACode('');
      setShowDisable2FA(true);
      return;
    }
    navigate('/dashboard/security');
    notifications.info('Complete 2FA setup on the Security vault page');
  };

  const handleConfirmDisable2FA = async () => {
    const code = disable2FACode.trim();
    if (code.length < 6) {
      notifications.error('Enter the 6-digit code from your authenticator app.');
      return;
    }
    try {
      await apiClient.post('/2fa/disable-2fa', { code });
      setTwoFactorEnabled(false);
      setShowDisable2FA(false);
      setDisable2FACode('');
      notifications.success('Two-factor authentication disabled');
      await refreshActivitySummary();
    } catch (error) {
      notifications.error(error.response?.data?.detail || 'Failed to update 2FA settings');
    }
  };

  useEffect(() => {
    if (!showDisable2FA) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [showDisable2FA]);

  const handleTerminateSession = async (sessionId) => {
    const ok = await confirm({
      title: 'Revoke sign-in',
      message: 'Revoke this sign-in? That device will need to log in again.',
      confirmLabel: 'Revoke sign-in',
      variant: 'danger',
    });
    if (!ok) return;

    try {
      await apiClient.delete(`/profile/sessions/${sessionId}`);
      notifications.success('Sign-in revoked');
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      await refreshActivitySummary();
    } catch (error) {
      notifications.error(error.response?.data?.detail || 'Failed to revoke sign-in');
    }
  };

  const currentSession = sessions.find((s) => s.current);
  const otherSessions = sessions.filter((s) => !s.current);

  if (isLoading) {
    return (
      <PageContainer variant="config" className="security-settings-page">
        <PageHeader
          kicker="Account security"
          title="Security Settings"
          subtitle="Password, two-factor authentication, and sign-in overview"
        />
        <SettingsPageSkeleton />
      </PageContainer>
    );
  }

  const closeDisable2FA = () => {
    setShowDisable2FA(false);
    setDisable2FACode('');
  };

  return (
    <PageContainer variant="config" className="security-settings-page">
      <TwoFADialog
        open={showDisable2FA}
        onClose={closeDisable2FA}
        titleId="disable-2fa-title"
        title="Disable two-factor authentication"
        kicker="Account security"
        variant="danger"
        description="Enter the 6-digit code from your authenticator app to confirm you want to turn off 2FA."
        primaryLabel="Disable 2FA"
        primaryVariant="danger"
        onPrimary={handleConfirmDisable2FA}
        cancelLabel="Cancel"
        onCancel={closeDisable2FA}
      >
        <input
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder="000000"
          value={disable2FACode}
          onChange={(e) => setDisable2FACode(e.target.value.replace(/\D/g, ''))}
          maxLength={6}
          className="twofa-input"
          aria-label="2FA code to disable"
        />
      </TwoFADialog>
      <PageHeader
        kicker="Account security"
        title="Security Settings"
        subtitle="Password, two-factor authentication, and sign-in overview"
        onRefresh={() =>
          runPageRefresh(fetchSecuritySettings, {
            loadingMessage: 'Refreshing security settings…',
            successMessage: 'Security settings page refreshed.',
            errorMessage: 'Failed to refresh security settings.',
          })
        }
        refreshing={pageRefreshing || isLoading}
      />

      <AccountHubNav />

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
                onBlur={() => markPasswordFieldTouched('currentPassword')}
                required
                className="form-input"
                aria-invalid={!!showPasswordFieldError('currentPassword')}
                aria-describedby={showPasswordFieldError('currentPassword') ? 'current-password-error' : undefined}
              />
              {showPasswordFieldError('currentPassword') && (
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
                onBlur={() => markPasswordFieldTouched('newPassword')}
                required
                minLength={8}
                placeholder="Create a strong password"
                className="form-input"
                aria-invalid={!!showPasswordFieldError('newPassword')}
                aria-describedby="security-new-password-requirements"
              />
              <PasswordRequirementsPanel
                password={passwordData.newPassword}
                id="security-new-password-requirements"
              />
              {showPasswordFieldError('newPassword') && (
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
                onBlur={() => markPasswordFieldTouched('confirmPassword')}
                required
                className="form-input"
                aria-invalid={!!showPasswordFieldError('confirmPassword')}
                aria-describedby={showPasswordFieldError('confirmPassword') ? 'confirm-password-error' : undefined}
              />
              {showPasswordFieldError('confirmPassword') && (
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
        <h3>Sign-in methods</h3>
        <div className="security-item">
          <div className="security-info">
            <h4>Password</h4>
            <p>{linkedAccounts.password_set ? 'Password sign-in enabled' : 'No password set'}</p>
          </div>
        </div>
        <div className="security-item">
          <div className="security-info">
            <h4>Google</h4>
            <p>{linkedAccounts.google_linked ? 'Linked for single sign-on' : 'Not linked'}</p>
          </div>
          {linkedAccounts.google_linked && (
            <div className="linked-account-unlink">
              <input
                type="password"
                className="form-input"
                placeholder="Current password"
                value={unlinkPassword}
                onChange={(e) => setUnlinkPassword(e.target.value)}
                autoComplete="current-password"
              />
              <button type="button" className="btn-danger-outline" onClick={handleUnlinkGoogle}>
                Unlink Google
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="security-card security-card--full">
        <h3>Passkeys</h3>
        <p className="security-card-subtitle">
          Passwordless sign-in with Face ID, Touch ID, or a security key — coming in a future update.
        </p>
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
              className="btn-danger-outline sign-out-others-btn"
              onClick={handleRevokeAllOtherSessions}
            >
              Sign out all other devices ({otherSessions.length})
            </button>
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
            <button
              type="button"
              className="btn-secondary-outline audit-view-all-btn"
              onClick={handleDownloadActivityCsv}
            >
              Download activity log (CSV)
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
    </PageContainer>
  );
};

export default SecuritySettingsPage;
