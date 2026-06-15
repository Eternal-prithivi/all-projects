// =============================================================================
// PAGE: DashboardPage.jsx
// ROUTE: /dashboard (default landing after login)
// PURPOSE: Mission Control bento-grid overview — live stats, cost sparkline,
//          storage breakdown, quick actions, greeting banner
// API: /api/dashboard/stats, /cost-trend, /recent-activity, /refresh-costs
// =============================================================================
import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { usePreferences } from "../context/PreferencesContext.jsx";
import { getDashboardStats, apiClient } from "../api.js";
import StatCard from "../components/dashboard/StatCard.jsx";
import SparklineChart from "../components/dashboard/SparklineChart.jsx";
import ProgressRing from "../components/dashboard/ProgressRing.jsx";
import LoadingSpinner from "../components/LoadingSpinner.jsx";
import EmptyState from "../components/EmptyState.jsx";
import {
  IconDollarSign,
  IconServer,
  IconHardDrive,
  IconShieldCheck,
  IconRefresh,
  IconUploadCloud,
  IconBarChart,
  IconActivity,
  IconAlert,
} from "../components/dashboard/Icons.jsx";
import { useNavigate } from 'react-router-dom';
import { useNotifications } from "../hooks/useNotifications.js";
import PageHeader from "../components/ui/PageHeader.jsx";
import PageContainer from "../components/ui/PageContainer.jsx";
import { usePageRefresh } from "../hooks/usePageRefresh.js";
import { useCountUp } from "../hooks/useCountUp.js";
import { DashboardSkeleton } from "../components/Skeletons.jsx";
import { PATHS } from "../data/productFacts.js";
import { usePlanEntitlementsContext } from "../context/PlanEntitlementsContext.jsx";
import { useCloudAvailabilityContext } from "../context/CloudAvailabilityContext.jsx";
import { Link } from "react-router-dom";
import '../styles/dashboard-enhanced.css';

// ─── Getting Started checklist ──────────────────────────────────────────────
const GS_DISMISS_KEY = (username) => `zenith_gs_dismissed_${username || ''}`;

const GS_STEPS = [
  {
    id: 'connect_cloud',
    label: 'Connect your cloud',
    description: 'Link AWS, GCP, or Azure credentials to unlock cost analysis and storage.',
    path: '/dashboard/settings#byoc',
    icon: '☁️',
  },
  {
    id: 'analyze_costs',
    label: 'Analyze your costs',
    description: 'View multi-cloud spend broken down by service, region, and date range.',
    path: '/dashboard/costs',
    icon: '📊',
  },
  {
    id: 'upload_file',
    label: 'Upload a file',
    description: 'Our ML engine picks the cheapest cloud tier for every file you store.',
    path: '/dashboard/storage',
    icon: '📁',
  },
  {
    id: 'request_vm',
    label: 'Request a VM cluster',
    description: 'Describe your workload in plain English — the NLP engine handles the rest.',
    path: '/dashboard/vmcluster',
    icon: '🖥️',
  },
];

function GettingStartedCard({ username, stats, byocConnected }) {
  const navigate = useNavigate();
  const [dismissed, setDismissed] = React.useState(
    () => !!localStorage.getItem(GS_DISMISS_KEY(username)),
  );

  if (dismissed) return null;

  const completed = {
    connect_cloud: byocConnected?.length > 0,
    analyze_costs: !!localStorage.getItem(`zenith_visited_costs_${username}`),
    upload_file: (stats?.total_files || 0) > 0,
    request_vm: (stats?.active_vms || 0) > 0,
  };

  const doneCount = Object.values(completed).filter(Boolean).length;
  const pct = Math.round((doneCount / GS_STEPS.length) * 100);

  const handleDismiss = () => {
    localStorage.setItem(GS_DISMISS_KEY(username), '1');
    setDismissed(true);
  };

  return (
    <div className="gs-card" role="region" aria-label="Getting started checklist">
      <div className="gs-header">
        <div className="gs-header-text">
          <h3 className="gs-title">Getting started checklist</h3>
          <p className="gs-subtitle">
            Four hands-on steps to connect clouds, analyze spend, upload files, and request VMs.
            {' '}{doneCount} of {GS_STEPS.length} complete
          </p>
        </div>
        <div className="gs-progress-wrap">
          <div className="gs-progress-bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div className="gs-progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <span className="gs-progress-label">{pct}%</span>
        </div>
        <button type="button" className="gs-dismiss" onClick={handleDismiss} aria-label="Dismiss getting started">
          ✕
        </button>
      </div>
      <div className="gs-steps">
        {GS_STEPS.map((step) => {
          const done = completed[step.id];
          return (
            <button
              key={step.id}
              type="button"
              className={`gs-step ${done ? 'gs-step--done' : ''}`}
              onClick={() => navigate(step.path)}
            >
              <span className="gs-step-icon" aria-hidden="true">{step.icon}</span>
              <span className="gs-step-check" aria-label={done ? 'Complete' : 'Incomplete'}>
                {done ? '✓' : ''}
              </span>
              <span className="gs-step-body">
                <span className="gs-step-label">{step.label}</span>
                <span className="gs-step-desc">{step.description}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return { text: "Good morning", tone: "Morning operations" };
  if (hour < 17) return { text: "Good afternoon", tone: "Cloud command active" };
  if (hour < 21) return { text: "Good evening", tone: "Evening optimization" };
  return { text: "Good night", tone: "Night watch online" };
};

function platformStatusLabel(data) {
  if (!data) return { text: 'Checking platform…', className: 'loading' };
  if (data.demo_mode || data.services?.billing_data === 'demo_mock') {
    return { text: 'Demo mode — sample billing data', className: 'demo' };
  }
  if (data.overall === 'operational') {
    return { text: 'All systems operational', className: 'healthy' };
  }
  if (data.overall === 'maintenance') {
    return { text: 'Scheduled maintenance', className: 'warn' };
  }
  return { text: 'Partial degradation', className: 'warn' };
}

function DashboardPage() {
  const { token, user } = useAuth();
  const { isFeatureEnabled, limits: planLimits } = usePlanEntitlementsContext();
  const { byocConnected } = useCloudAvailabilityContext();
  const { formatCurrency, formatDateFriendly, currencySymbol } = usePreferences();
  const navigate = useNavigate();
  const notifications = useNotifications();
  const { runPageRefresh, pageRefreshing } = usePageRefresh();
  const [stats, setStats] = useState(null);
  const [budgets, setBudgets] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [costTrendSeries, setCostTrendSeries] = useState(null);
  const [vmHealth, setVmHealth] = useState({ healthy: 0, warning: 0, critical: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRefreshingCosts, setIsRefreshingCosts] = useState(false);
  const [lastCostUpdate, setLastCostUpdate] = useState(null);
  const [costByProvider, setCostByProvider] = useState({});
  const [costDemoMode, setCostDemoMode] = useState(false);
  const [billingStatus, setBillingStatus] = useState(null);
  const [teamOrg, setTeamOrg] = useState(null);
  const [teamSummary, setTeamSummary] = useState(null);
  const [attention, setAttention] = useState({ anomalies: 0, tickets: 0 });

  const greeting = useMemo(getGreeting, []);
  const formattedDate = useMemo(() => formatDateFriendly(new Date()), [formatDateFriendly]);

  const animatedCost = useCountUp(stats?.monthly_costs || 0, 1400, 2);
  const animatedVMs = useCountUp(stats?.active_vms || 0, 1000);
  const animatedAlerts = useCountUp(stats?.security_alerts || 0, 800);

  const storageCapTb = useMemo(() => {
    const storageGb = planLimits?.storage_gb ?? 10;
    return Math.max(storageGb / 1024, 0.01);
  }, [planLimits]);

  const storagePercentage = useMemo(() => {
    if (!stats) return 0;
    return Math.min(Math.round((stats.storage_used_tb / storageCapTb) * 100), 100);
  }, [stats, storageCapTb]);

  const sparklineData = useMemo(() => {
    if (!costTrendSeries?.has_data) return [];
    return (costTrendSeries.points || []).map((p) => ({
      name: p.label,
      value: p.value,
    }));
  }, [costTrendSeries]);

  const trendChip = useMemo(() => {
    if (!costTrendSeries?.trend_pct || !costTrendSeries?.has_data) return null;
    return {
      trend: costTrendSeries.trend_direction || 'up',
      value: `${costTrendSeries.trend_direction === 'down' ? '-' : '+'}${costTrendSeries.trend_pct}%`,
    };
  }, [costTrendSeries]);

  const loadCostTrend = useCallback(async () => {
    try {
      const res = await apiClient.get('/dashboard/cost-trend?days=7');
      setCostTrendSeries(res.data);
      setCostDemoMode(Boolean(res.data?.demo_mode));
    } catch {
      setCostTrendSeries({ has_data: false, points: [] });
    }
  }, []);

  const fetchDashboardData = useCallback(async () => {
    if (!token) return;

    setError(null);

    try {
      const parallel = await Promise.allSettled([
        getDashboardStats(token),
        apiClient.get('/dashboard/recent-activity?limit=6'),
        loadCostTrend(),
      ]);

      if (parallel[0].status === 'fulfilled') {
        const statsData = parallel[0].value;
        setStats(statsData);
        setCostByProvider(statsData.cost_by_provider || {});
        if (statsData.vm_health) {
          setVmHealth(statsData.vm_health);
        }
      }
      if (parallel[1].status === 'fulfilled') {
        setRecentActivity(parallel[1].value.data || []);
      }
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
      setError("Failed to load dashboard data. Please try again.");
      notifications.error('Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  }, [token, loadCostTrend, notifications]);

  const fetchDeferredDashboardData = useCallback(async () => {
    if (!token) return;

    const parallel = await Promise.allSettled([
      apiClient.get('/budgets/status'),
      apiClient.get('/cost/billing-status'),
      apiClient.get('/organizations/me'),
      apiClient.get('/organizations/summary'),
      apiClient.get('/cost/anomalies/summary'),
      apiClient.get('/support/tickets'),
    ]);

    if (parallel[0].status === 'fulfilled') {
      setBudgets((parallel[0].value.data || []).slice(0, 3));
    }
    if (parallel[1].status === 'fulfilled') {
      setBillingStatus(parallel[1].value.data);
    }
    if (parallel[2].status === 'fulfilled') {
      setTeamOrg(parallel[2].value.data);
    }
    if (parallel[3].status === 'fulfilled') {
      setTeamSummary(parallel[3].value.data);
    } else {
      setTeamSummary(null);
    }
    const anomalyCount =
      parallel[4].status === 'fulfilled'
        ? parallel[4].value.data?.total_unacknowledged || 0
        : 0;
    const ticketCount =
      parallel[5].status === 'fulfilled'
        ? (parallel[5].value.data?.tickets || []).filter((t) => t.status === 'open').length
        : 0;
    setAttention({
      anomalies: anomalyCount,
      tickets: ticketCount,
    });
  }, [token]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  useEffect(() => {
    if (!token || isLoading) return;
    const runDeferred = () => fetchDeferredDashboardData();
    let idleId;
    let timeoutId;
    if (typeof requestIdleCallback !== 'undefined') {
      idleId = requestIdleCallback(runDeferred, { timeout: 2000 });
    } else {
      timeoutId = setTimeout(runDeferred, 150);
    }
    return () => {
      if (idleId != null && typeof cancelIdleCallback !== 'undefined') {
        cancelIdleCallback(idleId);
      }
      if (timeoutId != null) clearTimeout(timeoutId);
    };
  }, [token, isLoading, fetchDeferredDashboardData]);

  const refreshCosts = async () => {
    setIsRefreshingCosts(true);
    await notifications.executeWithNotification(
      async () => {
        const response = await apiClient.post('/dashboard/refresh-costs');
        if (response.data.success) {
          setStats((prevStats) => ({
            ...prevStats,
            monthly_costs: response.data.monthly_costs,
            cost_by_provider: response.data.cost_by_provider,
          }));
          setCostByProvider(response.data.cost_by_provider || {});
          setCostDemoMode(Boolean(response.data.demo_mode));
          setLastCostUpdate(new Date().toLocaleTimeString());
          await loadCostTrend();
          return response.data;
        }
        throw new Error('Refresh failed');
      },
      {
        loadingMessage: 'Refreshing cost data...',
        getSuccessMessage: (result) => `Cost data refreshed: ${formatCurrency(result.monthly_costs)}`,
        errorMessage: 'Failed to refresh cost data',
      }
    ).catch((err) => {
      console.error('Failed to refresh costs:', err);
    }).finally(() => {
      setIsRefreshingCosts(false);
    });
  };

  const getActivityIcon = (type) => {
    switch (type) {
      case 'vm': return <IconServer />;
      case 'storage': return <IconHardDrive />;
      case 'cost': return <IconDollarSign />;
      case 'security': return <IconShieldCheck />;
      default: return <IconActivity />;
    }
  };

  const offlineProviders = useMemo(() => {
    if (!billingStatus?.providers) return [];
    return Object.entries(billingStatus.providers)
      .filter(([, p]) => !p?.live)
      .map(([key]) => key.toUpperCase());
  }, [billingStatus]);

  const statusBanner = platformStatusLabel(null);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return (
      <EmptyState
        icon={<IconAlert aria-hidden="true" />}
        title="Unable to Load Dashboard"
        message={error}
        actionLabel="Retry"
        onAction={fetchDashboardData}
      />
    );
  }

  if (!user || !stats) {
    return <LoadingSpinner size="large" text="Initializing..." />;
  }

  const totalVMs = vmHealth.healthy + vmHealth.warning + vmHealth.critical;
  const hasAttention =
    stats.security_alerts > 0 || attention.anomalies > 0 || attention.tickets > 0;

  return (
    <PageContainer className="dashboard-overview">
      <PageHeader
        kicker={greeting.tone}
        title={`${greeting.text}, ${user.username}`}
        subtitle={`${formattedDate} — Operational overview across compute, storage, cost, and security.`}
        onRefresh={() =>
          runPageRefresh(fetchDashboardData, {
            loadingMessage: 'Refreshing dashboard…',
            successMessage: 'Dashboard refreshed.',
            errorMessage: 'Failed to refresh dashboard.',
          })
        }
        refreshing={pageRefreshing || isLoading}
      />

      {!isFeatureEnabled('live_billing') && (
        <div className="dashboard-demo-banner" role="status">
          <span>
            You are on the Free plan — cost charts use demo sample data. Upgrade for live billing across your clouds.
          </span>
          <Link to={PATHS.pricing}>View plans</Link>
        </div>
      )}

      {hasAttention && (
        <div className="dashboard-attention-strip" role="status">
          <span className="dashboard-attention-strip__label">Needs attention</span>
          {stats.security_alerts > 0 && (
            <button type="button" className="dashboard-attention-pill" onClick={() => navigate(PATHS.security)}>
              {stats.security_alerts} security alert{stats.security_alerts !== 1 ? 's' : ''}
            </button>
          )}
          {attention.anomalies > 0 && (
            <button type="button" className="dashboard-attention-pill" onClick={() => navigate(PATHS.costs)}>
              {attention.anomalies} cost anomal{attention.anomalies !== 1 ? 'ies' : 'y'}
            </button>
          )}
          {attention.tickets > 0 && (
            <button type="button" className="dashboard-attention-pill" onClick={() => navigate(PATHS.support)}>
              {attention.tickets} open ticket{attention.tickets !== 1 ? 's' : ''}
            </button>
          )}
        </div>
      )}

      {isFeatureEnabled('live_billing') && offlineProviders.length > 0 && !billingStatus?.demo_mode && (
        <div className="dashboard-setup-card bento-card" data-type="costs">
          <h3 className="card-title">Cloud billing setup</h3>
          <p className="card-subtitle">
            Connect billing for: {offlineProviders.join(', ')}. Open Cost Analysis to complete setup.
          </p>
          <button type="button" className="view-details-btn" onClick={() => navigate(PATHS.costs)}>
            Open Cost Analysis →
          </button>
        </div>
      )}

      <GettingStartedCard
        username={user?.username}
        stats={stats}
        byocConnected={byocConnected}
      />

      <div className="bento-grid" data-tour="bento-grid">
        <StatCard
          title="Cost Overview"
          value={`${currencySymbol}${animatedCost}`}
          icon={<IconDollarSign />}
          type="costs"
          size="lg"
          trend={trendChip?.trend}
          trendValue={trendChip?.value}
          data-tour="card-costs"
          action={
            <button
              className="refresh-costs-btn"
              type="button"
              onClick={refreshCosts}
              disabled={isRefreshingCosts}
              aria-label="Refresh cost data for all connected clouds"
              title="Refresh cost data for all connected clouds"
            >
              <IconRefresh className={isRefreshingCosts ? 'refresh-icon is-spinning' : 'refresh-icon'} />
              Refresh
            </button>
          }
          subtitle={
            `${costDemoMode ? 'Demo data · ' : ''}${
              lastCostUpdate
                ? `Updated: ${lastCostUpdate}${
                    Object.keys(costByProvider).length > 0
                      ? ` · ${Object.entries(costByProvider)
                          .map(([k, v]) => `${k.toUpperCase()} ${formatCurrency(v)}`)
                          .join(' + ')}`
                      : ''
                  }`
                : '30-day spend (all available clouds)'
            }`
          }
        >
          {sparklineData.length > 0 ? (
            <SparklineChart data={sparklineData} height={140} showXAxis={true} />
          ) : (
            <p className="dashboard-sparkline-empty">
              Refresh costs to build your 7-day trend.
            </p>
          )}
        </StatCard>

        <StatCard
          title="VM Health"
          icon={<IconServer />}
          type="vms"
          size="md"
          value={`${animatedVMs} Active`}
          data-tour="card-vms"
        >
          <div className="vm-rings-row">
            <div className="vm-ring-item">
              <ProgressRing
                percentage={totalVMs > 0 ? (vmHealth.healthy / Math.max(totalVMs, 1)) * 100 : 0}
                color="var(--success)"
                size={56}
                strokeWidth={5}
              >
                <span className="ring-count">{vmHealth.healthy}</span>
              </ProgressRing>
              <span className="ring-label">Healthy</span>
            </div>
            <div className="vm-ring-item">
              <ProgressRing
                percentage={totalVMs > 0 ? (vmHealth.warning / Math.max(totalVMs, 1)) * 100 : 0}
                color="var(--warning)"
                size={56}
                strokeWidth={5}
              >
                <span className="ring-count">{vmHealth.warning}</span>
              </ProgressRing>
              <span className="ring-label">Warning</span>
            </div>
            <div className="vm-ring-item">
              <ProgressRing
                percentage={totalVMs > 0 ? (vmHealth.critical / Math.max(totalVMs, 1)) * 100 : 0}
                color="var(--danger)"
                size={56}
                strokeWidth={5}
              >
                <span className="ring-count">{vmHealth.critical}</span>
              </ProgressRing>
              <span className="ring-label">Critical</span>
            </div>
          </div>
          <button className="view-details-btn" type="button" onClick={() => navigate(PATHS.vmCluster)}>
            View VM Cluster →
          </button>
        </StatCard>

        <StatCard
          title="Storage"
          icon={<IconHardDrive />}
          type="storage"
          size="sm"
          data-tour="card-storage"
        >
          <div className="storage-ring-center">
            <ProgressRing
              percentage={storagePercentage}
              color="var(--gold-primary)"
              size={90}
              strokeWidth={7}
            >
              <span className="ring-value">{stats.storage_used_tb}</span>
              <span className="ring-unit">TB</span>
            </ProgressRing>
            <span className="storage-capacity">
              {storagePercentage}% of plan capacity ({storageCapTb.toFixed(2)} TB)
            </span>
          </div>
        </StatCard>

        <StatCard
          title="Security"
          icon={<IconShieldCheck />}
          type="security"
          size="sm"
          value={animatedAlerts}
          subtitle={stats.security_alerts > 0 ? "Needs attention" : "All clear"}
        >
          <button className="view-details-btn" type="button" onClick={() => navigate(PATHS.security)}>
            View Security →
          </button>
        </StatCard>

        {isFeatureEnabled('live_billing') && budgets.length > 0 && (
          <div className="bento-card size-sm" data-type="costs">
            <div className="stat-card-header">
              <div className="stat-icon"><IconBarChart /></div>
              <h3 className="card-title">Budget alerts</h3>
            </div>
            <div className="card-content dashboard-budget-list">
              {budgets.map((b) => (
                <div key={b.id || b.name} className="dashboard-budget-item">
                  <span>{b.name}</span>
                  <strong>
                    {formatCurrency(b.current_spend || 0)} / {formatCurrency(b.amount || 0)}
                  </strong>
                </div>
              ))}
            </div>
            <button type="button" className="view-details-btn" onClick={() => navigate(PATHS.costs)}>
              Manage budgets →
            </button>
          </div>
        )}

        {teamOrg?.organization && (
          <div className="bento-card size-sm" data-type="security">
            <div className="stat-card-header">
              <h3 className="card-title">Team</h3>
            </div>
            <div className="card-content">
              <p className="card-value" style={{ fontSize: '1.1rem' }}>{teamOrg.organization.name}</p>
              <p className="card-subtitle">
                {teamOrg.members?.length || 0} member{(teamOrg.members?.length || 0) !== 1 ? 's' : ''} · your role: {teamOrg.my_role}
                {teamSummary?.org_totals?.monthly_spend_usd != null && (
                  <> · org spend ${teamSummary.org_totals.monthly_spend_usd.toFixed(2)}/mo</>
                )}
              </p>
            </div>
            <button type="button" className="view-details-btn" onClick={() => navigate(PATHS.team)}>
              Manage team →
            </button>
          </div>
        )}
      </div>

      <div className="mc-bottom-row">
        <div className="bento-card mc-quick-actions" data-tour="quick-actions">
          <h3 className="card-title">Quick Actions</h3>
          <div className="quick-actions-grid">
            <button className="action-btn" type="button" onClick={() => navigate(PATHS.vmCluster)}>
              <span className="action-icon"><IconServer /></span>
              <span className="action-text">Manage VMs</span>
            </button>
            <button className="action-btn" type="button" onClick={() => navigate(PATHS.storage)}>
              <span className="action-icon"><IconUploadCloud /></span>
              <span className="action-text">Upload Files</span>
            </button>
            <button className="action-btn" type="button" onClick={() => navigate(PATHS.costs)}>
              <span className="action-icon"><IconBarChart /></span>
              <span className="action-text">Cost Analysis</span>
            </button>
            <button className="action-btn" type="button" onClick={() => navigate(PATHS.security)}>
              <span className="action-icon"><IconShieldCheck /></span>
              <span className="action-text">Security</span>
            </button>
          </div>
        </div>

        <div className="bento-card mc-activity-timeline">
          <h3 className="card-title">Recent Activity</h3>
          {recentActivity.length > 0 ? (
            <div className="activity-scroll">
              {recentActivity.map((activity, index) => (
                <div key={activity.id || index} className="timeline-card">
                  <span className="timeline-icon">{getActivityIcon(activity.type || activity.action_type)}</span>
                  <div className="timeline-content">
                    <span className="timeline-action">{activity.action || activity.description}</span>
                    <span className="timeline-time">{activity.time || activity.timestamp || ''}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">No recent activity — start managing your cloud resources!</p>
          )}
        </div>
      </div>

      <div className={`system-status-banner system-status-banner--${statusBanner.className}`}>
        <div className="status-indicator">
          <span className={`status-dot ${statusBanner.className}`}></span>
          <span>{statusBanner.text}</span>
        </div>
        <div className="status-info">
          <button type="button" className="dashboard-status-link" onClick={() => navigate('/status')}>
            View status page
          </button>
        </div>
      </div>
    </PageContainer>
  );
}

export default DashboardPage;
