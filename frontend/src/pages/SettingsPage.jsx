import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { apiClient } from '../api';
import LoadingSpinner from '../components/LoadingSpinner';
import '../styles/settings.css';

const SettingsPage = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [apiKeys, setApiKeys] = useState([]);
  const [notifications, setNotifications] = useState({
    emailNotifications: true,
    budgetAlerts: true,
    securityAlerts: true,
    weeklyReports: false,
    maintenanceUpdates: true,
  });

  const [preferences, setPreferences] = useState({
    theme: 'dark',
    language: 'en',
    timezone: 'UTC-5',
    dateFormat: 'MM/DD/YYYY',
    currency: 'USD',
  });

  const [billing, setBilling] = useState({
    autoRenew: true,
    paymentMethod: 'Credit Card ****1234',
  });

  useEffect(() => {
    fetchSettings();
    fetchApiKeys();
  }, []);

  const fetchSettings = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.get('/settings/');
      const data = response.data;
      
      setNotifications({
        emailNotifications: data.notifications.email_notifications,
        budgetAlerts: data.notifications.budget_alerts,
        securityAlerts: data.notifications.security_alerts,
        weeklyReports: data.notifications.weekly_reports,
        maintenanceUpdates: data.notifications.maintenance_updates,
      });
      
      setPreferences(data.preferences);
      setBilling({
        autoRenew: data.billing.auto_renew,
        paymentMethod: data.billing.payment_method || 'Credit Card ****1234'
      });
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchApiKeys = async () => {
    try {
      const response = await apiClient.get('/settings/api-keys');
      setApiKeys(response.data.keys || []);
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
    }
  };

  const handleNotificationChange = async (key) => {
    const newNotifications = {
      ...notifications,
      [key]: !notifications[key]
    };
    setNotifications(newNotifications);
    
    try {
      await apiClient.put('/settings/notifications', {
        email_notifications: newNotifications.emailNotifications,
        budget_alerts: newNotifications.budgetAlerts,
        security_alerts: newNotifications.securityAlerts,
        weekly_reports: newNotifications.weeklyReports,
        maintenance_updates: newNotifications.maintenanceUpdates,
      });
      toast.success('Notification settings updated');
    } catch (error) {
      toast.error('Failed to update notifications');
      // Revert change
      setNotifications(notifications);
    }
  };

  const handlePreferenceChange = (e) => {
    setPreferences({
      ...preferences,
      [e.target.name]: e.target.value
    });
  };

  const handleSavePreferences = async () => {
    try {
      await apiClient.put('/settings/preferences', preferences);
      toast.success('Preferences saved successfully!');
    } catch (error) {
      toast.error('Failed to save preferences');
    }
  };

  const handleGenerateApiKey = async () => {
    try {
      const response = await apiClient.post('/settings/api-keys');
      toast.success(
        <div>
          <strong>API Key Generated!</strong><br/>
          <code style={{fontSize: '0.85rem'}}>{response.data.key}</code><br/>
          <small>{response.data.note}</small>
        </div>,
        { autoClose: false }
      );
      fetchApiKeys();
    } catch (error) {
      toast.error('Failed to generate API key');
    }
  };

  const handleRevokeApiKey = async (keyId) => {
    try {
      await apiClient.delete(`/settings/api-keys/${keyId}`);
      toast.success('API key revoked');
      fetchApiKeys();
    } catch (error) {
      toast.error('Failed to revoke API key');
    }
  };

  const handleUpdatePaymentMethod = async () => {
    const cardNumber = prompt('Enter the last 4 digits of your new card:');
    
    if (!cardNumber) {
      toast.info('Payment method update cancelled');
      return;
    }
    
    if (cardNumber.length !== 4 || isNaN(cardNumber)) {
      toast.error('Please enter exactly 4 digits');
      return;
    }

    try {
      await apiClient.put('/settings/payment-method', {
        last_four: cardNumber
      });
      
      const newPaymentMethod = `Credit Card ****${cardNumber}`;
      setBilling({ ...billing, paymentMethod: newPaymentMethod });
      toast.success('Payment method updated successfully!');
    } catch (error) {
      toast.error('Failed to update payment method');
    }
  };

  if (isLoading) {
    return <LoadingSpinner size="large" text="Loading settings..." />;
  }

  return (
    <div className="settings-page">
      <div className="settings-header">
        <h2>Settings</h2>
        <p>Manage your application preferences and configurations</p>
      </div>

      <div className="settings-content">
        {/* Notifications Settings */}
        <div className="settings-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 16a2 2 0 0 0 2-2H6a2 2 0 0 0 2 2zM8 1.918l-.797.161A4.002 4.002 0 0 0 4 6c0 .628-.134 2.197-.459 3.742-.16.767-.376 1.566-.663 2.258h10.244c-.287-.692-.502-1.49-.663-2.258C12.134 8.197 12 6.628 12 6a4.002 4.002 0 0 0-3.203-3.92L8 1.917zM14.22 12c.223.447.481.801.78 1H1c.299-.199.557-.553.78-1C2.68 10.2 3 6.88 3 6c0-2.42 1.72-4.44 4.005-4.901a1 1 0 1 1 1.99 0A5.002 5.002 0 0 1 13 6c0 .88.32 4.2 1.22 6z"/>
            </svg>
            Notifications
          </h3>
          <div className="settings-group">
            {Object.entries(notifications).map(([key, value]) => (
              <div key={key} className="setting-item">
                <div className="setting-info">
                  <h4>{key.replace(/([A-Z])/g, ' $1').trim()}</h4>
                  <p>Receive {key.replace(/([A-Z])/g, ' $1').toLowerCase()} notifications</p>
                </div>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={value}
                    onChange={() => handleNotificationChange(key)}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
            ))}
          </div>
        </div>

        {/* Preferences */}
        <div className="settings-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492zM5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0z"/>
              <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52l-.094-.319z"/>
            </svg>
            Preferences
          </h3>
          <div className="settings-group">
            <div className="setting-item-full">
              <label>Theme</label>
              <select
                name="theme"
                value={preferences.theme}
                onChange={handlePreferenceChange}
                className="settings-select"
              >
                <option value="dark">Dark</option>
                <option value="light">Light</option>
                <option value="auto">Auto</option>
              </select>
            </div>

            <div className="setting-item-full">
              <label>Language</label>
              <select
                name="language"
                value={preferences.language}
                onChange={handlePreferenceChange}
                className="settings-select"
              >
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
            </div>

            <div className="setting-item-full">
              <label>Timezone</label>
              <select
                name="timezone"
                value={preferences.timezone}
                onChange={handlePreferenceChange}
                className="settings-select"
              >
                <option value="UTC-8">Pacific Time (UTC-8)</option>
                <option value="UTC-5">Eastern Time (UTC-5)</option>
                <option value="UTC+0">UTC</option>
                <option value="UTC+1">Central European Time (UTC+1)</option>
              </select>
            </div>

            <div className="setting-item-full">
              <label>Date Format</label>
              <select
                name="dateFormat"
                value={preferences.dateFormat}
                onChange={handlePreferenceChange}
                className="settings-select"
              >
                <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD</option>
              </select>
            </div>

            <div className="setting-item-full">
              <label>Currency</label>
              <select
                name="currency"
                value={preferences.currency}
                onChange={handlePreferenceChange}
                className="settings-select"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="JPY">JPY (¥)</option>
              </select>
            </div>
          </div>
          <button className="btn-save" onClick={handleSavePreferences}>
            Save Preferences
          </button>
        </div>

        {/* Billing Settings */}
        <div className="settings-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V4zm2-1a1 1 0 0 0-1 1v1h14V4a1 1 0 0 0-1-1H2zm13 4H1v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V7z"/>
              <path d="M2 10a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-1z"/>
            </svg>
            Billing & Payment
          </h3>
          <div className="settings-group">
            <div className="setting-item">
              <div className="setting-info">
                <h4>Auto-Renewal</h4>
                <p>Automatically renew subscription at the end of billing cycle</p>
              </div>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={billing.autoRenew}
                  onChange={async () => {
                    const newValue = !billing.autoRenew;
                    setBilling({ ...billing, autoRenew: newValue });
                    try {
                      await apiClient.put('/settings/billing', {
                        auto_renew: newValue,
                        payment_method: billing.paymentMethod
                      });
                      toast.success('Billing settings updated');
                    } catch (error) {
                      toast.error('Failed to update billing settings');
                      setBilling({ ...billing, autoRenew: !newValue });
                    }
                  }}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <div className="billing-method">
              <div className="payment-info">
                <h4>Payment Method</h4>
                <p>{billing.paymentMethod}</p>
              </div>
              <button className="btn-secondary" onClick={handleUpdatePaymentMethod}>Update Payment Method</button>
            </div>
          </div>
        </div>

        {/* API Keys */}
        <div className="settings-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M0 8a4 4 0 0 1 7.465-2H14a.5.5 0 0 1 .354.146l1.5 1.5a.5.5 0 0 1 0 .708l-1.5 1.5a.5.5 0 0 1-.708 0L13 9.207l-.646.647a.5.5 0 0 1-.708 0L11 9.207l-.646.647a.5.5 0 0 1-.708 0L9 9.207l-.646.647A.5.5 0 0 1 8 10h-.535A4 4 0 0 1 0 8zm4-3a3 3 0 1 0 2.712 4.285A.5.5 0 0 1 7.163 9h.63l.853-.854a.5.5 0 0 1 .708 0l.646.647.646-.647a.5.5 0 0 1 .708 0l.646.647.646-.647a.5.5 0 0 1 .708 0l.646.647.793-.793-1-1h-6.63a.5.5 0 0 1-.451-.285A3 3 0 0 0 4 5z"/>
              <path d="M4 8a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"/>
            </svg>
            API Keys
          </h3>
          <div className="settings-group">
            <p className="info-text">Generate and manage API keys for programmatic access to your resources</p>
            {apiKeys.map((key) => (
              <div key={key.key_id} className="api-key-item">
                <div className="api-key-info">
                  <h4>Production API Key</h4>
                  <code>{key.key_preview}</code>
                  <p className="key-created">Created: {new Date(key.created_at).toLocaleDateString()}</p>
                </div>
                <button className="btn-danger-outline" onClick={() => handleRevokeApiKey(key.key_id)}>Revoke</button>
              </div>
            ))}
            {apiKeys.length === 0 && (
              <p className="info-text">No API keys generated yet</p>
            )}
            <button className="btn-secondary" onClick={handleGenerateApiKey}>Generate New API Key</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
