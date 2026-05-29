import React, { useCallback, useState, useEffect } from 'react';
import api from '../../api';
import { toast } from 'react-toastify';
import '../../styles/admin-pages.css';
import { 
  FaCog, FaToggleOn, FaToggleOff, FaServer, 
  FaDatabase, FaEnvelope, FaClock, FaShieldAlt 
} from 'react-icons/fa';

const AdminSettingsPage = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState(null);
  const [statistics, setStatistics] = useState(null);

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/admin/settings');
      setSettings(response.data.settings);
      setStatistics(response.data.statistics);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
      toast.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleToggle = (key) => {
    setSettings({ ...settings, [key]: !settings[key] });
  };

  const handleInputChange = (key, value) => {
    setSettings({ ...settings, [key]: value });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/admin/settings', settings);
      toast.success('Settings saved successfully!');
    } catch (error) {
      console.error('Failed to save settings:', error);
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="spinner"></div>
        <p>Loading settings...</p>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="admin-loading">
        <p>Failed to load settings</p>
      </div>
    );
  }

  return (
    <div className="admin-settings">
      <div className="admin-page-header">
        <h1>Platform Settings</h1>
        <p>Configure platform-wide settings and preferences</p>
      </div>

      {/* Statistics */}
      {statistics && (
        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', marginBottom: '2rem' }}>
          <div className="stat-card">
            <div className="stat-icon stat-icon--gold">
              <FaServer />
            </div>
            <div className="stat-info">
              <p className="stat-label">Total Users</p>
              <h3 className="stat-value">{statistics.total_users}</h3>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
              <FaShieldAlt />
            </div>
            <div className="stat-info">
              <p className="stat-label">Active Subscriptions</p>
              <h3 className="stat-value">{statistics.active_subscriptions}</h3>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
              <FaDatabase />
            </div>
            <div className="stat-info">
              <p className="stat-label">Total Revenue</p>
              <h3 className="stat-value">₹{statistics.total_revenue.toLocaleString()}</h3>
            </div>
          </div>
        </div>
      )}

      {/* General Settings */}
      <div className="settings-section">
        <h2><FaCog /> General Settings</h2>
        <div className="settings-grid">
          <div className="setting-item">
            <label>Platform Name</label>
            <input
              type="text"
              value={settings.platform_name}
              onChange={(e) => handleInputChange('platform_name', e.target.value)}
              className="setting-input"
            />
          </div>
        </div>
      </div>

      {/* Platform Controls */}
      <div className="settings-section">
        <h2><FaShieldAlt /> Platform Controls</h2>
        <div className="settings-list">
          <div className="setting-toggle">
            <div className="toggle-info">
              <h3>Maintenance Mode</h3>
              <p>Temporarily disable platform access for maintenance</p>
            </div>
            <button 
              className="toggle-button"
              onClick={() => handleToggle('maintenance_mode')}
            >
              {settings.maintenance_mode ? (
                <FaToggleOn className="toggle-icon active" />
              ) : (
                <FaToggleOff className="toggle-icon" />
              )}
            </button>
          </div>

          <div className="setting-toggle">
            <div className="toggle-info">
              <h3>Allow New Registrations</h3>
              <p>Enable or disable new user sign-ups</p>
            </div>
            <button 
              className="toggle-button"
              onClick={() => handleToggle('allow_new_registrations')}
            >
              {settings.allow_new_registrations ? (
                <FaToggleOn className="toggle-icon active" />
              ) : (
                <FaToggleOff className="toggle-icon" />
              )}
            </button>
          </div>

          <div className="setting-toggle">
            <div className="toggle-info">
              <h3>Email Notifications</h3>
              <p>Send email notifications to users</p>
            </div>
            <button 
              className="toggle-button"
              onClick={() => handleToggle('email_notifications_enabled')}
            >
              {settings.email_notifications_enabled ? (
                <FaToggleOn className="toggle-icon active" />
              ) : (
                <FaToggleOff className="toggle-icon" />
              )}
            </button>
          </div>

          <div className="setting-toggle">
            <div className="toggle-info">
              <h3>Require Email Verification</h3>
              <p>Require users to verify email before accessing platform</p>
            </div>
            <button 
              className="toggle-button"
              onClick={() => handleToggle('require_email_verification')}
            >
              {settings.require_email_verification ? (
                <FaToggleOn className="toggle-icon active" />
              ) : (
                <FaToggleOff className="toggle-icon" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Default Limits */}
      <div className="settings-section">
        <h2><FaServer /> Default Resource Limits (Free Tier)</h2>
        <div className="settings-grid">
          <div className="setting-item">
            <label>Default VM Limit</label>
            <input
              type="number"
              value={settings.default_vm_limit}
              onChange={(e) => handleInputChange('default_vm_limit', parseInt(e.target.value))}
              className="setting-input"
              min="1"
              max="100"
            />
          </div>

          <div className="setting-item">
            <label>Default Storage (GB)</label>
            <input
              type="number"
              value={settings.default_storage_gb}
              onChange={(e) => handleInputChange('default_storage_gb', parseInt(e.target.value))}
              className="setting-input"
              min="1"
              max="1000"
            />
          </div>
        </div>
      </div>

      {/* Security Settings */}
      <div className="settings-section">
        <h2><FaClock /> Security & Sessions</h2>
        <div className="settings-grid">
          <div className="setting-item">
            <label>Session Timeout (hours)</label>
            <input
              type="number"
              value={settings.session_timeout_hours}
              onChange={(e) => handleInputChange('session_timeout_hours', parseInt(e.target.value))}
              className="setting-input"
              min="1"
              max="168"
            />
          </div>

          <div className="setting-item">
            <label>Max Login Attempts</label>
            <input
              type="number"
              value={settings.max_login_attempts}
              onChange={(e) => handleInputChange('max_login_attempts', parseInt(e.target.value))}
              className="setting-input"
              min="3"
              max="10"
            />
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="settings-actions">
        <button 
          className="save-settings-btn"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
};

export default AdminSettingsPage;