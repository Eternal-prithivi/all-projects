import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { apiClient } from '../api';
import LoadingSpinner from '../components/LoadingSpinner';
import '../styles/security-settings.css';

const SecuritySettingsPage = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [activities, setActivities] = useState([]);
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });

  useEffect(() => {
    fetchSecuritySettings();
  }, []);

  const fetchSecuritySettings = async () => {
    try {
      setIsLoading(true);
      // Fetch 2FA status
      const twoFAResponse = await apiClient.get('/2fa/status-2fa');
      setTwoFactorEnabled(twoFAResponse.data.enabled || false);
      
      // Fetch active sessions
      const sessionsResponse = await apiClient.get('/profile/sessions');
      setSessions(sessionsResponse.data || []);
      
      // Fetch activity log
      const activityResponse = await apiClient.get('/profile/activity');
      setActivities(activityResponse.data || []);
    } catch (error) {
      console.error('Failed to fetch security settings:', error);
      toast.error('Failed to load security settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }

    if (passwordData.newPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    try {
      await apiClient.put('/profile/change-password', {
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword
      });
      
      toast.success('Password changed successfully!');
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to change password');
    }
  };

  const handleToggle2FA = async () => {
    try {
      if (twoFactorEnabled) {
        // Disable 2FA
        await apiClient.post('/2fa/disable-2fa');
        setTwoFactorEnabled(false);
        toast.success('Two-factor authentication disabled');
      } else {
        // Enable 2FA - redirect to setup
        const response = await apiClient.post('/2fa/enable-2fa');
        if (response.data.qr_code) {
          // Show QR code modal or redirect to 2FA setup
          toast.info('Please complete 2FA setup in Security page');
          window.location.href = '/dashboard/security';
        }
      }
    } catch (error) {
      toast.error('Failed to update 2FA settings');
    }
  };

  const handleTerminateSession = async (sessionId) => {
    if (!window.confirm('Are you sure you want to terminate this session?')) {
      return;
    }

    try {
      await apiClient.delete(`/profile/sessions/${sessionId}`);
      toast.success('Session terminated successfully');
      setSessions(sessions.filter(s => s.id !== sessionId));
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to terminate session';
      toast.error(message);
    }
  };

  if (isLoading) {
    return <LoadingSpinner size="large" text="Loading security settings..." />;
  }

  return (
    <div className="security-settings-page">
      <div className="security-header">
        <h2>Security Settings</h2>
        <p>Manage your account security and authentication methods</p>
      </div>

      <div className="security-content">
        {/* Change Password */}
        <div className="security-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2zm3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/>
            </svg>
            Change Password
          </h3>
          <form onSubmit={handlePasswordChange} className="password-form">
            <div className="form-group">
              <label>Current Password</label>
              <input
                type="password"
                value={passwordData.currentPassword}
                onChange={(e) => setPasswordData({...passwordData, currentPassword: e.target.value})}
                required
                className="form-input"
              />
            </div>
            <div className="form-group">
              <label>New Password</label>
              <input
                type="password"
                value={passwordData.newPassword}
                onChange={(e) => setPasswordData({...passwordData, newPassword: e.target.value})}
                required
                minLength={8}
                className="form-input"
              />
              <small className="hint-text">Must be at least 8 characters</small>
            </div>
            <div className="form-group">
              <label>Confirm New Password</label>
              <input
                type="password"
                value={passwordData.confirmPassword}
                onChange={(e) => setPasswordData({...passwordData, confirmPassword: e.target.value})}
                required
                className="form-input"
              />
            </div>
            <button type="submit" className="btn-primary">Change Password</button>
          </form>
        </div>

        {/* Two-Factor Authentication */}
        <div className="security-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M5.338 1.59a61.44 61.44 0 0 0-2.837.856.481.481 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188a10.725 10.725 0 0 0 2.287 2.233c.346.244.652.42.893.533.12.057.218.095.293.118a.55.55 0 0 0 .101.025.615.615 0 0 0 .1-.025c.076-.023.174-.061.294-.118.24-.113.547-.29.893-.533a10.726 10.726 0 0 0 2.287-2.233c1.527-1.997 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39c-.651-.213-1.75-.56-2.837-.855C9.552 1.29 8.531 1.067 8 1.067c-.53 0-1.552.223-2.662.524zM5.072.56C6.157.265 7.31 0 8 0s1.843.265 2.928.56c1.11.3 2.229.655 2.887.87a1.54 1.54 0 0 1 1.044 1.262c.596 4.477-.787 7.795-2.465 9.99a11.775 11.775 0 0 1-2.517 2.453 7.159 7.159 0 0 1-1.048.625c-.28.132-.581.24-.829.24s-.548-.108-.829-.24a7.158 7.158 0 0 1-1.048-.625 11.777 11.777 0 0 1-2.517-2.453C1.928 10.487.545 7.169 1.141 2.692A1.54 1.54 0 0 1 2.185 1.43 62.456 62.456 0 0 1 5.072.56z"/>
              <path d="M10.854 5.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 7.793l2.646-2.647a.5.5 0 0 1 .708 0z"/>
            </svg>
            Two-Factor Authentication
          </h3>
          <div className="security-group">
            <div className="security-item">
              <div className="security-info">
                <h4>Enable 2FA</h4>
                <p>Add an extra layer of security to your account with two-factor authentication</p>
                <span className={`status-badge ${twoFactorEnabled ? 'enabled' : 'disabled'}`}>
                  {twoFactorEnabled ? '✓ Enabled' : '✗ Disabled'}
                </span>
              </div>
              <button 
                className={twoFactorEnabled ? 'btn-danger-outline' : 'btn-primary'}
                onClick={handleToggle2FA}
              >
                {twoFactorEnabled ? 'Disable 2FA' : 'Enable 2FA'}
              </button>
            </div>
          </div>
        </div>

        {/* Active Sessions */}
        <div className="security-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M0 1.5A.5.5 0 0 1 .5 1H2a.5.5 0 0 1 .485.379L2.89 3H14.5a.5.5 0 0 1 .491.592l-1.5 8A.5.5 0 0 1 13 12H4a.5.5 0 0 1-.491-.408L2.01 3.607 1.61 2H.5a.5.5 0 0 1-.5-.5zM5 12a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm7 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm-7 1a1 1 0 1 1 0 2 1 1 0 0 1 0-2zm7 0a1 1 0 1 1 0 2 1 1 0 0 1 0-2z"/>
            </svg>
            Active Sessions
          </h3>
          <div className="security-group">
            <p className="info-text">Manage devices currently signed in to your account</p>
            {sessions.length > 0 ? (
              sessions.map((session) => {
                const formatLastActive = (timestamp) => {
                  const date = new Date(timestamp);
                  const now = new Date();
                  const diffMs = now - date;
                  const diffMins = Math.floor(diffMs / 60000);
                  
                  if (diffMins < 1) return 'Just now';
                  if (diffMins < 60) return `${diffMins} minutes ago`;
                  return date.toLocaleString();
                };

                return (
                  <div key={session.id} className="session-item">
                    <div className="session-info">
                      <div className="session-header">
                        <h4>{session.device}</h4>
                        {session.current && <span className="current-badge">Current Session</span>}
                      </div>
                      <p className="session-details">
                        {session.location} • {session.ip}
                      </p>
                      <p className="session-time">
                        Last active: {formatLastActive(session.last_active || session.lastActive)}
                      </p>
                    </div>
                    {!session.current && (
                      <button 
                        className="btn-danger-outline"
                        onClick={() => handleTerminateSession(session.id)}
                      >
                        Terminate
                      </button>
                    )}
                  </div>
                );
              })
            ) : (
              <p>No active sessions</p>
            )}
          </div>
        </div>

        {/* Login History */}
        <div className="security-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8.5 5.5a.5.5 0 0 0-1 0v3.362l-1.429 2.38a.5.5 0 1 0 .858.515l1.5-2.5A.5.5 0 0 0 8.5 9V5.5z"/>
              <path d="M6.5 0a.5.5 0 0 0 0 1H7v1.07a7.001 7.001 0 0 0-3.273 12.474l-.602.602a.5.5 0 0 0 .707.708l.746-.746A6.97 6.97 0 0 0 8 16a6.97 6.97 0 0 0 3.422-.892l.746.746a.5.5 0 0 0 .707-.708l-.601-.602A7.001 7.001 0 0 0 9 2.07V1h.5a.5.5 0 0 0 0-1h-3zm1.038 3.018a6.093 6.093 0 0 1 .924 0 6 6 0 1 1-.924 0zM0 3.5c0 .753.333 1.429.86 1.887A8.035 8.035 0 0 1 4.387 1.86 2.5 2.5 0 0 0 0 3.5zM13.5 1c-.753 0-1.429.333-1.887.86a8.035 8.035 0 0 1 3.527 3.527A2.5 2.5 0 0 0 13.5 1z"/>
            </svg>
            Recent Activity
          </h3>
          <div className="security-group">
            {activities.length > 0 ? (
              activities.map((activity, index) => {
                // Icon mapping
                const getIcon = (action) => {
                  if (action.toLowerCase().includes('login')) return '🔐';
                  if (action.toLowerCase().includes('password')) return '🔑';
                  if (action.toLowerCase().includes('2fa')) return '🛡️';
                  if (action.toLowerCase().includes('session')) return '🚪';
                  return '⚙️';
                };

                const formatTime = (timestamp) => {
                  const date = new Date(timestamp);
                  const now = new Date();
                  const diffMs = now - date;
                  const diffMins = Math.floor(diffMs / 60000);
                  const diffHours = Math.floor(diffMs / 3600000);
                  const diffDays = Math.floor(diffMs / 86400000);

                  if (diffMins < 60) return `${diffMins} minutes ago`;
                  if (diffHours < 24) return `${diffHours} hours ago`;
                  if (diffDays < 7) return `${diffDays} days ago`;
                  return date.toLocaleDateString();
                };

                return (
                  <div key={index} className="activity-item">
                    <div className="activity-icon">{getIcon(activity.action)}</div>
                    <div className="activity-details">
                      <h4>{activity.action}</h4>
                      <p>{activity.description}</p>
                      <small>{formatTime(activity.timestamp)}</small>
                      {activity.ip && <small> • IP: {activity.ip}</small>}
                    </div>
                  </div>
                );
              })
            ) : (
              <p>No recent activity</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SecuritySettingsPage;
