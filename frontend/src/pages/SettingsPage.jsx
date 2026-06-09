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
import { Link } from 'react-router-dom';
import { useNotifications } from "../hooks/useNotifications";
import { useTheme } from "../context/ThemeContext";
import { usePreferences } from "../context/PreferencesContext";
import { apiClient } from '../api';
import LoadingSpinner from '../components/LoadingSpinner';
import {
  getValidationErrorMessage,
  validateByocConnectionForm,
  validateByocAwsStep1,
  validateByocAwsStep2,
  validateByocGcpStep1,
  validateByocAzureStep1,
} from '../utils/formValidation';
import '../styles/settings.css';
import PageHeader from '../components/ui/PageHeader.jsx';
import { usePageRefresh } from '../hooks/usePageRefresh.js';
import PlatformRegionPills from '../components/PlatformRegionPills.jsx';

const SettingsPage = () => {
  const notifications = useNotifications();
  const { executeWithNotification, showLoading, updateSuccess, updateError } = notifications;
  const { runPageRefresh, pageRefreshing } = usePageRefresh();
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
    provisionEngine: 'boto3',
    platformRegionSlug: '',
    defaultLifecyclePolicy: 'auto',
    lifecycleNoticeDays: 7,
    defaultSecurityEncryption: 'ask',
    alwaysAskEncryption: false,
    defaultSecurityCsp: 'AWS',
    defaultSecurityReplication: false,
    staleFileDays: 90,
    staleNoticeDays: 7,
    mlAssistedScan: true,
  });
  const [platformMultiRegion, setPlatformMultiRegion] = useState(false);
  const [platformRegions, setPlatformRegions] = useState([]);

  // BYOC State
  const [byocStatus, setByocStatus] = useState(null);
  const [byocEligible, setByocEligible] = useState(false);
  const [byocCurrentPlan, setByocCurrentPlan] = useState('free');
  const [subscription, setSubscription] = useState(null);
  const [byocActiveCSP, setByocActiveCSP] = useState(null); // Which CSP form is open
  const [byocMethod, setByocMethod] = useState('access_keys'); // access_keys or iam_role
  const [byocConnecting, setByocConnecting] = useState(false);
  const [byocTesting, setByocTesting] = useState(false);
  const [byocTestResult, setByocTestResult] = useState(null);
  const [showPolicy, setShowPolicy] = useState(false);
  const [policyTemplates, setPolicyTemplates] = useState(null);
  const [awsConnectStep, setAwsConnectStep] = useState(1);
  const [awsCredentialsVerified, setAwsCredentialsVerified] = useState(false);
  const [awsVerifying, setAwsVerifying] = useState(false);
  const [gcpConnectStep, setGcpConnectStep] = useState(1);
  const [gcpCredentialsVerified, setGcpCredentialsVerified] = useState(false);
  const [gcpVerifying, setGcpVerifying] = useState(false);
  const [gcpDiscoveredBuckets, setGcpDiscoveredBuckets] = useState([]);
  const [azureConnectStep, setAzureConnectStep] = useState(1);
  const [azureCredentialsVerified, setAzureCredentialsVerified] = useState(false);
  const [azureVerifying, setAzureVerifying] = useState(false);
  const [azureDiscoveredContainers, setAzureDiscoveredContainers] = useState([]);
  const [bucketCheckStatus, setBucketCheckStatus] = useState({});

  // BYOC Form fields
  const [awsForm, setAwsForm] = useState({
    access_key_id: '',
    secret_access_key: '',
    bucket_name: '',
    storage_bucket_name: '',
    secure_bucket_name: '',
    replica_bucket_name: '',
    secure_dual_write: true,
    region: 'ap-south-1',
    role_arn: '',
  });
  const [gcpForm, setGcpForm] = useState({
    service_account_json: '',
    gcp_bucket_name: '',
    storage_bucket_name: '',
    secure_bucket_name: '',
    replica_bucket_name: '',
    secure_dual_write: true,
    gcp_primary_location: 'ASIA-SOUTH1',
    gcp_replica_location: 'US-EAST1',
    gcp_billing_dataset_id: '',
    gcp_billing_table_id: '',
  });
  const [azureForm, setAzureForm] = useState({
    account_name: '',
    account_key: '',
    container_name: '',
    storage_container_name: '',
    secure_container_name: '',
    replica_container_name: '',
    secure_dual_write: true,
    azure_subscription_id: '',
    azure_tenant_id: '',
    azure_client_id: '',
    azure_client_secret: '',
  });

  const byocValidation = useMemo(
    () => {
      if (byocActiveCSP === 'AWS') {
        return awsConnectStep === 1
          ? validateByocAwsStep1({ method: byocMethod, awsForm })
          : validateByocAwsStep2({ awsForm });
      }
      if (byocActiveCSP === 'GCP') {
        return gcpConnectStep === 1
          ? validateByocGcpStep1({ gcpForm })
          : validateByocConnectionForm({
              csp: 'GCP',
              gcpForm,
              gcpStep: 2,
            });
      }
      if (byocActiveCSP === 'Azure') {
        return azureConnectStep === 1
          ? validateByocAzureStep1({ azureForm })
          : validateByocConnectionForm({
              csp: 'Azure',
              azureForm,
              azureStep: 2,
            });
      }
      return validateByocConnectionForm({
        csp: byocActiveCSP,
        method: byocMethod,
        awsForm,
        gcpForm,
        azureForm,
      });
    },
    [byocActiveCSP, byocMethod, awsForm, gcpForm, azureForm, awsConnectStep, gcpConnectStep, azureConnectStep]
  );

  const resetAwsConnectFlow = () => {
    setAwsConnectStep(1);
    setAwsCredentialsVerified(false);
    setBucketCheckStatus({});
    setByocTestResult(null);
  };

  const resetGcpConnectFlow = () => {
    setGcpConnectStep(1);
    setGcpCredentialsVerified(false);
    setGcpDiscoveredBuckets([]);
    setBucketCheckStatus({});
    setByocTestResult(null);
  };

  const resetAzureConnectFlow = () => {
    setAzureConnectStep(1);
    setAzureCredentialsVerified(false);
    setAzureDiscoveredContainers([]);
    setBucketCheckStatus({});
    setByocTestResult(null);
  };

  useEffect(() => {
    fetchSettings();
    fetchApiKeys();
    fetchByocStatus();
    fetchSubscription();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial load on mount
  }, []);

  const fetchSubscription = async () => {
    try {
      const response = await apiClient.get('/payments/my-subscription');
      setSubscription(response.data);
    } catch (error) {
      console.error('Failed to fetch subscription:', error);
      setSubscription({ plan_id: 'free', plan_name: 'Free Tier', status: 'active' });
    }
  };

  const planDisplay = useMemo(() => {
    const planId = subscription?.plan_id || 'free';
    const names = {
      free: 'Free Plan',
      basic: 'Basic Plan',
      pro: 'Pro Plan',
      enterprise: 'Enterprise Plan',
    };
    const prices = {
      free: { amount: '$0', period: '/month' },
      basic: { amount: '₹499', period: '/month' },
      pro: { amount: '₹1,499', period: '/month' },
      enterprise: { amount: '₹4,999', period: '/month' },
    };
    const icons = { free: '✨', basic: '⭐', pro: '🚀', enterprise: '👑' };
    return {
      planId,
      name: subscription?.plan_name || names[planId] || planId,
      ...prices[planId] || prices.free,
      icon: icons[planId] || '✨',
      isPaid: planId !== 'free',
    };
  }, [subscription]);

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
      
      const serverTheme = data.preferences?.theme;
      if (serverTheme && ['dark', 'light', 'auto'].includes(serverTheme)) {
        setTheme(serverTheme);
      }

      setPlatformMultiRegion(Boolean(data.platform_multi_region));
      setPlatformRegions(data.platform_regions || []);

      setPreferences(prev => ({
        ...prev,
        ...data.preferences,
        dateFormat: data.preferences?.date_format || data.preferences?.dateFormat || prev.dateFormat,
        theme: serverTheme && ['dark', 'light', 'auto'].includes(serverTheme) ? serverTheme : theme,
        provisionEngine: data.preferences?.provision_engine || prev.provisionEngine,
        platformRegionSlug:
          data.preferences?.platform_region_slug ||
          data.platform_regions?.[0]?.slug ||
          prev.platformRegionSlug,
        defaultLifecyclePolicy:
          data.preferences?.default_lifecycle_policy || prev.defaultLifecyclePolicy,
        lifecycleNoticeDays:
          data.preferences?.lifecycle_notice_days ?? prev.lifecycleNoticeDays,
        defaultSecurityEncryption:
          data.preferences?.default_security_encryption || prev.defaultSecurityEncryption,
        alwaysAskEncryption:
          data.preferences?.always_ask_encryption ?? prev.alwaysAskEncryption,
        defaultSecurityCsp:
          data.preferences?.default_security_csp || prev.defaultSecurityCsp,
        defaultSecurityReplication:
          data.preferences?.default_security_replication ?? prev.defaultSecurityReplication,
        staleFileDays: data.preferences?.stale_file_days ?? prev.staleFileDays,
        staleNoticeDays: data.preferences?.stale_notice_days ?? prev.staleNoticeDays,
        mlAssistedScan: data.preferences?.ml_assisted_scan ?? prev.mlAssistedScan,
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

  const handleGcpVerifyCredentials = async () => {
    if (!gcpForm.service_account_json?.trim()) {
      setByocTestResult({ success: false, message: 'Service account JSON is required.' });
      return;
    }
    setGcpVerifying(true);
    setByocTestResult(null);
    try {
      const response = await apiClient.post('/byoc/verify-credentials', {
        csp: 'GCP',
        connection_method: 'access_keys',
        service_account_json: gcpForm.service_account_json,
        gcp_bucket_name: gcpForm.gcp_bucket_name || undefined,
      });
      const suggestions = response.data.suggestions || {};
      setGcpDiscoveredBuckets(response.data.buckets || []);
      setGcpForm((prev) => ({
        ...prev,
        storage_bucket_name: suggestions.storage_bucket_name || prev.storage_bucket_name,
        gcp_bucket_name: suggestions.gcp_bucket_name || suggestions.storage_bucket_name || prev.gcp_bucket_name,
        secure_bucket_name: suggestions.secure_bucket_name || prev.secure_bucket_name,
        replica_bucket_name: suggestions.replica_bucket_name || prev.replica_bucket_name,
        gcp_primary_location: response.data.primary_location || prev.gcp_primary_location,
        gcp_replica_location: response.data.replica_location || prev.gcp_replica_location,
      }));
      setGcpCredentialsVerified(true);
      setGcpConnectStep(2);
      setByocTestResult({
        success: true,
        message: response.data.message || 'Credentials verified. Configure your buckets below.',
      });
    } catch (error) {
      const detail = error.response?.data?.detail;
      setByocTestResult({
        success: false,
        message: typeof detail === 'string' ? detail : detail?.message || 'Verification failed',
      });
    } finally {
      setGcpVerifying(false);
    }
  };

  const handleAzureVerifyCredentials = async () => {
    if (!azureForm.account_name?.trim() || !azureForm.account_key?.trim()) {
      setByocTestResult({ success: false, message: 'Storage account name and key are required.' });
      return;
    }
    setAzureVerifying(true);
    setByocTestResult(null);
    try {
      const response = await apiClient.post('/byoc/verify-credentials', {
        csp: 'Azure',
        connection_method: 'access_keys',
        account_name: azureForm.account_name,
        account_key: azureForm.account_key,
        container_name: azureForm.container_name || undefined,
        azure_subscription_id: azureForm.azure_subscription_id || undefined,
        azure_tenant_id: azureForm.azure_tenant_id || undefined,
        azure_client_id: azureForm.azure_client_id || undefined,
        azure_client_secret: azureForm.azure_client_secret || undefined,
      });
      const suggestions = response.data.suggestions || {};
      setAzureDiscoveredContainers(response.data.containers || []);
      setAzureForm((prev) => ({
        ...prev,
        storage_container_name: suggestions.storage_container_name || prev.storage_container_name,
        container_name: suggestions.container_name || suggestions.storage_container_name || prev.container_name,
        secure_container_name: suggestions.secure_container_name || prev.secure_container_name,
        replica_container_name: suggestions.replica_container_name || prev.replica_container_name,
      }));
      setAzureCredentialsVerified(true);
      setAzureConnectStep(2);
      const costNote = response.data.cost_management_verified
        ? ' Cost Management credentials OK.'
        : response.data.cost_management_message
          ? ` ${response.data.cost_management_message}`
          : '';
      setByocTestResult({
        success: true,
        message: (response.data.message || 'Azure credentials verified.') + costNote,
      });
    } catch (error) {
      const detail = error.response?.data?.detail;
      setByocTestResult({
        success: false,
        message: typeof detail === 'string' ? detail : detail?.message || 'Verification failed',
      });
    } finally {
      setAzureVerifying(false);
    }
  };

  const handleAwsVerifyCredentials = async () => {
    const step1 = validateByocAwsStep1({ method: byocMethod, awsForm });
    if (!step1.isValid) {
      setByocTestResult({ success: false, message: getValidationErrorMessage(step1.errors) });
      return;
    }
    setAwsVerifying(true);
    setByocTestResult(null);
    try {
      const payload = {
        csp: 'AWS',
        connection_method: byocMethod,
        region: awsForm.region,
        access_key_id: awsForm.access_key_id,
        secret_access_key: awsForm.secret_access_key,
        role_arn: awsForm.role_arn,
      };
      const response = await apiClient.post('/byoc/verify-credentials', payload);
      const suggestions = response.data.suggestions || {};
      setAwsForm((prev) => ({
        ...prev,
        storage_bucket_name: suggestions.storage_bucket_name || prev.storage_bucket_name,
        secure_bucket_name: suggestions.secure_bucket_name || prev.secure_bucket_name,
        replica_bucket_name: suggestions.replica_bucket_name || prev.replica_bucket_name,
        bucket_name: suggestions.storage_bucket_name || prev.bucket_name,
      }));
      setAwsCredentialsVerified(true);
      setAwsConnectStep(2);
      setByocTestResult({
        success: true,
        message: response.data.message || 'Credentials verified. Configure your buckets below.',
      });
    } catch (error) {
      const detail = error.response?.data?.detail;
      setByocTestResult({
        success: false,
        message: typeof detail === 'string' ? detail : detail?.message || 'Verification failed',
      });
    } finally {
      setAwsVerifying(false);
    }
  };

  const REPLICA_REGION = 'us-east-1';

  const bucketRoleForField = (field) => {
    if (field === 'replica_bucket_name') return 'replica';
    if (field === 'secure_bucket_name') return 'secure';
    return 'storage';
  };

  const regionForBucketField = (field, region) => {
    if (field === 'replica_bucket_name') return REPLICA_REGION;
    return region || awsForm.region;
  };

  const handleCheckAwsBucket = async (field, bucketName, region) => {
    if (!bucketName || !awsCredentialsVerified) return;
    const targetRegion = regionForBucketField(field, region);
    try {
      const response = await apiClient.post('/byoc/check-bucket-name', {
        bucket_name: bucketName,
        region: targetRegion,
        bucket_role: bucketRoleForField(field),
        connection_method: byocMethod,
        access_key_id: awsForm.access_key_id,
        secret_access_key: awsForm.secret_access_key,
        role_arn: awsForm.role_arn,
        create_if_missing: true,
      });
      setBucketCheckStatus((prev) => ({
        ...prev,
        [field]: response.data,
      }));
    } catch {
      setBucketCheckStatus((prev) => ({
        ...prev,
        [field]: { status: 'forbidden', message: 'Could not check bucket.' },
      }));
    }
  };

  const gcpBucketRoleForField = (field) => {
    if (field === 'replica_bucket_name') return 'replica';
    if (field === 'secure_bucket_name') return 'secure';
    return 'storage';
  };

  const handleCheckGcpBucket = async (field, bucketName) => {
    if (!bucketName || !gcpCredentialsVerified) return;
    const location =
      field === 'replica_bucket_name'
        ? gcpForm.gcp_replica_location
        : gcpForm.gcp_primary_location;
    try {
      const response = await apiClient.post('/byoc/check-gcp-bucket', {
        bucket_name: bucketName,
        bucket_role: gcpBucketRoleForField(field),
        location,
        service_account_json: gcpForm.service_account_json,
        create_if_missing: true,
      });
      setBucketCheckStatus((prev) => ({ ...prev, [field]: response.data }));
    } catch {
      setBucketCheckStatus((prev) => ({
        ...prev,
        [field]: { status: 'forbidden', message: 'Could not check bucket.' },
      }));
    }
  };

  const azureContainerRoleForField = (field) => {
    if (field === 'replica_container_name') return 'replica';
    if (field === 'secure_container_name') return 'secure';
    return 'storage';
  };

  const handleCheckAzureContainer = async (field, containerName) => {
    if (!containerName || !azureCredentialsVerified) return;
    try {
      const response = await apiClient.post('/byoc/check-azure-container', {
        container_name: containerName,
        container_role: azureContainerRoleForField(field),
        account_name: azureForm.account_name,
        account_key: azureForm.account_key,
        create_if_missing: true,
      });
      setBucketCheckStatus((prev) => ({ ...prev, [field]: response.data }));
    } catch {
      setBucketCheckStatus((prev) => ({
        ...prev,
        [field]: { status: 'forbidden', message: 'Could not check container.' },
      }));
    }
  };

  const handleByocConnect = async () => {
    if (!byocValidation.isValid) {
      setByocTestResult({ success: false, message: getValidationErrorMessage(byocValidation.errors) });
      return;
    }
    if (byocActiveCSP === 'AWS' && !awsCredentialsVerified) {
      setByocTestResult({ success: false, message: 'Verify your credentials first (Step 1).' });
      return;
    }
    if (byocActiveCSP === 'GCP' && !gcpCredentialsVerified) {
      setByocTestResult({ success: false, message: 'Verify your GCP service account first.' });
      return;
    }
    if (byocActiveCSP === 'Azure' && !azureCredentialsVerified) {
      setByocTestResult({ success: false, message: 'Verify your Azure storage credentials first.' });
      return;
    }

    setByocConnecting(true);
    try {
      let payload = { csp: byocActiveCSP, connection_method: byocMethod };
      if (byocActiveCSP === 'AWS') {
        payload = {
          ...payload,
          ...awsForm,
          primary_region: awsForm.region,
          replica_region: REPLICA_REGION,
          bucket_name: awsForm.storage_bucket_name || awsForm.bucket_name,
        };
      } else if (byocActiveCSP === 'GCP') {
        const storage = gcpForm.storage_bucket_name || gcpForm.gcp_bucket_name;
        Object.assign(payload, {
          ...gcpForm,
          gcp_bucket_name: storage,
          storage_bucket_name: storage,
        });
      } else if (byocActiveCSP === 'Azure') {
        const storage = azureForm.storage_container_name || azureForm.container_name;
        Object.assign(payload, {
          ...azureForm,
          container_name: storage,
          storage_container_name: storage,
        });
      }

      const response = await apiClient.post('/byoc/connect', payload);
      setByocActiveCSP(null);
      resetAwsConnectFlow();
      resetGcpConnectFlow();
      resetAzureConnectFlow();
      setByocTestResult({
        success: true,
        message: response.data.message || response.data.bucket_message || 'Connected successfully.',
      });
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
    } catch {
      notifications.error('Failed to update notifications');
      // Revert change
      setNotificationSettings(notificationSettings);
    }
  };

  const buildPreferencesPayload = (prefs) => ({
    theme: prefs.theme,
    language: prefs.language,
    timezone: prefs.timezone,
    date_format: prefs.dateFormat,
    currency: prefs.currency,
    provision_engine: prefs.provisionEngine,
    platform_region_slug: prefs.platformRegionSlug || null,
    default_lifecycle_policy: prefs.defaultLifecyclePolicy || 'auto',
    lifecycle_notice_days: Number(prefs.lifecycleNoticeDays) || 7,
    default_security_encryption: prefs.defaultSecurityEncryption || 'ask',
    always_ask_encryption: Boolean(prefs.alwaysAskEncryption),
    default_security_csp: prefs.defaultSecurityCsp || 'AWS',
    default_security_replication: Boolean(prefs.defaultSecurityReplication),
    stale_file_days: Number(prefs.staleFileDays) || 90,
    stale_notice_days: Number(prefs.staleNoticeDays) || 7,
    ml_assisted_scan: Boolean(prefs.mlAssistedScan),
  });

  const handlePreferenceChange = (e) => {
    const { name, value, type, checked } = e.target;
    const numericFields = new Set([
      'lifecycleNoticeDays',
      'staleFileDays',
      'staleNoticeDays',
    ]);
    const parsedValue =
      type === 'checkbox'
        ? checked
        : numericFields.has(name)
          ? Number(value)
          : value;
    const nextPreferences = { ...preferences, [name]: parsedValue };
    setPreferences(nextPreferences);

    // Apply theme immediately and persist so reload/login stay in sync
    if (name === 'theme') {
      setTheme(value);
      apiClient.put('/settings/preferences', {
        theme: value,
        language: nextPreferences.language,
        timezone: nextPreferences.timezone,
        date_format: nextPreferences.dateFormat,
        currency: nextPreferences.currency,
        provision_engine: nextPreferences.provisionEngine,
        platform_region_slug: nextPreferences.platformRegionSlug || null,
      }).catch(() => {
        notifications.error('Theme updated locally but failed to save to account');
      });
    }
    if (name === 'provisionEngine') {
      apiClient.put('/settings/preferences', {
        theme: nextPreferences.theme,
        language: nextPreferences.language,
        timezone: nextPreferences.timezone,
        date_format: nextPreferences.dateFormat,
        currency: nextPreferences.currency,
        provision_engine: value,
        platform_region_slug: nextPreferences.platformRegionSlug || null,
        default_lifecycle_policy: nextPreferences.defaultLifecyclePolicy || 'auto',
        lifecycle_notice_days: Number(nextPreferences.lifecycleNoticeDays) || 7,
      }).catch(() => {
        notifications.error('Failed to save provisioning engine preference');
      });
    }
    const autoSavePrefs = new Set([
      'defaultLifecyclePolicy',
      'lifecycleNoticeDays',
      'defaultSecurityEncryption',
      'alwaysAskEncryption',
      'defaultSecurityCsp',
      'defaultSecurityReplication',
      'staleFileDays',
      'staleNoticeDays',
      'mlAssistedScan',
    ]);
    if (autoSavePrefs.has(name)) {
      apiClient.put('/settings/preferences', buildPreferencesPayload(nextPreferences)).catch(() => {
        notifications.error('Failed to save preferences');
      });
    }
  };

  const handleSavePreferences = async () => {
    try {
      await executeWithNotification(
        async () => {
          await apiClient.put('/settings/preferences', buildPreferencesPayload(preferences));
          updatePreferences({
            currency: preferences.currency,
            dateFormat: preferences.dateFormat,
            timezone: preferences.timezone,
            platformRegionSlug: preferences.platformRegionSlug || null,
          });
        },
        {
          loadingMessage: 'Saving preferences…',
          successMessage: 'Preferences saved successfully!',
          errorMessage: 'Failed to save preferences',
        }
      );
    } catch {
      /* toast already shown */
    }
  };

  const handleGenerateApiKey = async () => {
    const loadingToastId = showLoading('Generating API key…');
    try {
      const response = await apiClient.post('/settings/api-keys');
      updateSuccess(loadingToastId, 'API key generated — copy it now; it will not be shown again.');
      notifications.success(
        <div>
          <strong>API Key Generated!</strong><br/>
          <code style={{fontSize: '0.85rem'}}>{response.data.key}</code><br/>
          <small>{response.data.note}</small>
        </div>,
        { autoClose: false }
      );
      fetchApiKeys();
    } catch {
      updateError(loadingToastId, 'Failed to generate API key');
    }
  };

  const handleRevokeApiKey = async (keyId) => {
    try {
      await executeWithNotification(
        async () => {
          await apiClient.delete(`/settings/api-keys/${keyId}`);
          await fetchApiKeys();
        },
        {
          loadingMessage: 'Revoking API key…',
          successMessage: 'API key revoked.',
          errorMessage: 'Failed to revoke API key',
        }
      );
    } catch {
      /* toast already shown */
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
        <div className="settings-card byoc-card">
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
      <div className="settings-card byoc-card">
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
                        <span className="byoc-status-connected">
                          ● Connected
                          {csp === 'AWS' && connection.storage_bucket_name ? (
                            <> — storage: {connection.storage_bucket_name}</>
                          ) : (
                            connection.bucket_name ? <> — {connection.bucket_name}</> : null
                          )}
                        </span>
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
                      resetAwsConnectFlow();
                      resetGcpConnectFlow();
                      resetAzureConnectFlow();
                      setByocMethod('access_keys');
                      if (!policyTemplates) fetchPolicyTemplates();
                    }}>Connect</button>
                  )}
                </div>

                {/* Expanded Connection Form */}
                {byocActiveCSP === csp && !isConnected && (
                  <div className="byoc-connect-form">
                    {(csp === 'AWS' || csp === 'GCP' || csp === 'Azure') && (
                      <div className="byoc-step-indicator">
                        <span
                          className={
                            (csp === 'AWS' && awsConnectStep === 1)
                            || (csp === 'GCP' && gcpConnectStep === 1)
                            || (csp === 'Azure' && azureConnectStep === 1)
                              ? 'active'
                              : (csp === 'AWS' && awsCredentialsVerified)
                                || (csp === 'GCP' && gcpCredentialsVerified)
                                || (csp === 'Azure' && azureCredentialsVerified)
                                ? 'done'
                                : ''
                          }
                        >
                          Step 1 — Verify credentials
                        </span>
                        <span
                          className={
                            (csp === 'AWS' && awsConnectStep === 2)
                            || (csp === 'GCP' && gcpConnectStep === 2)
                            || (csp === 'Azure' && azureConnectStep === 2)
                              ? 'active'
                              : ''
                          }
                        >
                          Step 2 — {csp === 'Azure' ? 'Container' : 'Bucket'} configuration
                        </span>
                      </div>
                    )}
                    {/* Method Selection */}
                    <div className="byoc-method-selector">
                      <button
                        className={`method-btn ${byocMethod === 'access_keys' ? 'active' : ''}`}
                        onClick={() => { setByocMethod('access_keys'); resetAwsConnectFlow(); }}
                      >
                        <span className="method-icon">🔑</span>
                        <span className="method-label">Quick Setup</span>
                        <span className="method-risk risk-medium">⚠️ Medium Risk</span>
                      </button>
                      <button
                        className={`method-btn ${byocMethod === 'iam_role' ? 'active' : ''}`}
                        onClick={() => { setByocMethod('iam_role'); resetAwsConnectFlow(); }}
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
                    {csp === 'AWS' && byocMethod === 'access_keys' && awsConnectStep === 1 && (
                      <div className="byoc-fields">
                        <p className="byoc-field-hint">
                          Enter your AWS keys. We will verify them before asking for bucket names.
                          Create buckets in AWS (or use the suggested names in Step 2).
                        </p>
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
                          <label>Primary region (storage + secure buckets)</label>
                          <select className="zenith-select" value={awsForm.region} onChange={(e) => setAwsForm({...awsForm, region: e.target.value})}>
                            <option value="ap-south-1">AP South 1 (Mumbai)</option>
                            <option value="us-east-1">US East 1 (Virginia)</option>
                            <option value="us-west-2">US West 2 (Oregon)</option>
                            <option value="eu-west-1">EU West 1 (Ireland)</option>
                          </select>
                        </div>
                      </div>
                    )}

                    {csp === 'AWS' && awsConnectStep === 2 && (
                      <div className="byoc-fields">
                        <p className="byoc-field-hint">
                          Confirm bucket names below. Zenith will create any that do not exist yet in your AWS account
                          (primary region: {awsForm.region}; replica in <strong>US East (N. Virginia)</strong>).
                        </p>
                        {[
                          { field: 'storage_bucket_name', label: 'Storage bucket', region: awsForm.region },
                          { field: 'secure_bucket_name', label: 'Secure vault bucket', region: awsForm.region },
                          ...(awsForm.secure_dual_write
                            ? [{ field: 'replica_bucket_name', label: 'Secure replica bucket (Virginia)', region: 'us-east-1' }]
                            : []),
                        ].map(({ field, label, region }) => (
                          <div className="byoc-field" key={field}>
                            <label>{label}</label>
                            <input
                              type="text"
                              value={awsForm[field]}
                              onChange={(e) => setAwsForm({ ...awsForm, [field]: e.target.value, bucket_name: field === 'storage_bucket_name' ? e.target.value : awsForm.bucket_name })}
                              onBlur={() => handleCheckAwsBucket(field, awsForm[field], region)}
                              aria-invalid={!!byocValidation.errors[field]}
                            />
                            {byocValidation.errors[field] && (
                              <p className="form-field-error">{byocValidation.errors[field]}</p>
                            )}
                            {bucketCheckStatus[field] && (
                              <p className={`byoc-bucket-check byoc-bucket-check--${bucketCheckStatus[field].status}`}>
                                {bucketCheckStatus[field].message}
                              </p>
                            )}
                          </div>
                        ))}
                        <div className="byoc-field byoc-field-checkbox">
                          <label>
                            <input
                              type="checkbox"
                              checked={awsForm.secure_dual_write}
                              onChange={(e) => setAwsForm({ ...awsForm, secure_dual_write: e.target.checked })}
                            />
                            Replicate secure files to replica bucket (recommended)
                          </label>
                        </div>
                        <button type="button" className="btn-back-step" onClick={() => setAwsConnectStep(1)}>
                          ← Back to credentials
                        </button>
                      </div>
                    )}

                    {csp === 'AWS' && byocMethod === 'iam_role' && awsConnectStep === 1 && (
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
                          <label>Primary region</label>
                          <select className="zenith-select" value={awsForm.region} onChange={(e) => setAwsForm({...awsForm, region: e.target.value})}>
                            <option value="ap-south-1">AP South 1 (Mumbai)</option>
                            <option value="us-east-1">US East 1 (Virginia)</option>
                            <option value="us-west-2">US West 2 (Oregon)</option>
                            <option value="eu-west-1">EU West 1 (Ireland)</option>
                          </select>
                        </div>
                        <p className="byoc-no-keys-note">✨ No access keys stored — Zenith assumes your role with temporary credentials.</p>
                      </div>
                    )}

                    {csp === 'GCP' && gcpConnectStep === 1 && (
                      <div className="byoc-fields">
                        <p className="byoc-field-hint">
                          Paste your GCP service account JSON. We will verify it before asking for bucket names.
                        </p>
                        <div className="byoc-field">
                          <label>Service Account JSON</label>
                          <textarea placeholder='Paste your service account JSON key here...' rows="6"
                            value={gcpForm.service_account_json}
                            onChange={(e) => setGcpForm({...gcpForm, service_account_json: e.target.value})}
                            aria-invalid={!!byocValidation.errors.service_account_json}
                            aria-describedby={byocValidation.errors.service_account_json ? 'byoc-gcp-json-error' : undefined} />
                          {byocValidation.errors.service_account_json && <p id="byoc-gcp-json-error" className="form-field-error">{byocValidation.errors.service_account_json}</p>}
                        </div>
                      </div>
                    )}

                    {csp === 'GCP' && gcpConnectStep === 2 && (
                      <div className="byoc-fields">
                        <p className="byoc-field-hint">
                          Confirm bucket names below. Zenith will create any that do not exist yet in your GCP project
                          (primary: {gcpForm.gcp_primary_location}; replica: {gcpForm.gcp_replica_location}).
                        </p>
                        {[
                          { field: 'storage_bucket_name', label: 'Storage bucket', location: gcpForm.gcp_primary_location },
                          { field: 'secure_bucket_name', label: 'Secure vault bucket', location: gcpForm.gcp_primary_location },
                          ...(gcpForm.secure_dual_write
                            ? [{ field: 'replica_bucket_name', label: 'Secure replica bucket', location: gcpForm.gcp_replica_location }]
                            : []),
                        ].map(({ field, label, location }) => (
                          <div className="byoc-field" key={field}>
                            <label>{label}</label>
                            <input
                              type="text"
                              value={gcpForm[field]}
                              onChange={(e) => setGcpForm({
                                ...gcpForm,
                                [field]: e.target.value,
                                gcp_bucket_name: field === 'storage_bucket_name' ? e.target.value : gcpForm.gcp_bucket_name,
                              })}
                              onBlur={() => handleCheckGcpBucket(field, gcpForm[field])}
                              aria-invalid={!!byocValidation.errors[field]}
                            />
                            {byocValidation.errors[field] && (
                              <p className="form-field-error">{byocValidation.errors[field]}</p>
                            )}
                            {bucketCheckStatus[field] && (
                              <p className={`byoc-bucket-check byoc-bucket-check--${bucketCheckStatus[field].status}`}>
                                {bucketCheckStatus[field].message}
                              </p>
                            )}
                            <p className="byoc-field-hint">Location: {location}</p>
                          </div>
                        ))}
                        <div className="byoc-field byoc-field-checkbox">
                          <label>
                            <input
                              type="checkbox"
                              checked={gcpForm.secure_dual_write}
                              onChange={(e) => setGcpForm({ ...gcpForm, secure_dual_write: e.target.checked })}
                            />
                            Replicate secure files to replica bucket (recommended)
                          </label>
                        </div>
                        <p className="byoc-section-hint">Optional — live billing in Cost hub (BigQuery export)</p>
                        <div className="byoc-field">
                          <label>Billing dataset ID</label>
                          <input type="text" placeholder="billing_export" value={gcpForm.gcp_billing_dataset_id}
                            onChange={(e) => setGcpForm({ ...gcpForm, gcp_billing_dataset_id: e.target.value })} />
                        </div>
                        <div className="byoc-field">
                          <label>Billing table ID</label>
                          <input type="text" placeholder="gcp_billing_export_v1_XXXXX" value={gcpForm.gcp_billing_table_id}
                            onChange={(e) => setGcpForm({ ...gcpForm, gcp_billing_table_id: e.target.value })} />
                        </div>
                        <button type="button" className="btn-back-step" onClick={() => setGcpConnectStep(1)}>
                          ← Back to credentials
                        </button>
                      </div>
                    )}

                    {csp === 'Azure' && azureConnectStep === 1 && (
                      <div className="byoc-fields">
                        <p className="byoc-field-hint">
                          Enter your Azure storage account credentials. We will verify them before asking for container names.
                        </p>
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
                      </div>
                    )}

                    {csp === 'Azure' && azureConnectStep === 2 && (
                      <div className="byoc-fields">
                        <p className="byoc-field-hint">
                          Confirm container names below. Zenith will create any that do not exist yet in your storage account.
                        </p>
                        {[
                          { field: 'storage_container_name', label: 'Storage container' },
                          { field: 'secure_container_name', label: 'Secure vault container' },
                          ...(azureForm.secure_dual_write
                            ? [{ field: 'replica_container_name', label: 'Secure replica container' }]
                            : []),
                        ].map(({ field, label }) => (
                          <div className="byoc-field" key={field}>
                            <label>{label}</label>
                            <input
                              type="text"
                              value={azureForm[field]}
                              onChange={(e) => setAzureForm({
                                ...azureForm,
                                [field]: e.target.value,
                                container_name: field === 'storage_container_name' ? e.target.value : azureForm.container_name,
                              })}
                              onBlur={() => handleCheckAzureContainer(field, azureForm[field])}
                              aria-invalid={!!byocValidation.errors[field]}
                            />
                            {byocValidation.errors[field] && (
                              <p className="form-field-error">{byocValidation.errors[field]}</p>
                            )}
                            {bucketCheckStatus[field] && (
                              <p className={`byoc-bucket-check byoc-bucket-check--${bucketCheckStatus[field].status}`}>
                                {bucketCheckStatus[field].message}
                              </p>
                            )}
                          </div>
                        ))}
                        <div className="byoc-field byoc-field-checkbox">
                          <label>
                            <input
                              type="checkbox"
                              checked={azureForm.secure_dual_write}
                              onChange={(e) => setAzureForm({ ...azureForm, secure_dual_write: e.target.checked })}
                            />
                            Replicate secure files to replica container (recommended)
                          </label>
                        </div>
                        <p className="byoc-section-hint">Optional — Cost Management API (separate from storage key)</p>
                        <div className="byoc-field">
                          <label>Subscription ID</label>
                          <input type="text" value={azureForm.azure_subscription_id}
                            onChange={(e) => setAzureForm({ ...azureForm, azure_subscription_id: e.target.value })} />
                        </div>
                        <div className="byoc-field">
                          <label>Tenant ID</label>
                          <input type="text" value={azureForm.azure_tenant_id}
                            onChange={(e) => setAzureForm({ ...azureForm, azure_tenant_id: e.target.value })} />
                        </div>
                        <div className="byoc-field">
                          <label>Cost reader client ID</label>
                          <input type="text" value={azureForm.azure_client_id}
                            onChange={(e) => setAzureForm({ ...azureForm, azure_client_id: e.target.value })} />
                        </div>
                        <div className="byoc-field">
                          <label>Cost reader client secret</label>
                          <input type="password" value={azureForm.azure_client_secret}
                            onChange={(e) => setAzureForm({ ...azureForm, azure_client_secret: e.target.value })} />
                        </div>
                        <button type="button" className="btn-back-step" onClick={() => setAzureConnectStep(1)}>
                          ← Back to credentials
                        </button>
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
                      <button className="btn-secondary" onClick={() => {
                        setByocActiveCSP(null);
                        resetAwsConnectFlow();
                        resetGcpConnectFlow();
                        resetAzureConnectFlow();
                      }}>Cancel</button>
                      {(byocActiveCSP === 'AWS' && awsConnectStep === 1)
                      || (byocActiveCSP === 'GCP' && gcpConnectStep === 1)
                      || (byocActiveCSP === 'Azure' && azureConnectStep === 1) ? (
                        <button
                          className="btn-connect-save"
                          type="button"
                          onClick={
                            byocActiveCSP === 'AWS'
                              ? handleAwsVerifyCredentials
                              : byocActiveCSP === 'GCP'
                                ? handleGcpVerifyCredentials
                                : handleAzureVerifyCredentials
                          }
                          disabled={
                            (byocActiveCSP === 'AWS' && (awsVerifying || !byocValidation.isValid))
                            || (byocActiveCSP === 'GCP' && (gcpVerifying || !byocValidation.isValid))
                            || (byocActiveCSP === 'Azure' && (azureVerifying || !byocValidation.isValid))
                          }
                        >
                          {(awsVerifying || gcpVerifying || azureVerifying) ? '⏳ Verifying...' : '✓ Verify & continue'}
                        </button>
                      ) : (
                        <button
                          className="btn-connect-save"
                          onClick={handleByocConnect}
                          disabled={
                            byocConnecting
                            || !byocValidation.isValid
                            || (byocActiveCSP === 'AWS' && !awsCredentialsVerified)
                            || (byocActiveCSP === 'GCP' && !gcpCredentialsVerified)
                            || (byocActiveCSP === 'Azure' && !azureCredentialsVerified)
                          }
                        >
                          {byocConnecting ? '⏳ Connecting...' : '🔗 Complete connection'}
                        </button>
                      )}
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
      <PageHeader
        kicker="Workspace"
        title="Settings"
        subtitle="Manage your application preferences and configurations"
        onRefresh={() =>
          runPageRefresh(
            async () => {
              await fetchSettings();
              await fetchApiKeys();
            },
            {
              loadingMessage: 'Refreshing settings…',
              successMessage: 'Settings page refreshed.',
              errorMessage: 'Failed to refresh settings.',
            }
          )
        }
        refreshing={pageRefreshing}
      />

      <div className="settings-content stagger-children">
        {/* BYOC Section — First for visibility */}
        {renderByocSection()}

        {/* Notifications Settings */}
        <div className="settings-card">
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

        {/* Secure vault defaults */}
        <div className="settings-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1a2 2 0 0 1 2 2v4.5A1.5 1.5 0 0 0 11.5 9h1A1.5 1.5 0 0 1 14 10.5V13a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-2.5A1.5 1.5 0 0 1 3.5 9h1A1.5 1.5 0 0 0 6 7.5V3a2 2 0 0 1 2-2z"/>
            </svg>
            Secure vault defaults
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Defaults for secure uploads, stale-file reminders, and ML-assisted scanning.
          </p>
          <div className="settings-group">
            <div className="setting-item-full">
              <label>Default encryption</label>
              <select
                name="defaultSecurityEncryption"
                value={preferences.defaultSecurityEncryption}
                onChange={handlePreferenceChange}
                className="zenith-select settings-select"
              >
                <option value="ask">Ask me each time</option>
                <option value="server-side">Cloud-managed</option>
                <option value="client-side">Browser encryption</option>
              </select>
            </div>
            <div className="setting-item-full">
              <label>
                <input
                  type="checkbox"
                  name="alwaysAskEncryption"
                  checked={preferences.alwaysAskEncryption}
                  onChange={handlePreferenceChange}
                />{' '}
                Always ask before encrypting
              </label>
            </div>
            <div className="setting-item-full">
              <label>Default cloud</label>
              <select
                name="defaultSecurityCsp"
                value={preferences.defaultSecurityCsp}
                onChange={handlePreferenceChange}
                className="zenith-select settings-select"
              >
                <option value="AWS">AWS</option>
                <option value="GCP">Google Cloud</option>
                <option value="Azure">Azure</option>
              </select>
            </div>
            <div className="setting-item-full">
              <label>
                <input
                  type="checkbox"
                  name="defaultSecurityReplication"
                  checked={preferences.defaultSecurityReplication}
                  onChange={handlePreferenceChange}
                />{' '}
                Enable replication by default (AWS/GCP)
              </label>
            </div>
            <div className="setting-item-full">
              <label>Stale file reminder after (days)</label>
              <select
                name="staleFileDays"
                value={String(preferences.staleFileDays)}
                onChange={handlePreferenceChange}
                className="zenith-select settings-select"
              >
                <option value="60">60 days</option>
                <option value="90">90 days (default)</option>
                <option value="120">120 days</option>
                <option value="180">180 days</option>
              </select>
            </div>
            <div className="setting-item-full">
              <label>Notice before stale action (days)</label>
              <select
                name="staleNoticeDays"
                value={String(preferences.staleNoticeDays)}
                onChange={handlePreferenceChange}
                className="zenith-select settings-select"
              >
                <option value="0">0 — health bar only</option>
                <option value="3">3 days</option>
                <option value="7">7 days (default)</option>
                <option value="14">14 days</option>
              </select>
            </div>
            <div className="setting-item-full">
              <label>
                <input
                  type="checkbox"
                  name="mlAssistedScan"
                  checked={preferences.mlAssistedScan}
                  onChange={handlePreferenceChange}
                />{' '}
                ML-assisted sensitive scan (alongside rules)
              </label>
            </div>
          </div>
        </div>

        {/* Storage lifecycle defaults */}
        <div className="settings-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1a2 2 0 0 1 2 2v1h1.5A1.5 1.5 0 0 1 13 5.5v8A1.5 1.5 0 0 1 11.5 15h-7A1.5 1.5 0 0 1 3 13.5v-8A1.5 1.5 0 0 1 4.5 4H6V3a2 2 0 0 1 2-2zm0 1a1 1 0 0 0-1 1v1h2V3a1 1 0 0 0-1-1zM4.5 5a.5.5 0 0 0-.5.5v8a.5.5 0 0 0 .5.5h7a.5.5 0 0 0 .5-.5v-8a.5.5 0 0 0-.5-.5h-7z"/>
            </svg>
            Storage lifecycle
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Defaults for new uploads. Zenith notifies you before moving files to cheaper tiers unless
            notice period is 0 days.
          </p>
          <div className="settings-group">
            <div className="setting-item-full">
              <label>Default policy for new files</label>
              <select
                name="defaultLifecyclePolicy"
                value={preferences.defaultLifecyclePolicy}
                onChange={handlePreferenceChange}
                className="zenith-select settings-select"
              >
                <option value="auto">Auto-optimize (recommended)</option>
                <option value="keep_hot">Keep fast access</option>
                <option value="aggressive">Archive aggressively</option>
                <option value="manual">Suggest only — no automatic moves</option>
              </select>
            </div>
            <div className="setting-item-full">
              <label>Notice period before tier move (days)</label>
              <select
                name="lifecycleNoticeDays"
                value={String(preferences.lifecycleNoticeDays)}
                onChange={handlePreferenceChange}
                className="zenith-select settings-select"
              >
                <option value="0">0 — move immediately after notify</option>
                <option value="3">3 days</option>
                <option value="7">7 days (default)</option>
                <option value="14">14 days</option>
              </select>
            </div>
          </div>
        </div>

        {/* Infrastructure provisioning engine */}
        <div className="settings-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zM2.5 2a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3zm6.5.5A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm1.5-.5a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3zM1 10.5A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm1.5-.5a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3zm6.5.5A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3zm1.5-.5a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3z"/>
            </svg>
            Infrastructure provisioning
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Choose how new stacks are deployed. Boto3 is fast and works on Render free tier.
            Terraform provides full IaC with state (best on localhost or Render Docker).
          </p>
          <div className="settings-group">
            <div className="setting-item-full">
              <label>Deploy engine</label>
              <select
                name="provisionEngine"
                value={preferences.provisionEngine}
                onChange={handlePreferenceChange}
                className="zenith-select settings-select"
              >
                <option value="boto3">Boto3 — fast (recommended for Render)</option>
                <option value="terraform">Terraform — full plan &amp; state</option>
              </select>
            </div>
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
              <select name="theme" value={preferences.theme} onChange={handlePreferenceChange} className="zenith-select settings-select">
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
              <select name="language" value={preferences.language} onChange={handlePreferenceChange} className="zenith-select settings-select" disabled>
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
            </div>
            <div className="setting-item-full">
              <label>Timezone</label>
              <select name="timezone" value={preferences.timezone} onChange={handlePreferenceChange} className="zenith-select settings-select">
                <option value="UTC-8">Pacific Time (UTC-8)</option>
                <option value="UTC-5">Eastern Time (UTC-5)</option>
                <option value="UTC+0">UTC</option>
                <option value="UTC+5:30">India Standard Time (UTC+5:30)</option>
                <option value="UTC+1">Central European Time (UTC+1)</option>
              </select>
            </div>
            <div className="setting-item-full">
              <label>Date Format</label>
              <select name="dateFormat" value={preferences.dateFormat} onChange={handlePreferenceChange} className="zenith-select settings-select">
                <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD</option>
              </select>
            </div>
            <div className="setting-item-full">
              <label>Currency</label>
              <select name="currency" value={preferences.currency} onChange={handlePreferenceChange} className="zenith-select settings-select">
                <option value="USD">USD ($)</option>
                <option value="INR">INR (₹)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
            {platformMultiRegion && platformRegions.length > 1 && (
              <div className="setting-item-full settings-platform-region">
                <label>Default platform region</label>
                <p className="settings-hint">
                  Used for Storage uploads, sync, and other platform services. You can override
                  per session on the Storage page.
                </p>
                <PlatformRegionPills
                  regions={platformRegions}
                  selectedSlug={preferences.platformRegionSlug}
                  onSelect={(slug) => {
                    setPreferences((prev) => ({ ...prev, platformRegionSlug: slug }));
                  }}
                  id="settings-platform-region"
                  hideLabel
                />
              </div>
            )}
          </div>
          <button className="btn-save" onClick={handleSavePreferences}>
            Save Preferences
          </button>
          <div className="setting-item setting-item--action settings-tour-row">
            <div className="setting-info">
              <h4>Onboarding Tour</h4>
              <p>Restart the guided walkthrough of Zenith&apos;s key features</p>
            </div>
            <button
              type="button"
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

        {/* Plan & Billing — loaded from /payments/my-subscription (same DB as Billing page) */}
        <div className="settings-card">
          <h3>
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M0 4a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V4zm2-1a1 1 0 0 0-1 1v1h14V4a1 1 0 0 0-1-1H2zm13 4H1v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V7z"/>
              <path d="M2 10a1 1 0 0 1 1-1h1a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-1z"/>
            </svg>
            Plan & Billing
          </h3>
          <div className={`free-plan-card current-plan-card plan-${planDisplay.planId}`}>
            <div className="free-plan-header">
              <div className="free-plan-badge">
                <span className="plan-icon">{planDisplay.icon}</span>
                <span className="plan-name">{planDisplay.name}</span>
              </div>
              <span className="plan-price">
                {planDisplay.amount}
                <span className="plan-period">{planDisplay.period}</span>
              </span>
            </div>
            <p className="free-plan-description">
              {planDisplay.isPaid
                ? `Your Zenith subscription is active (${subscription?.status || 'active'}). BYOC, billing, and limits follow this plan.`
                : 'Core features for evaluation — upgrade to Pro or Enterprise for BYOC and higher limits.'}
            </p>
            {subscription?.vm_limit != null && (
              <p className="free-plan-description" style={{ marginTop: 0 }}>
                Includes up to {subscription.vm_limit >= 999 ? 'unlimited' : subscription.vm_limit} VMs
                {' · '}
                {subscription.storage_gb >= 1000
                  ? `${subscription.storage_gb / 1000} TB`
                  : `${subscription.storage_gb} GB`}{' '}
                storage per VM
              </p>
            )}
            <div className="settings-plan-actions">
              <Link to="/dashboard/billing" className="btn-save" style={{ textDecoration: 'none', display: 'inline-block' }}>
                Manage billing →
              </Link>
              {!planDisplay.isPaid && (
                <Link to="/dashboard/pricing" className="btn-save" style={{ textDecoration: 'none', display: 'inline-block', marginLeft: '0.75rem', background: 'rgba(255,255,255,0.06)' }}>
                  View plans
                </Link>
              )}
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
