// =============================================================================
// PAGE: SettingsPage.jsx  (830 lines)
// ROUTE: /dashboard/settings
// PURPOSE: User preferences — theme (dark/light/auto), currency, timezone, date format,
//          BYOC (Bring Your Own Cloud) AWS credential management, notification toggles,
//          language, session management, and "Restart Tour" button
// API: Uses apiClient from api.js — saves preferences to /api/settings, BYOC to /api/byoc/*
// CONTEXTS: ThemeContext (theme switching), PreferencesContext (currency/timezone/date),
//           AuthContext (current user)
// BACKEND: /api/settings → preferences, /api/byoc → connect/test/disconnect
// DO NOT:
//   - Bypass ThemeContext for theme changes — it syncs to DB and applies CSS class to <html>
//   - Add inline style overrides for theme — use CSS variables from index.css
//   - Remove the "Restart Tour" button from Preferences section (localStorage: zenith_onboarding_complete)
// =============================================================================
import React, { useMemo, useState, useEffect } from 'react';
import { useNotifications } from "../hooks/useNotifications";
import { useTheme } from "../context/ThemeContext";
import { usePreferences } from "../context/PreferencesContext";
import { apiClient } from '../api';
import LoadingSpinner from '../components/LoadingSpinner';
import {
  getValidationErrorMessage,
  validateByocConnectionForm,
} from '../utils/formValidation';
import '../styles/settings.css';

const SettingsPage = () => {
  const notifications = useNotifications();
  const { theme, setTheme } = useTheme();
  const { updatePreferences } = usePreferences();
  
  const [isLoading, setIsLoading] = useState(true);
  const [apiKeys, setApiKeys] = useState([]);
  const [notificationSettings, setNotificationSettings] = useState({
    emailNotifications: true,
    budgetAlerts: true,
    securityAlerts: true,
    weeklyReports: false,
    maintenanceUpdates: true,
  });

  const [preferences, setPreferences] = useState({
    theme: theme,
    language: 'en',
    timezone: 'UTC+5:30',
    dateFormat: 'MM/DD/YYYY',
    currency: 'USD',
  });

  // BYOC State
  const [byocStatus, setByocStatus] = useState(null);
  const [byocEligible, setByocEligible] = useState(false);
  const [byocCurrentPlan, setByocCurrentPlan] = useState('free');
  const [byocActiveCSP, setByocActiveCSP] = useState(null); // Which CSP form is open
  const [byocMethod, setByocMethod] = useState('access_keys'); // access_keys or iam_role
  const [byocConnecting, setByocConnecting] = useState(false);
  const [byocTesting, setByocTesting] = useState(false);
  const [byocTestResult, setByocTestResult] = useState(null);
  const [showPolicy, setShowPolicy] = useState(false);
  const [policyTemplates, setPolicyTemplates] = useState(null);

  // BYOC Form fields
  const [awsForm, setAwsForm] = useState({ access_key_id: '', secret_access_key: '', bucket_name: '', region: 'ap-south-1', role_arn: '' });
  const [gcpForm, setGcpForm] = useState({ service_account_json: '', gcp_bucket_name: '' });
  const [azureForm, setAzureForm] = useState({ account_name: '', account_key: '', container_name: '' });

  const byocValidation = useMemo(
    () => validateByocConnectionForm({
      csp: byocActiveCSP,
      method: byocMethod,
      awsForm,
      gcpForm,
      azureForm,
    }),
    [byocActiveCSP, byocMethod, awsForm, gcpForm, azureForm]
  );

  useEffect(() => {
    fetchSettings();
    fetchApiKeys();
    fetchByocStatus();
  }, []);

  // Sync theme from ThemeContext when it changes externally
  useEffect(() => {
    setPreferences(prev => ({ ...prev, theme }));
  }, [theme]);

  const fetchSettings = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.get('/settings/');
      const data = response.data;
      
      setNotificationSettings({
        emailNotifications: data.notifications.email_notifications,
        budgetAlerts: data.notifications.budget_alerts,
        securityAlerts: data.notifications.security_alerts,
        weeklyReports: data.notifications.weekly_reports,
        maintenanceUpdates: data.notifications.maintenance_updates,
      });
      
      setPreferences(prev => ({
        ...prev,
        ...data.preferences,
        theme: theme, // Always use ThemeContext as source of truth
      }));
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

  const fetchByocStatus = async () => {
    try {
      const response = await apiClient.get('/byoc/status');
      setByocStatus(response.data.connections);
      setByocEligible(response.data.eligible);
      setByocCurrentPlan(response.data.current_plan);
    } catch (error) {
      console.error('Failed to fetch BYOC status:', error);
    }
  };

  const fetchPolicyTemplates = async () => {
    try {
      const response = await apiClient.get('/byoc/policy-templates');
      setPolicyTemplates(response.data);
    } catch (error) {
      console.error('Failed to fetch policy templates:', error);
    }
  };

  const handleByocTest = async () => {
    if (!byocValidation.isValid) {
      setByocTestResult({ success: false, message: getValidationErrorMessage(byocValidation.errors) });
      return;
    }

    setByocTesting(true);
    setByocTestResult(null);
    try {
      let payload = { csp: byocActiveCSP, connection_method: byocMethod };
      if (byocActiveCSP === 'AWS') Object.assign(payload, awsForm);
      else if (byocActiveCSP === 'GCP') Object.assign(payload, gcpForm);
      else if (byocActiveCSP === 'Azure') Object.assign(payload, azureForm);

      const response = await apiClient.post('/byoc/test', payload);
      setByocTestResult(response.data);
    } catch (error) {
      const detail = error.response?.data?.detail;
      setByocTestResult({ success: false, message: detail?.message || detail || 'Connection test failed' });
    } finally {
      setByocTesting(false);
    }
  };

  const handleByocConnect = async () => {
    if (!byocValidation.isValid) {
      setByocTestResult({ success: false, message: getValidationErrorMessage(byocValidation.errors) });
      return;
    }

    setByocConnecting(true);
    try {
      let payload = { csp: byocActiveCSP, connection_method: byocMethod };
      if (byocActiveCSP === 'AWS') Object.assign(payload, awsForm);
      else if (byocActiveCSP === 'GCP') Object.assign(payload, gcpForm);
      else if (byocActiveCSP === 'Azure') Object.assign(payload, azureForm);

      await apiClient.post('/byoc/connect', payload);
      setByocActiveCSP(null);
      setByocTestResult(null);
      fetchByocStatus();
    } catch (error) {
      const detail = error.response?.data?.detail;
      setByocTestResult({ success: false, message: detail?.message || detail || 'Failed to connect' });
    } finally {
      setByocConnecting(false);
    }
  };

  const handleByocDisconnect = async (csp) => {
    if (!window.confirm(`Disconnect your ${csp} account? Operations will revert to Zenith's managed infrastructure.`)) return;
    try {
      await apiClient.delete(`/byoc/disconnect/${csp}`);
      fetchByocStatus();
    } catch (error) {
      console.error('Failed to disconnect:', error);
    }
  };

  const handleNotificationChange = async (key) => {
    // Don't allow toggling "Coming Soon" features
    if (key === 'weeklyReports') return;

    const newNotificationSettings = {
      ...notificationSettings,
      [key]: !notificationSettings[key]
    };
    setNotificationSettings(newNotificationSettings);
    
    try {
      await apiClient.put('/settings/notifications', {
        email_notifications: newNotificationSettings.emailNotifications,
        budget_alerts: newNotificationSettings.budgetAlerts,
        security_alerts: newNotificationSettings.securityAlerts,
        weekly_reports: newNotificationSettings.weeklyReports,
        maintenance_updates: newNotificationSettings.maintenanceUpdates,
      });
      notifications.success('Notification settings updated');
    } catch (error) {
      notifications.error('Failed to update notifications');
      // Revert change
      setNotificationSettings(notificationSettings);
    }
  };

  const handlePreferenceChange = (e) => {
    const { name, value } = e.target;
    
    setPreferences({
      ...preferences,
      [name]: value
    });

    // Apply theme change immediately through ThemeContext
    if (name === 'theme') {
      setTheme(value);
    }
  };

  const handleSavePreferences = async () => {
    try {
      await apiClient.put('/settings/preferences', {
        theme: preferences.theme,
        language: preferences.language,
        timezone: preferences.timezone,
        date_format: preferences.dateFormat,
        currency: preferences.currency,
      });
      
      // Update the app-wide PreferencesContext so formatting changes propagate immediately
      updatePreferences({
        currency: preferences.currency,
        dateFormat: preferences.dateFormat,
        timezone: preferences.timezone,
      });
      
      notifications.success('Preferences saved successfully!');
    } catch (error) {
      notifications.error('Failed to save preferences');
    }
  };

  const handleGenerateApiKey = async () => {
    try {
      const response = await apiClient.post('/settings/api-keys');
      notifications.success(
        <div>
          <strong>API Key Generated!</strong><br/>
          <code style={{fontSize: '0.85rem'}}>{response.data.key}</code><br/>
          <small>{response.data.note}</small>
        </div>,
        { autoClose: false }
      );
      fetchApiKeys();
    } catch (error) {
      notifications.error('Failed to generate API key');
    }
  };

  const handleRevokeApiKey = async (keyId) => {
    try {
      await apiClient.delete(`/settings/api-keys/${keyId}`);
      notifications.success('API key revoked');
      fetchApiKeys();
    } catch (error) {
      notifications.error('Failed to revoke API key');
    }
  };

  // Notification display config: labels, descriptions, and whether it's coming soon
  const notificationConfig = {
    emailNotifications: {
      label: 'Email Notifications',
      description: 'Receive important updates via email',
      comingSoon: false,
    },
    budgetAlerts: {
      label: 'Budget Alerts',
      description: 'Get notified when spending approaches budget limits',
      comingSoon: false,
    },
    securityAlerts: {
      label: 'Security Alerts',
      description: 'Receive alerts about security events and threats',
      comingSoon: false,
    },
    weeklyReports: {
      label: 'Weekly Reports',
      description: 'Receive weekly cloud usage and cost summaries',
      comingSoon: true,
    },
    maintenanceUpdates: {
      label: 'Maintenance Updates',
      description: 'Get notified about scheduled maintenance windows',
      comingSoon: false,
    },
  };

  // BYOC Cloud Icons
  const CloudIcon = ({ csp }) => {
    const icons = {
      AWS: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M7.164 16.12c-1.876-.56-3.227-1.3-3.227-1.3l-.427.858s1.514.826 3.586 1.424l.068-.982z" fill="#F90"/>
          <path d="M12 4C7.6 4 4.5 6.8 4.5 10.5c0 2.4 1.5 4.5 3.8 5.7l.2-1c-1.8-1-3-2.7-3-4.7C5.5 7.3 8.2 5 12 5s6.5 2.3 6.5 5.5c0 2-1.2 3.7-3 4.7l.2 1c2.3-1.2 3.8-3.3 3.8-5.7C19.5 6.8 16.4 4 12 4z" fill="#F90"/>
        </svg>
      ),
      GCP: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M12 6l-6 10.4h12L12 6z" fill="#4285F4"/>
          <circle cx="12" cy="16.4" r="3" fill="#34A853"/>
        </svg>
      ),
      Azure: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M5 5h6l-3 14H5l3-14zm4 0l7 14h3L12 5H9z" fill="#0078D4"/>
        </svg>
      ),
    };
    return icons[csp] || null;
  };

  // BYOC Section Renderer
  const renderByocSection = () => {
    if (!byocEligible) {
      return (
        <div className="settings-card byoc-card animate-fade-in-up">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M4.406 3.342A5.53 5.53 0 0 1 8 2c2.69 0 4.923 2 5.166 4.579C14.758 6.804 16 8.137 16 9.773 16 11.569 14.502 13 12.687 13H3.781C1.708 13 0 11.366 0 9.318c0-1.763 1.266-3.223 2.942-3.593.143-.863.698-1.723 1.464-2.383z"/>
            </svg>
            Bring Your Own Cloud (BYOC)
            <span className="byoc-badge byoc-badge-locked">Pro / Enterprise</span>
          </h3>
          <div className="byoc-upgrade-prompt">
            <p>Connect your own AWS, GCP, or Azure accounts. All cloud operations will use your infrastructure — you only pay the platform fee.</p>
            <p className="byoc-plan-note">
              <strong>Your current plan:</strong> <span className="plan-badge">{byocCurrentPlan}</span> — Upgrade to <strong>Pro</strong> or <strong>Enterprise</strong> to unlock BYOC.
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="settings-card byoc-card animate-fade-in-up">
        <h3>
          <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
            <path d="M4.406 3.342A5.53 5.53 0 0 1 8 2c2.69 0 4.923 2 5.166 4.579C14.758 6.804 16 8.137 16 9.773 16 11.569 14.502 13 12.687 13H3.781C1.708 13 0 11.366 0 9.318c0-1.763 1.266-3.223 2.942-3.593.143-.863.698-1.723 1.464-2.383z"/>
          </svg>
          Bring Your Own Cloud (BYOC)
          <span className="byoc-badge byoc-badge-active">Active</span>
        </h3>
        <p className="byoc-description">
          Connect your own cloud accounts. Operations will use your infrastructure — you only pay the Zenith platform fee.
        </p>

        {/* Cloud Provider Cards */}
        <div className="byoc-providers">
          {['AWS', 'GCP', 'Azure'].map((csp) => {
            const connection = byocStatus?.[csp.toLowerCase()];
            const isConnected = connection?.connected;

            return (
              <div key={csp} className={`byoc-provider-card ${isConnected ? 'connected' : ''}`}>
                <div className="byoc-provider-header">
                  <div className="byoc-provider-info">
                    <CloudIcon csp={csp} />
                    <div>
                      <h4>{csp === 'GCP' ? 'Google Cloud' : csp === 'Azure' ? 'Microsoft Azure' : 'Amazon Web Services'}</h4>
                      {isConnected ? (
                        <span className="byoc-status-connected">● Connected — {connection.bucket_name}</span>
                      ) : (
                        <span className="byoc-status-disconnected">○ Not connected</span>
                      )}
                    </div>
                  </div>
                  {isConnected ? (
                    <button className="btn-disconnect" onClick={() => handleByocDisconnect(csp)}>Disconnect</button>
                  ) : (
                    <button className="btn-connect" onClick={() => {
                      setByocActiveCSP(csp);
                      setByocTestResult(null);
                      setByocMethod('access_keys');
                      if (!policyTemplates) fetchPolicyTemplates();
                    }}>Connect</button>
                  )}
                </div>

                {/* Expanded Connection Form */}
                {byocActiveCSP === csp && !isConnected && (
                  <div className="byoc-connect-form">
                    {/* Method Selection */}
                    <div className="byoc-method-selector">
                      <button
                        className={`method-btn ${byocMethod === 'access_keys' ? 'active' : ''}`}
                        onClick={() => setByocMethod('access_keys')}
                      >
                        <span className="method-icon">🔑</span>
                        <span className="method-label">Quick Setup</span>
                        <span className="method-risk risk-medium">⚠️ Medium Risk</span>
                      </button>
                      <button
                        className={`method-btn ${byocMethod === 'iam_role' ? 'active' : ''}`}
                        onClick={() => setByocMethod('iam_role')}
                      >
                        <span className="method-icon">🛡️</span>
                        <span className="method-label">Secure Setup (Recommended)</span>
                        <span className="method-risk risk-low">✅ Low Risk</span>
                      </button>
                    </div>

                    {/* Risk Warning */}
                    <div className={`byoc-risk-warning ${byocMethod === 'access_keys' ? 'risk-medium' : 'risk-low'}`}>
                      {byocMethod === 'access_keys' ? (
                        <>
                          <strong>⚠️ Medium Risk — Quick Setup</strong>
                          <p>You'll paste your existing cloud keys directly. If these are root or admin keys, a breach could expose your entire {csp} account. Only use this if you understand the risk.</p>
                        </>
                      ) : (
                        <>
                          <strong>✅ Low Risk — Secure Setup</strong>
                          <p>First, create a new user in your {csp} console with only storage permissions using our policy template below. Then paste that new user's keys here. Even if breached, the attacker can only access one bucket — nothing else.</p>
                          {policyTemplates && (
                            <button className="btn-show-policy" onClick={() => setShowPolicy(!showPolicy)}>
                              {showPolicy ? 'Hide' : 'Show'} IAM Policy Template
                            </button>
                          )}
                          {showPolicy && policyTemplates?.[csp] && (
                            <div className="policy-template">
                              <h5>Setup Steps:</h5>
                              <ol>
                                {policyTemplates[csp].setup_steps.map((step, i) => (
                                  <li key={i}>{step}</li>
                                ))}
                              </ol>
                              {policyTemplates[csp].policy_json && (
                                <>
                                  <h5>IAM Policy JSON:</h5>
                                  <pre className="policy-json">
                                    {JSON.stringify(policyTemplates[csp].policy_json, null, 2)}
                                  </pre>
                                  <button className="btn-copy-policy" onClick={() => {
                                    navigator.clipboard.writeText(JSON.stringify(policyTemplates[csp].policy_json, null, 2));
                                  }}>📋 Copy Policy</button>
                                </>
                              )}
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {/* CSP-specific form fields */}
                    {csp === 'AWS' && byocMethod === 'access_keys' && (
                      <div className="byoc-fields">
                        <div className="byoc-field">
                          <label>Access Key ID</label>
                          <input type="text" placeholder="AKIA..." value={awsForm.access_key_id}
                            onChange={(e) => setAwsForm({...awsForm, access_key_id: e.target.value})}
                            aria-invalid={!!byocValidation.errors.access_key_id}
                            aria-describedby={byocValidation.errors.access_key_id ? 'byoc-aws-access-key-error' : undefined} />
                          {byocValidation.errors.access_key_id && <p id="byoc-aws-access-key-error" className="form-field-error">{byocValidation.errors.access_key_id}</p>}
                        </div>
                        <div className="byoc-field">
                          <label>Secret Access Key</label>
                          <input type="password" placeholder="Your secret key" value={awsForm.secret_access_key}
                            onChange={(e) => setAwsForm({...awsForm, secret_access_key: e.target.value})}
                            aria-invalid={!!byocValidation.errors.secret_access_key}
                            aria-describedby={byocValidation.errors.secret_access_key ? 'byoc-aws-secret-key-error' : undefined} />
                          {byocValidation.errors.secret_access_key && <p id="byoc-aws-secret-key-error" className="form-field-error">{byocValidation.errors.secret_access_key}</p>}
                        </div>
                        <div className="byoc-field">
                          <label>S3 Bucket Name</label>
                          <input type="text" placeholder="my-company-bucket" value={awsForm.bucket_name}
                            onChange={(e) => setAwsForm({...awsForm, bucket_name: e.target.value})}
                            aria-invalid={!!byocValidation.errors.bucket_name}
                            aria-describedby={byocValidation.errors.bucket_name ? 'byoc-aws-bucket-error' : undefined} />
                          {byocValidation.errors.bucket_name && <p id="byoc-aws-bucket-error" className="form-field-error">{byocValidation.errors.bucket_name}</p>}
                        </div>
                        <div className="byoc-field">
                          <label>Region</label>
                          <select value={awsForm.region} onChange={(e) => setAwsForm({...awsForm, region: e.target.value})}>
                            <option value="ap-south-1">AP South 1 (Mumbai)</option>
                            <option value="us-east-1">US East 1 (Virginia)</option>
                            <option value="us-west-2">US West 2 (Oregon)</option>
                            <option value="eu-west-1">EU West 1 (Ireland)</option>
                          </select>
                        </div>
                      </div>
                    )}

                    {csp === 'AWS' && byocMethod === 'iam_role' && (
                      <div className="byoc-fields">
                        {policyTemplates?.AWS?.iam_role?.external_id && (
                          <div className="byoc-readonly-field">
                            <label>Your External ID <span className="auto-generated">(auto-generated, use in trust policy)</span></label>
                            <div className="readonly-value">
                              <code>{policyTemplates.AWS.iam_role.external_id}</code>
                              <button className="btn-copy-small" onClick={() => navigator.clipboard.writeText(policyTemplates.AWS.iam_role.external_id)}>📋</button>
                            </div>
                          </div>
                        )}
                        <div className="byoc-field">
                          <label>Role ARN</label>
                          <input type="text" placeholder="arn:aws:iam::123456789012:role/ZenithBYOC" value={awsForm.role_arn}
                            onChange={(e) => setAwsForm({...awsForm, role_arn: e.target.value})}
                            aria-invalid={!!byocValidation.errors.role_arn}
                            aria-describedby={byocValidation.errors.role_arn ? 'byoc-aws-role-error' : undefined} />
                          {byocValidation.errors.role_arn && <p id="byoc-aws-role-error" className="form-field-error">{byocValidation.errors.role_arn}</p>}
                        </div>
                        <div className="byoc-field">
                          <label>S3 Bucket Name</label>
                          <input type="text" placeholder="my-company-bucket" value={awsForm.bucket_name}
                            onChange={(e) => setAwsForm({...awsForm, bucket_name: e.target.value})} />
                        </div>
                        <div className="byoc-field">
                          <label>Region</label>
                          <select value={awsForm.region} onChange={(e) => setAwsForm({...awsForm, region: e.target.value})}>
                            <option value="ap-south-1">AP South 1 (Mumbai)</option>
                            <option value="us-east-1">US East 1 (Virginia)</option>
                            <option value="us-west-2">US West 2 (Oregon)</option>
                            <option value="eu-west-1">EU West 1 (Ireland)</option>
                          </select>
                        </div>
                        <p className="byoc-no-keys-note">✨ No access keys needed — Zenith assumes your role using temporary credentials that expire automatically.</p>
                      </div>
                    )}

                    {csp === 'GCP' && (
                      <div className="byoc-fields">
                        <div className="byoc-field">
                          <label>Service Account JSON</label>
                          <textarea placeholder='Paste your service account JSON key here...' rows="6"
                            value={gcpForm.service_account_json}
                            onChange={(e) => setGcpForm({...gcpForm, service_account_json: e.target.value})}
                            aria-invalid={!!byocValidation.errors.service_account_json}
                            aria-describedby={byocValidation.errors.service_account_json ? 'byoc-gcp-json-error' : undefined} />
                          {byocValidation.errors.service_account_json && <p id="byoc-gcp-json-error" className="form-field-error">{byocValidation.errors.service_account_json}</p>}
                        </div>
                        <div className="byoc-field">
                          <label>GCP Bucket Name</label>
                          <input type="text" placeholder="my-company-bucket" value={gcpForm.gcp_bucket_name}
                            onChange={(e) => setGcpForm({...gcpForm, gcp_bucket_name: e.target.value})}
                            aria-invalid={!!byocValidation.errors.gcp_bucket_name}
                            aria-describedby={byocValidation.errors.gcp_bucket_name ? 'byoc-gcp-bucket-error' : undefined} />
                          {byocValidation.errors.gcp_bucket_name && <p id="byoc-gcp-bucket-error" className="form-field-error">{byocValidation.errors.gcp_bucket_name}</p>}
                        </div>
                      </div>
                    )}

                    {csp === 'Azure' && (
                      <div className="byoc-fields">
                        <div className="byoc-field">
                          <label>Storage Account Name</label>
                          <input type="text" placeholder="mystorageaccount" value={azureForm.account_name}
                            onChange={(e) => setAzureForm({...azureForm, account_name: e.target.value})}
                            aria-invalid={!!byocValidation.errors.account_name}
                            aria-describedby={byocValidation.errors.account_name ? 'byoc-azure-account-error' : undefined} />
                          {byocValidation.errors.account_name && <p id="byoc-azure-account-error" className="form-field-error">{byocValidation.errors.account_name}</p>}
                        </div>
                        <div className="byoc-field">
                          <label>Storage Account Key</label>
                          <input type="password" placeholder="Your account key" value={azureForm.account_key}
                            onChange={(e) => setAzureForm({...azureForm, account_key: e.target.value})}
                            aria-invalid={!!byocValidation.errors.account_key}
                            aria-describedby={byocValidation.errors.account_key ? 'byoc-azure-key-error' : undefined} />
                          {byocValidation.errors.account_key && <p id="byoc-azure-key-error" className="form-field-error">{byocValidation.errors.account_key}</p>}
                        </div>
                        <div className="byoc-field">
                          <label>Container Name</label>
                          <input type="text" placeholder="my-container" value={azureForm.container_name}
                            onChange={(e) => setAzureForm({...azureForm, container_name: e.target.value})}
                            aria-invalid={!!byocValidation.errors.container_name}
                            aria-describedby={byocValidation.errors.container_name ? 'byoc-azure-container-error' : undefined} />
                          {byocValidation.errors.container_name && <p id="byoc-azure-container-error" className="form-field-error">{byocValidation.errors.container_name}</p>}
                        </div>
                      </div>
                    )}

                    {/* Test Result */}
                    {byocTestResult && (
                      <div className={`byoc-test-result ${byocTestResult.success ? 'success' : 'error'}`}>
                        {byocTestResult.success ? '✅' : '❌'} {byocTestResult.message}
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="byoc-actions">
                      <button className="btn-secondary" onClick={() => { setByocActiveCSP(null); setByocTestResult(null); }}>Cancel</button>
                      <button className="btn-test" onClick={handleByocTest} disabled={byocTesting || !byocValidation.isValid}>
                        {byocTesting ? '⏳ Testing...' : '🔍 Test Connection'}
                      </button>
                      <button className="btn-connect-save" onClick={handleByocConnect} disabled={byocConnecting || !byocValidation.isValid}>
                        {byocConnecting ? '⏳ Connecting...' : '🔗 Connect & Save'}
                      </button>
                    </div>

                    <p className="byoc-encryption-note">
                      🔒 Your credentials are encrypted with AES-256-GCM before storage. They are never logged or exposed in API responses.
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
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

      <div className="settings-content stagger-children">
        {/* BYOC Section — First for visibility */}
        {renderByocSection()}

        {/* Notifications Settings */}
        <div className="settings-card animate-fade-in-up">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 16a2 2 0 0 0 2-2H6a2 2 0 0 0 2 2zM8 1.918l-.797.161A4.002 4.002 0 0 0 4 6c0 .628-.134 2.197-.459 3.742-.16.767-.376 1.566-.663 2.258h10.244c-.287-.692-.502-1.49-.663-2.258C12.134 8.197 12 6.628 12 6a4.002 4.002 0 0 0-3.203-3.92L8 1.917zM14.22 12c.223.447.481.801.78 1H1c.299-.199.557-.553.78-1C2.68 10.2 3 6.88 3 6c0-2.42 1.72-4.44 4.005-4.901a1 1 0 1 1 1.99 0A5.002 5.002 0 0 1 13 6c0 .88.32 4.2 1.22 6z"/>
            </svg>
            Notifications
          </h3>
          <div className="settings-group">
            {Object.entries(notificationSettings).map(([key, value]) => {
              const config = notificationConfig[key];
              return (
                <div key={key} className={`setting-item ${config?.comingSoon ? 'setting-item-disabled' : ''}`}>
                  <div className="setting-info">
                    <h4>
                      {config?.label || key.replace(/([A-Z])/g, ' $1').trim()}
                      {config?.comingSoon && <span className="coming-soon-badge">Coming Soon</span>}
                    </h4>
                    <p>{config?.description || `Receive ${key.replace(/([A-Z])/g, ' $1').toLowerCase()} notifications`}</p>
                  </div>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={value}
                      onChange={() => handleNotificationChange(key)}
                      disabled={config?.comingSoon}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                </div>
              );
            })}
          </div>
        </div>

        {/* Preferences */}
        <div className="settings-card animate-fade-in-up">
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
              <select name="theme" value={preferences.theme} onChange={handlePreferenceChange} className="settings-select">
                <option value="dark">Dark</option>
                <option value="light">Light</option>
                <option value="auto">Auto (System)</option>
              </select>
            </div>
            <div className="setting-item-full setting-item-disabled-wrapper">
              <label>
                Language
                <span className="coming-soon-badge">Coming Soon</span>
              </label>
              <select name="language" value={preferences.language} onChange={handlePreferenceChange} className="settings-select" disabled>
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
            </div>
            <div className="setting-item-full">
              <label>Timezone</label>
              <select name="timezone" value={preferences.timezone} onChange={handlePreferenceChange} className="settings-select">
                <option value="UTC-8">Pacific Time (UTC-8)</option>
                <option value="UTC-5">Eastern Time (UTC-5)</option>
                <option value="UTC+0">UTC</option>
                <option value="UTC+5:30">India Standard Time (UTC+5:30)</option>
                <option value="UTC+1">Central European Time (UTC+1)</option>
              </select>
            </div>
            <div className="setting-item-full">
              <label>Date Format</label>
              <select name="dateFormat" value={preferences.dateFormat} onChange={handlePreferenceChange} className="settings-select">
                <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD</option>
              </select>
            </div>
            <div className="setting-item-full">
              <label>Currency</label>
              <select name="currency" value={preferences.currency} onChange={handlePreferenceChange} className="settings-select">
                <option value="USD">USD ($)</option>
                <option value="INR">INR (₹)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
          </div>
          <button className="btn-save" onClick={handleSavePreferences}>
            Save Preferences
          </button>
          <div className="setting-item-full" style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <div>
              <label>Onboarding Tour</label>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0' }}>
                Restart the guided walkthrough of Zenith's key features
              </p>
            </div>
            <button
              className="btn-save"
              style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--text-secondary)', border: '1px solid rgba(255,255,255,0.08)' }}
              onClick={() => {
                localStorage.removeItem('zenith_onboarding_complete');
                localStorage.removeItem('zenith_onboarding_dismissed');
                notifications.success('Tour will start on your next dashboard visit');
              }}
            >
              Restart Tour
            </button>
          </div>
        </div>

        {/* Billing & Plan — Honest free tier display */}
        <div className="settings-card animate-fade-in-up">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V4zm2-1a1 1 0 0 0-1 1v1h14V4a1 1 0 0 0-1-1H2zm13 4H1v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V7z"/>
              <path d="M2 10a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-1z"/>
            </svg>
            Plan & Billing
          </h3>
          <div className="free-plan-card">
            <div className="free-plan-header">
              <div className="free-plan-badge">
                <span className="plan-icon">✨</span>
                <span className="plan-name">Free Plan</span>
              </div>
              <span className="plan-price">$0<span className="plan-period">/month</span></span>
            </div>
            <p className="free-plan-description">
              All core features included for evaluation — storage management, cost analysis, VM monitoring, 2FA security, and more.
            </p>
            <div className="free-plan-features">
              <div className="feature-item">
                <span className="feature-check">✓</span>
                <span>Multi-cloud storage (AWS, GCP, Azure)</span>
              </div>
              <div className="feature-item">
                <span className="feature-check">✓</span>
                <span>Intelligent file placement & tiering</span>
              </div>
              <div className="feature-item">
                <span className="feature-check">✓</span>
                <span>2FA-protected secure vault</span>
              </div>
              <div className="feature-item">
                <span className="feature-check">✓</span>
                <span>Cost analysis & optimization</span>
              </div>
              <div className="feature-item">
                <span className="feature-check">✓</span>
                <span>VM cluster management</span>
              </div>
            </div>
          </div>
        </div>

        {/* API Keys */}
        <div className="settings-card animate-fade-in-up">
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
