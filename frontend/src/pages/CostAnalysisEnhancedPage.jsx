// =============================================================================
// PAGE: CostAnalysisEnhancedPage.jsx  (716 lines)
// ROUTE: /dashboard/costs
// PURPOSE: Advanced cost analytics — interactive time-range charts, per-service breakdown,
//          Z-score anomaly detection highlights, decay-weighted forecast graph, CSV export
// API: Uses apiClient → /api/cost/cost-data, /api/cost/anomalies, /api/cost/forecast, /api/cost/export/csv
// CONTEXTS: PreferencesContext (currencySymbol for all displayed values)
// DO NOT:
//   - Hardcode "$" — always use PreferencesContext.currencySymbol
//   - Remove the anomaly highlight layer — it's a key differentiator from basic cost page
//   - Change CSV export format — ops team depends on the column order
// =============================================================================
import React, { useState, useEffect } from 'react';
import { apiClient, getApiErrorMessage } from '../api.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useNotifications } from "../hooks/useNotifications";
import { usePreferences } from '../context/PreferencesContext.jsx';
import PageHeader from '../components/ui/PageHeader.jsx';
import PageContainer from '../components/ui/PageContainer.jsx';
import { usePageRefresh } from '../hooks/usePageRefresh.js';
import CostHubNav from '../components/dashboard/CostHubNav.jsx';
import {
  IconAlert,
  IconActivity,
  IconBarChart,
  IconDownload,
} from '../components/dashboard/Icons.jsx';
import '../styles/costanalysis.css';
import CloudCapabilityBanner from '../components/cloud/CloudCapabilityBanner.jsx';
import FeatureLockedState from '../components/cloud/FeatureLockedState.jsx';
import CredentialSourceBadge from '../components/cloud/CredentialSourceBadge.jsx';
import {
  useCloudAvailability,
  CSP_TO_COST_KEY,
  COST_KEY_TO_CSP,
} from '../hooks/useCloudAvailability.js';
import { usePlanEntitlementsContext } from '../context/PlanEntitlementsContext.jsx';
import PlanUpgradeGate from '../components/billing/PlanUpgradeGate.jsx';
import { NAV_ID_LABELS, MIN_PLAN_LABELS } from '../config/planNavConfig.js';
import { PATHS } from '../data/productFacts.js';
import { Link } from 'react-router-dom';
import CloudProviderLogo from '../components/cloud/CloudProviderLogo.jsx';

const ProviderLogo = ({ provider }) => (
  <CloudProviderLogo provider={provider} className="provider-logo" />
);

const CostAnalysisEnhancedPage = () => {
  const { user } = useAuth();
  const notifications = useNotifications();
  const { formatCurrency } = usePreferences();
  const { runPageRefresh, pageRefreshing } = usePageRefresh();
  const { getFeature, getLockedProviders, getCredentialSource } = useCloudAvailability();
  const { isFeatureEnabled, planName, getNavMeta, openUpgradeDrawer } = usePlanEntitlementsContext();
  const costProviderKeys = (getFeature('cost').providers || []).map((p) => CSP_TO_COST_KEY[p]).filter(Boolean);
  const lockedCostProviders = getLockedProviders('cost');
  const costFullyBlocked = !costProviderKeys.length && lockedCostProviders.length > 0;

  useEffect(() => {
    if (user?.username) {
      localStorage.setItem(`zenith_visited_costs_${user.username}`, '1');
    }
  }, [user?.username]);

  // Core state
  const [selectedProvider, setSelectedProvider] = useState('aws');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [granularity, setGranularity] = useState('DAILY');
  const [costData, setCostData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [totalCost, setTotalCost] = useState(0);
  const [costByService, setCostByService] = useState([]);
  
  // Budget state
  const [budgets, setBudgets] = useState([]);
  const [showBudgetForm, setShowBudgetForm] = useState(false);
  const [budgetForm, setBudgetForm] = useState({
    name: '',
    amount: '',
    provider: 'all',
    period: 'monthly',
    alert_threshold: 80,
    phone_number: ''
  });
  
  // Forecast state
  const [forecast, setForecast] = useState(null);
  const [showForecast, setShowForecast] = useState(false);
  
  // Anomaly state
  const [anomalies, setAnomalies] = useState([]);
  const [anomalySummary, setAnomalySummary] = useState(null);
  const [showAnomalies, setShowAnomalies] = useState(false);
  const [billingStatus, setBillingStatus] = useState(null);
  const [storageMetering, setStorageMetering] = useState(null);
  const [providerSetup, setProviderSetup] = useState(null);
  const [setupForm, setSetupForm] = useState({
    billing_dataset_id: '',
    billing_table_id: '',
    subscription_id: '',
    tenant_id: '',
    client_id: '',
    client_secret: '',
  });
  const [savingSetup, setSavingSetup] = useState(false);

  const fetchBillingStatus = async () => {
    try {
      const res = await apiClient.get('/cost/billing-status');
      setBillingStatus(res.data);
    } catch {
      setBillingStatus(null);
    }
  };

  const fetchStorageMetering = async () => {
    try {
      const res = await apiClient.get('/billing/storage-metering');
      setStorageMetering(res.data);
    } catch {
      setStorageMetering(null);
    }
  };

  // Set default dates (last 30 days)
  useEffect(() => {
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    setEndDate(today.toISOString().split('T')[0]);
    setStartDate(thirtyDaysAgo.toISOString().split('T')[0]);
    
    // Load budgets and anomalies on mount
    fetchBudgets();
    fetchAnomalies();
    fetchAnomalySummary();
    fetchBillingStatus();
    fetchStorageMetering();
  }, []);

  const fetchProviderSetup = async (provider) => {
    if (provider === 'aws') {
      setProviderSetup(null);
      return;
    }
    try {
      const res = await apiClient.get(`/cost/setup/${provider}`);
      setProviderSetup(res.data);
      if (provider === 'gcp') {
        setSetupForm((f) => ({
          ...f,
          billing_dataset_id: res.data.billing_dataset_id || '',
          billing_table_id: res.data.billing_table_id || '',
        }));
      } else if (provider === 'azure') {
        setSetupForm((f) => ({
          ...f,
          subscription_id: res.data.subscription_id || '',
          tenant_id: res.data.tenant_id || '',
          client_id: res.data.client_id || '',
          client_secret: '',
        }));
      }
    } catch {
      setProviderSetup(null);
    }
  };

  useEffect(() => {
    if (costProviderKeys.length && !costProviderKeys.includes(selectedProvider)) {
      setSelectedProvider(costProviderKeys[0]);
    }
  }, [costProviderKeys, selectedProvider]);

  useEffect(() => {
    fetchProviderSetup(selectedProvider);
  }, [selectedProvider]);

  const saveProviderSetup = async (e) => {
    e.preventDefault();
    setSavingSetup(true);
    try {
      if (selectedProvider === 'gcp') {
        await apiClient.put('/cost/setup/gcp', {
          billing_dataset_id: setupForm.billing_dataset_id,
          billing_table_id: setupForm.billing_table_id,
        });
      } else if (selectedProvider === 'azure') {
        const body = {
          subscription_id: setupForm.subscription_id,
          tenant_id: setupForm.tenant_id,
          client_id: setupForm.client_id,
        };
        if (setupForm.client_secret) body.client_secret = setupForm.client_secret;
        await apiClient.put('/cost/setup/azure', body);
      }
      notifications.success('Billing settings saved.');
      await fetchProviderSetup(selectedProvider);
      await fetchBillingStatus();
    } catch (error) {
      notifications.error(getApiErrorMessage(error, 'Failed to save billing settings.'));
    } finally {
      setSavingSetup(false);
    }
  };

  // Quick date presets
  const applyDatePreset = (preset) => {
    const today = new Date();
    let start = new Date();
    
    switch(preset) {
      case 'last7days':
        start.setDate(today.getDate() - 7);
        break;
      case 'last30days':
        start.setDate(today.getDate() - 30);
        break;
      case 'last90days':
        start.setDate(today.getDate() - 90);
        break;
      case 'ytd':
        start = new Date(today.getFullYear(), 0, 1);
        break;
      case 'lastMonth': {
        start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        const endOfLastMonth = new Date(today.getFullYear(), today.getMonth(), 0);
        setEndDate(endOfLastMonth.toISOString().split('T')[0]);
        setStartDate(start.toISOString().split('T')[0]);
        return;
      }
      default:
        return;
    }
    
    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(today.toISOString().split('T')[0]);
  };

  // Fetch cost data
  const fetchCostData = async () => {
    if (!startDate || !endDate) {
      notifications.error('Please select both start and end dates');
      return;
    }

    setLoading(true);
    try {
      let response;
      
      if (selectedProvider === 'aws') {
        response = await apiClient.get('/cost/aws', {
          params: {
            start_date: startDate,
            end_date: endDate,
            granularity: granularity,
            group_by_dimension: ['SERVICE']
          }
        });
      } else if (selectedProvider === 'gcp') {
        response = await apiClient.get('/cost/gcp', {
          params: {
            start_date: startDate,
            end_date: endDate
          }
        });
      } else if (selectedProvider === 'azure') {
        response = await apiClient.get('/cost/azure', {
          params: {
            start_date: startDate,
            end_date: endDate
          }
        });
      }

      setCostData(response.data);
      processCostData(response.data);
      const cfg = response.data?.data?.status;
      if (cfg === 'missing_config' || cfg === 'missing_dependency') {
        notifications.info(
          getApiErrorMessage(
            { detail: response.data?.data },
            `${selectedProvider.toUpperCase()} billing is not configured yet.`
          )
        );
      } else {
        notifications.success(`${selectedProvider.toUpperCase()} cost data loaded successfully`);
      }
    } catch (error) {
      console.error('Error fetching cost data:', error);
      notifications.error(getApiErrorMessage(error, 'Failed to fetch cost data'));
      setCostData(null);
    } finally {
      setLoading(false);
    }
  };

  // Process cost data
  const processCostData = (data) => {
    // Check for error/placeholder responses
    if (data?.data?.status === 'not_configured' || data?.data?.status === 'missing_config' || 
        data?.data?.status === 'missing_dependency' || data?.data?.status === 'error') {
      setTotalCost(data?.data?.estimated_cost || 0);
      setCostByService([]);
      return;
    }

    // Handle unified format (ResultsByTime for AWS/GCP/Azure)
    if (!data?.data?.ResultsByTime) {
      setTotalCost(0);
      setCostByService([]);
      return;
    }

    let total = 0;
    const serviceMap = {};

    // Process time series data
    data.data.ResultsByTime.forEach((timeRange) => {
      if (timeRange.Groups && timeRange.Groups.length > 0) {
        timeRange.Groups.forEach((group) => {
          const serviceName = group.Keys?.[0] || 'Unknown Service';
          const costAmount = group.Metrics?.UnblendedCost?.Amount || group.Metrics?.BlendedCost?.Amount || '0';
          const cost = parseFloat(costAmount);

          if (serviceMap[serviceName]) {
            serviceMap[serviceName] += cost;
          } else {
            serviceMap[serviceName] = cost;
          }
          total += cost;
        });
      } else {
        const cost = parseFloat(timeRange.Total.UnblendedCost.Amount);
        
        // Since we don't have service breakdown, add to a generic "Storage Services" entry
        const genericService = 'Storage Services';
        if (serviceMap[genericService]) {
          serviceMap[genericService] += cost;
        } else {
          serviceMap[genericService] = cost;
        }
        
        total += cost;
      }
    });

    // For GCP/Azure, if Services array is provided, use it instead
    if (data?.data?.Services && data.data.Services.length > 0) {
      data.data.Services.forEach(svc => {
        serviceMap[svc.service || svc.name] = svc.cost;
      });
      total = data.data.TotalCost || total;
    }

    setTotalCost(total);

    const serviceArray = Object.entries(serviceMap)
      .map(([service, cost]) => ({ name: service, cost: cost }))
      .sort((a, b) => b.cost - a.cost)
      .slice(0, 10);

    setCostByService(serviceArray);
  };

  // Budget functions
  const fetchBudgets = async () => {
    try {
      const response = await apiClient.get('/budgets/status');
      setBudgets(response.data);
    } catch (error) {
      console.error('Error fetching budgets:', error);
    }
  };

  const createBudget = async (e) => {
    e.preventDefault();
    try {
      await apiClient.post('/budgets/', {
        ...budgetForm,
        amount: parseFloat(budgetForm.amount),
        email_notifications: true
      });
      notifications.success('Budget created successfully');
      setShowBudgetForm(false);
      setBudgetForm({ name: '', amount: '', provider: 'all', period: 'monthly', alert_threshold: 80, phone_number: '' });
      fetchBudgets();
    } catch (error) {
      notifications.error(error.response?.data?.detail || 'Failed to create budget');
    }
  };

  const deleteBudget = async (budgetId) => {
    try {
      await apiClient.delete(`/budgets/${budgetId}`);
      notifications.success('Budget deleted');
      fetchBudgets();
    } catch (_error) {
      notifications.error('Failed to delete budget');
    }
  };

  const testSMS = async () => {
    if (!budgetForm.phone_number) {
      notifications.error('Please enter a phone number first');
      return;
    }
    try {
      await apiClient.post(`/budgets/test-sms?phone_number=${encodeURIComponent(budgetForm.phone_number)}&budget_name=Test Alert`);
      notifications.success(`SMS sent successfully to ${budgetForm.phone_number}`);
    } catch (error) {
      notifications.error(error.response?.data?.detail || 'Failed to send test SMS');
    }
  };

  // Forecast functions
  const fetchForecast = async () => {
    try {
      const response = await apiClient.get(`/cost/forecast/${selectedProvider}`, {
        params: { days_ahead: 30 }
      });
      setForecast(response.data);
      setShowForecast(true);
    } catch (error) {
      notifications.error(error.response?.data?.detail || 'Failed to fetch forecast');
    }
  };

  const fetchDemoForecast = async () => {
    try {
      notifications.info('Loading ML demo with synthetic data...');
      const response = await apiClient.get(`/cost/forecast/${selectedProvider}`, {
        params: { days_ahead: 30, demo_mode: true }
      });
      setForecast(response.data);
      setShowForecast(true);
      notifications.success('ML model demo loaded! This uses 90 days of synthetic data with increasing trend.');
    } catch (error) {
      notifications.error(error.response?.data?.detail || 'Failed to fetch demo forecast');
    }
  };

  // Anomaly functions
  const fetchAnomalies = async () => {
    try {
      const response = await apiClient.get('/cost/anomalies', {
        params: { acknowledged: false }
      });
      setAnomalies(response.data);
    } catch (error) {
      console.error('Error fetching anomalies:', error);
    }
  };

  const fetchAnomalySummary = async () => {
    try {
      const response = await apiClient.get('/cost/anomalies/summary');
      setAnomalySummary(response.data);
    } catch (error) {
      console.error('Error fetching anomaly summary:', error);
      // Set empty summary if unauthorized or error
      setAnomalySummary({ total: 0, unacknowledged: 0, critical: 0, warning: 0, anomalies: [] });
    }
  };

  const acknowledgeAnomaly = async (anomalyId) => {
    try {
      await apiClient.put(`/cost/anomalies/${anomalyId}/acknowledge`);
      notifications.success('Anomaly acknowledged');
      fetchAnomalies();
      fetchAnomalySummary();
    } catch (_error) {
      notifications.error('Failed to acknowledge anomaly');
    }
  };

  // Export functions
  const exportReport = async (format) => {
    try {
      const response = await apiClient.get(`/cost/export/${selectedProvider}`, {
        params: {
          start_date: startDate,
          end_date: endDate,
          format: format
        },
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${selectedProvider}_cost_report_${startDate}_${endDate}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      notifications.success(`Report exported as ${format.toUpperCase()}`);
    } catch (_error) {
      notifications.error('Failed to export report');
    }
  };

  return (
    <PageContainer className="cost-analysis-container">
      <PageHeader
        kicker="Cost intelligence"
        title="Cost Analysis"
        subtitle="Monitor and optimize your multi-cloud spending"
        onRefresh={() =>
          runPageRefresh(
            async () => {
              await fetchBillingStatus();
              await fetchStorageMetering();
              await fetchBudgets();
              if (startDate && endDate) {
                await fetchCostData();
              }
              if (showForecast) {
                await fetchForecast();
              }
              await fetchAnomalies();
            },
            {
              loadingMessage: 'Refreshing cost analysis…',
              successMessage: 'Cost analysis page refreshed.',
              errorMessage: 'Failed to refresh cost analysis.',
            }
          )
        }
        refreshing={pageRefreshing || loading}
      />
      <CostHubNav />
      {!isFeatureEnabled('live_billing') && (
        <div className="dashboard-demo-banner" role="status">
          <span>Free plan — live cost refresh is disabled. Charts may show demo or cached sample data.</span>
          <Link to={PATHS.pricing}>Upgrade for live billing</Link>
        </div>
      )}
      <CloudCapabilityBanner
        feature="cost"
        lockedProviders={lockedCostProviders}
        className="cost-capability-banner"
      />
      {costFullyBlocked && (
        <FeatureLockedState
          featureLabel="Cost analysis"
          lockedProviders={lockedCostProviders}
          className="cost-feature-locked"
        />
      )}
      {storageMetering?.estimated_usd && (
        <div className="storage-metering-cost-banner zenith-surface" role="status">
          <h3 className="storage-metering-cost-title">Storage API metering (this month)</h3>
          <p className="storage-metering-cost-desc">
            Pass-through estimate for list buckets, sync, upload, and download calls from the Storage page.
          </p>
          <div className="storage-metering-cost-pills">
            <span>AWS: {formatCurrency(storageMetering.estimated_usd.AWS || 0, 6)}</span>
            <span>GCP: {formatCurrency(storageMetering.estimated_usd.GCP || 0, 6)}</span>
            <span>Azure: {formatCurrency(storageMetering.estimated_usd.Azure || 0, 6)}</span>
            <strong>Total: {formatCurrency(storageMetering.estimated_usd.total || 0, 6)}</strong>
          </div>
        </div>
      )}
      {billingStatus?.providers && (
        <div className="billing-connectivity-banner" role="status">
          {(costProviderKeys.length ? costProviderKeys : ['aws', 'gcp', 'azure']).map((key) => {
            const p = billingStatus.providers[key];
            const label = COST_KEY_TO_CSP[key] || key.toUpperCase();
            const ok = p?.live;
            return (
              <span key={key} className={`billing-pill ${ok ? 'live' : 'offline'}`}>
                <ProviderLogo provider={key} />
                {label}: {ok ? 'Live' : p?.status || 'Setup needed'}
              </span>
            );
          })}
          {billingStatus.demo_mode && (
            <span className="billing-pill demo">Demo mode — sample billing data</span>
          )}
        </div>
      )}

      {providerSetup && !providerSetup.configured && selectedProvider !== 'aws' && (
        <div className="billing-setup-panel zenith-surface">
          <h3>
            {selectedProvider === 'gcp' ? 'GCP BigQuery billing export' : 'Azure Cost Management'}
          </h3>
          <p className="billing-setup-lead">
            Complete these steps, then save IDs on your BYOC record (requires an active{' '}
            {selectedProvider.toUpperCase()} BYOC connection) or set platform{' '}
            <code>.env</code> on the server.
          </p>
          <ol className="billing-setup-steps">
            {(providerSetup.setup_steps || []).map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          {providerSetup.can_update_via_api ? (
            <form className="billing-setup-form" onSubmit={saveProviderSetup}>
              {selectedProvider === 'gcp' ? (
                <>
                  <input
                    type="text"
                    placeholder="Billing dataset ID"
                    value={setupForm.billing_dataset_id}
                    onChange={(e) =>
                      setSetupForm({ ...setupForm, billing_dataset_id: e.target.value })
                    }
                    required
                  />
                  <input
                    type="text"
                    placeholder="Billing table ID (gcp_billing_export_v1_…)"
                    value={setupForm.billing_table_id}
                    onChange={(e) =>
                      setSetupForm({ ...setupForm, billing_table_id: e.target.value })
                    }
                    required
                  />
                </>
              ) : (
                <>
                  <input
                    type="text"
                    placeholder="Subscription ID"
                    value={setupForm.subscription_id}
                    onChange={(e) =>
                      setSetupForm({ ...setupForm, subscription_id: e.target.value })
                    }
                    required
                  />
                  <input
                    type="text"
                    placeholder="Tenant ID"
                    value={setupForm.tenant_id}
                    onChange={(e) => setSetupForm({ ...setupForm, tenant_id: e.target.value })}
                    required
                  />
                  <input
                    type="text"
                    placeholder="Client ID (app ID)"
                    value={setupForm.client_id}
                    onChange={(e) => setSetupForm({ ...setupForm, client_id: e.target.value })}
                    required
                  />
                  <input
                    type="password"
                    placeholder={
                      providerSetup.has_client_secret
                        ? 'Client secret (leave blank to keep existing)'
                        : 'Client secret'
                    }
                    value={setupForm.client_secret}
                    onChange={(e) =>
                      setSetupForm({ ...setupForm, client_secret: e.target.value })
                    }
                  />
                </>
              )}
              <button type="submit" className="fetch-button" disabled={savingSetup}>
                {savingSetup ? 'Saving…' : 'Save billing settings'}
              </button>
            </form>
          ) : (
            <p className="billing-setup-note">
              Connect {selectedProvider.toUpperCase()} under BYOC to save billing fields here, or
              ask your operator to set deployment environment variables.
            </p>
          )}
        </div>
      )}

      <div className="cost-provider-meta">
        <CredentialSourceBadge
          source={getCredentialSource(COST_KEY_TO_CSP[selectedProvider], 'cost')}
        />
      </div>
      {selectedProvider !== 'aws' && (
        <p className="cost-api-note" role="note">
          Service breakdown uses provider-native APIs for {selectedProvider.toUpperCase()}.{' '}
          <strong>Group-by dimensions</strong> (Cost Explorer style) apply to <strong>AWS only</strong>.
        </p>
      )}
      {/* Anomaly Alerts Banner */}
      {isFeatureEnabled('ai_recommendations') && anomalySummary && anomalySummary.total_unacknowledged > 0 && (
        <div className="anomaly-banner">
          <span className="anomaly-icon"><IconAlert aria-hidden="true" /></span>
          <span>
            <strong>{anomalySummary.total_unacknowledged} cost anomal{anomalySummary.total_unacknowledged === 1 ? 'y' : 'ies'} detected!</strong>
            {anomalySummary.by_severity.critical > 0 && ` (${anomalySummary.by_severity.critical} critical)`}
          </span>
          <button type="button" onClick={() => setShowAnomalies(!showAnomalies)} className="anomaly-toggle-btn">
            {showAnomalies ? 'Hide' : 'View'} Details
          </button>
        </div>
      )}

      {/* Anomalies Panel */}
      {isFeatureEnabled('ai_recommendations') && showAnomalies && (
        <div className="anomalies-panel">
          <h3>Cost Anomalies</h3>
          {anomalies.length === 0 ? (
            <p>No unacknowledged anomalies</p>
          ) : (
            <div className="anomalies-list">
              {anomalies.map(anomaly => (
                <div key={anomaly.id} className={`anomaly-card ${anomaly.severity}`}>
                  <div className="anomaly-header">
                    <span className="anomaly-provider">{anomaly.provider.toUpperCase()}</span>
                    <span className={`anomaly-severity ${anomaly.severity}`}>{anomaly.severity}</span>
                  </div>
                  <div className="anomaly-details">
                    <p><strong>Date:</strong> {anomaly.date}</p>
                    <p><strong>Cost:</strong> ${anomaly.cost.toFixed(2)} (Expected: ${anomaly.expected_cost.toFixed(2)})</p>
                    <p><strong>Deviation:</strong> {anomaly.deviation_percentage.toFixed(1)}%</p>
                  </div>
                  <button type="button" onClick={() => acknowledgeAnomaly(anomaly.id)} className="acknowledge-btn">
                    Acknowledge
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Budget Section */}
      <div className="budgets-section">
        <div className="section-header">
          <h3>Budget Alerts</h3>
          <button type="button" onClick={() => setShowBudgetForm(!showBudgetForm)} className="create-budget-btn">
            {showBudgetForm ? 'Cancel' : '+ Create Budget'}
          </button>
        </div>

        {showBudgetForm && (
          <form onSubmit={createBudget} className="budget-form">
            <input
              type="text"
              placeholder="Budget Name"
              value={budgetForm.name}
              onChange={(e) => setBudgetForm({...budgetForm, name: e.target.value})}
              required
            />
            <input
              type="number"
              placeholder="Amount ($)"
              value={budgetForm.amount}
              onChange={(e) => setBudgetForm({...budgetForm, amount: e.target.value})}
              required
              min="0"
              step="0.01"
            />
            <select className="zenith-select" value={budgetForm.provider} onChange={(e) => setBudgetForm({...budgetForm, provider: e.target.value})}>
              <option value="all">All Providers</option>
              <option value="aws">AWS</option>
              <option value="gcp">GCP</option>
              <option value="azure">Azure</option>
            </select>
            <select className="zenith-select" value={budgetForm.period} onChange={(e) => setBudgetForm({...budgetForm, period: e.target.value})}>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="yearly">Yearly</option>
            </select>
            <input
              type="number"
              placeholder="Alert Threshold (%)"
              value={budgetForm.alert_threshold}
              onChange={(e) => setBudgetForm({...budgetForm, alert_threshold: parseInt(e.target.value)})}
              min="0"
              max="100"
            />
            <input
              type="tel"
              placeholder="Phone Number (optional, e.g., +1234567890)"
              value={budgetForm.phone_number}
              onChange={(e) => setBudgetForm({...budgetForm, phone_number: e.target.value})}
              pattern="\+[0-9]{10,15}"
              title="Phone number must start with + and include country code (e.g., +1234567890)"
            />
            <div className="budget-form-actions">
              <button type="submit" className="submit-budget-btn">Create Budget</button>
              {budgetForm.phone_number && (
                <button type="button" onClick={testSMS} className="test-sms-btn">Test SMS</button>
              )}
            </div>
          </form>
        )}

        <div className="budgets-grid">
          {budgets.map(budgetStatus => (
            <div key={budgetStatus.budget.id} className={`budget-card ${budgetStatus.is_exceeded ? 'exceeded' : budgetStatus.is_near_limit ? 'warning' : ''}`}>
              <div className="budget-header">
                <h4>{budgetStatus.budget.name}</h4>
                <button
                  type="button"
                  onClick={() => deleteBudget(budgetStatus.budget.id)}
                  className="delete-budget-btn"
                  aria-label={`Delete budget ${budgetStatus.budget.name}`}
                >
                  ×
                </button>
              </div>
              <div className="budget-info">
                <p className="budget-amount">${budgetStatus.budget.current_spend.toFixed(2)} / ${budgetStatus.budget.amount.toFixed(2)}</p>
                <p className="budget-period">{budgetStatus.budget.period} • {budgetStatus.budget.provider.toUpperCase()}</p>
              </div>
              <div className="budget-progress">
                <div 
                  className="budget-progress-bar" 
                  style={{width: `${Math.min(budgetStatus.utilization_percentage, 100)}%`}}
                ></div>
              </div>
              <p className="budget-remaining">
                {budgetStatus.is_exceeded ? 'Budget exceeded!' : `$${budgetStatus.remaining_amount.toFixed(2)} remaining`}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Date Presets */}
      <div className="date-presets">
        <button type="button" onClick={() => applyDatePreset('last7days')}>Last 7 Days</button>
        <button type="button" onClick={() => applyDatePreset('last30days')}>Last 30 Days</button>
        <button type="button" onClick={() => applyDatePreset('last90days')}>Last 90 Days</button>
        <button type="button" onClick={() => applyDatePreset('lastMonth')}>Last Month</button>
        <button type="button" onClick={() => applyDatePreset('ytd')}>Year to Date</button>
      </div>

      {/* Filters */}
      <div className="cost-filters">
        <div className="filter-group">
          <label>Provider</label>
          <select className="zenith-select filter-select" value={selectedProvider} onChange={(e) => setSelectedProvider(e.target.value)}>
            {(costProviderKeys.length ? costProviderKeys : ['aws']).map((key) => (
              <option key={key} value={key}>
                {key === 'aws' ? 'AWS' : key === 'gcp' ? 'Google Cloud' : 'Azure'}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label>End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label>Granularity {selectedProvider !== 'aws' && '(AWS only)'}</label>
          <select
            className="zenith-select filter-select"
            value={granularity}
            onChange={(e) => setGranularity(e.target.value)}
            disabled={selectedProvider !== 'aws'}
            title={selectedProvider !== 'aws' ? 'Granularity applies to AWS Cost Explorer only' : ''}
          >
            <option value="DAILY">Daily</option>
            <option value="MONTHLY">Monthly</option>
          </select>
        </div>

        <button type="button" onClick={fetchCostData} disabled={loading} className="fetch-button">
          {loading ? 'Loading...' : 'Fetch Data'}
        </button>
      </div>

      {/* Action Buttons */}
      <div className="action-buttons">
        {isFeatureEnabled('ai_recommendations') ? (
          <>
            <button type="button" onClick={fetchForecast} className="forecast-btn">
              <IconBarChart aria-hidden="true" />
              View Forecast
            </button>
            <button type="button" onClick={fetchDemoForecast} className="forecast-btn" title="Test ML model with synthetic data">
              <IconActivity aria-hidden="true" />
              Demo ML
            </button>
          </>
        ) : (
          <button
            type="button"
            className="forecast-btn"
            onClick={() => openUpgradeDrawer('cost_optimization')}
          >
            <IconBarChart aria-hidden="true" />
            Forecast (Pro)
          </button>
        )}
        <button type="button" onClick={() => exportReport('csv')} disabled={!costData} className="export-btn">
          <IconDownload aria-hidden="true" />
          Export CSV
        </button>
        <button type="button" onClick={() => exportReport('json')} disabled={!costData} className="export-btn">
          <IconDownload aria-hidden="true" />
          Export JSON
        </button>
      </div>

      {/* Forecast Panel */}
      {!isFeatureEnabled('ai_recommendations') && showForecast && (
        <PlanUpgradeGate
          featureLabel={NAV_ID_LABELS.cost_optimization}
          currentPlan={planName}
          requiredPlan={MIN_PLAN_LABELS[getNavMeta('cost_optimization')?.min_plan] || 'Pro'}
          requiredPlanId={getNavMeta('cost_optimization')?.min_plan || 'pro'}
          compact
        />
      )}
      {isFeatureEnabled('ai_recommendations') && showForecast && forecast && (
        <div className="forecast-panel">
          <div className="forecast-header">
            <h3>Cost Forecast - Next 30 Days</h3>
            <button type="button" onClick={() => setShowForecast(false)} className="close-btn" aria-label="Close forecast panel">×</button>
          </div>
          <div className="forecast-summary">
            <div className="forecast-card">
              <h4>Predicted Total</h4>
              <p className="forecast-value">${forecast.total_forecast.toFixed(2)}</p>
            </div>
            <div className="forecast-card">
              <h4>Daily Average</h4>
              <p className="forecast-value">${forecast.average_daily_cost.toFixed(2)}</p>
            </div>
            <div className="forecast-card">
              <h4>Trend</h4>
              <p className="forecast-value">{forecast.trend === 'increasing' ? '📈 Increasing' : '📉 Decreasing'}</p>
            </div>
            <div className="forecast-card">
              <h4>Confidence Range</h4>
              <p className="forecast-value">${forecast.confidence_interval.lower.toFixed(2)} - ${forecast.confidence_interval.upper.toFixed(2)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Cost Summary */}
      {costData && (
        <div className="cost-summary">
          <div className="summary-card">
            <ProviderLogo provider={selectedProvider} />
            <div className="summary-content">
              <h3>Total Cost</h3>
              <p className="cost-value">${totalCost.toFixed(2)}</p>
            </div>
          </div>

          <div className="summary-card">
            <span className="summary-icon"><IconBarChart aria-hidden="true" /></span>
            <div className="summary-content">
              <h3>Daily Average</h3>
              <p className="cost-value">
                ${(totalCost / Math.max(1, costData.data.ResultsByTime?.length || 1)).toFixed(2)}
              </p>
            </div>
          </div>

          <div className="summary-card">
            <span className="summary-icon">🔧</span>
            <div className="summary-content">
              <h3>Services</h3>
              <p className="cost-value">{costByService.length}</p>
            </div>
          </div>
        </div>
      )}

      {/* Cost Breakdown */}
      {costByService.length > 0 && (
        <div className="cost-breakdown">
          <h3>Cost by Service</h3>
          <div className="table-responsive-scroll">
          <table className="cost-table data-card-table">
            <thead>
              <tr>
                <th>Service</th>
                <th>Cost</th>
                <th>Percentage</th>
              </tr>
            </thead>
            <tbody>
              {costByService.map((service, index) => (
                <tr key={index}>
                  <td data-label="Service">{service.name}</td>
                  <td data-label="Cost">${parseFloat(service.cost).toFixed(2)}</td>
                  <td data-label="Percentage">{((parseFloat(service.cost) / totalCost) * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {/* Time Series Display */}
      {costData && costData.data.ResultsByTime && (
        <div className="time-series">
          <h2>Cost Over Time</h2>
          <div className="time-series-list">
            {costData.data.ResultsByTime.map((item, index) => {
              const cost = parseFloat(item.Total?.UnblendedCost?.Amount || 0);
              const startDate = item.TimePeriod?.Start || '';
              
              return (
                <div key={index} className="time-entry">
                  <span className="time-date">{startDate}</span>
                  <span className="time-cost">${cost.toFixed(2)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </PageContainer>
  );
};

export default CostAnalysisEnhancedPage;
