import React, { useState, useEffect, useMemo } from "react";
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
} from "../components/dashboard/Icons.jsx";
import { useNavigate } from 'react-router-dom';
import { useNotifications } from "../hooks/useNotifications.js";
import { useCountUp } from "../hooks/useCountUp.js";
import { DashboardSkeleton } from "../components/Skeletons.jsx";
import '../styles/dashboard-enhanced.css';

// --- Helpers ---

const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return { text: "Good morning", emoji: "☀️" };
  if (hour < 17) return { text: "Good afternoon", emoji: "🌤️" };
  if (hour < 21) return { text: "Good evening", emoji: "🌅" };
  return { text: "Good night", emoji: "🌙" };
};

// getFormattedDate is now handled by PreferencesContext.formatDateFriendly()

/**
 * Generate synthetic 7-day cost trend data from a monthly total.
 * This creates a realistic-looking curve until the real cost-trend API exists.
 */
const generateCostTrend = (monthlyTotal) => {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const dailyAvg = monthlyTotal / 30;
  // Create a realistic variation pattern
  const multipliers = [0.85, 1.1, 0.95, 1.2, 1.05, 0.7, 0.6];
  return days.map((day, i) => ({
    name: day,
    value: Math.round(dailyAvg * multipliers[i] * 100) / 100,
  }));
};

// --- Main Component ---

function DashboardPage() {
  const { token, user } = useAuth();
  const { formatCurrency, formatDateFriendly, currencySymbol } = usePreferences();
  const navigate = useNavigate();
  const notifications = useNotifications();
  const [stats, setStats] = useState(null);
  const [budgets, setBudgets] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [costTrend, setCostTrend] = useState('up');
  const [vmHealth, setVmHealth] = useState({ healthy: 0, warning: 0, critical: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRefreshingCosts, setIsRefreshingCosts] = useState(false);
  const [lastCostUpdate, setLastCostUpdate] = useState(null);

  const greeting = useMemo(getGreeting, []);
  const formattedDate = useMemo(() => formatDateFriendly(new Date()), [formatDateFriendly]);

  // Animated counters
  const animatedCost = useCountUp(stats?.monthly_costs || 0, 1400, 2);
  const animatedVMs = useCountUp(stats?.active_vms || 0, 1000);
  const animatedAlerts = useCountUp(stats?.security_alerts || 0, 800);

  // Synthetic sparkline data
  const sparklineData = useMemo(() => {
    if (!stats) return [];
    return generateCostTrend(stats.monthly_costs);
  }, [stats?.monthly_costs]);

  // Storage percentage (mock: 82% as shown in design)
  const storagePercentage = useMemo(() => {
    if (!stats) return 0;
    return Math.min(Math.round((stats.storage_used_tb / 5) * 100), 100); // 5TB assumed max
  }, [stats?.storage_used_tb]);

  useEffect(() => {
    fetchDashboardData();
  }, [token]);

  const fetchDashboardData = async () => {
    if (!token) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const statsData = await getDashboardStats(token);
      setStats(statsData);
      
      if (statsData.vm_health) {
        setVmHealth(statsData.vm_health);
      }

      try {
        const budgetResponse = await apiClient.get('/budgets/status');
        setBudgets(budgetResponse.data.slice(0, 3));
      } catch (err) {
        console.log('Budgets not available');
      }

      try {
        const activityResponse = await apiClient.get('/dashboard/recent-activity?limit=6');
        setRecentActivity(activityResponse.data || []);
      } catch (err) {
        console.log('Activity data not available');
        setRecentActivity([]);
      }
      
      setCostTrend(statsData.monthly_costs > 0 ? 'up' : 'stable');
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
      setError("Failed to load dashboard data. Please try again.");
      notifications.error('Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  };

  const refreshCosts = async () => {
    setIsRefreshingCosts(true);
    await notifications.executeWithNotification(
      async () => {
        const response = await apiClient.post('/dashboard/refresh-costs');
        if (response.data.success) {
          setStats(prevStats => ({
            ...prevStats,
            monthly_costs: response.data.monthly_costs
          }));
          setLastCostUpdate(new Date().toLocaleTimeString());
          return response.data;
        }
        throw new Error('Refresh failed');
      },
      {
        loadingMessage: 'Refreshing cost data...',
        getSuccessMessage: (result) => `Cost data refreshed: ${formatCurrency(result.monthly_costs)}`,

        errorMessage: 'Failed to refresh cost data',
      }
    ).catch((error) => {
      console.error('Failed to refresh costs:', error);
    }).finally(() => {
      setIsRefreshingCosts(false);
    });
  };

  const getActivityIcon = (type) => {
    switch(type) {
      case 'vm': return '🖥️';
      case 'storage': return '💾';
      case 'cost': return '💰';
      case 'security': return '🔒';
      default: return '📋';
    }
  };

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return (
      <EmptyState
        icon="⚠️"
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

  return (
    <div className="dashboard-overview">
      {/* ============ GREETING ============ */}
      <div className="mc-greeting">
        <div className="mc-greeting-text">
          <h2>
            {greeting.text}, {user.username}
            <span className="greeting-emoji">{greeting.emoji}</span>
          </h2>
          <p className="greeting-date">{formattedDate} — Here's your cloud overview</p>
        </div>
      </div>

      {/* ============ BENTO GRID ============ */}
      <div className="bento-grid">
        {/* --- Cost Overview (Large, 2-col, 2-row) --- */}
        <StatCard
          title="Cost Overview"
          value={`${currencySymbol}${animatedCost}`}
          icon={<IconDollarSign />}
          type="costs"
          size="lg"
          trend={costTrend}
          trendValue="+12.5%"
          action={
            <button 
              className="refresh-costs-btn" 
              onClick={refreshCosts}
              disabled={isRefreshingCosts}
              title="Refresh cost data from AWS"
            >
              {isRefreshingCosts ? '🔄' : '↻'} Refresh
            </button>
          }
          subtitle={lastCostUpdate ? `Updated: ${lastCostUpdate}` : '7-day spending trend'}
        >
          <SparklineChart data={sparklineData} height={140} showXAxis={true} />
        </StatCard>

        {/* --- VM Health (Medium) --- */}
        <StatCard
          title="VM Health"
          icon={<IconServer />}
          type="vms"
          size="md"
          value={`${animatedVMs} Active`}
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
          <button className="view-details-btn" onClick={() => navigate('/dashboard/vmcluster')}>
            View VM Cluster →
          </button>
        </StatCard>

        {/* --- Storage Used (Small) --- */}
        <StatCard
          title="Storage"
          icon={<IconHardDrive />}
          type="storage"
          size="sm"
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
            <span className="storage-capacity">{storagePercentage}% of capacity</span>
          </div>
        </StatCard>

        {/* --- Security Alerts (Small) --- */}
        <StatCard
          title="Security"
          icon={<IconShieldCheck />}
          type="security"
          size="sm"
          value={animatedAlerts}
          subtitle={stats.security_alerts > 0 ? "Needs attention" : "All clear"}
        >
          <button className="view-details-btn" onClick={() => navigate('/dashboard/security')}>
            View Security →
          </button>
        </StatCard>
      </div>

      {/* ============ QUICK ACTIONS + ACTIVITY ============ */}
      <div className="mc-bottom-row">
        {/* Quick Actions */}
        <div className="bento-card mc-quick-actions">
          <h3 className="card-title">Quick Actions</h3>
          <div className="quick-actions-grid">
            <button className="action-btn" type="button" onClick={() => navigate('/dashboard/vmcluster')}>
              <span className="action-icon">🖥️</span>
              <span className="action-text">Manage VMs</span>
            </button>
            <button className="action-btn" type="button" onClick={() => navigate('/dashboard/storage')}>
              <span className="action-icon">📁</span>
              <span className="action-text">Upload Files</span>
            </button>
            <button className="action-btn" type="button" onClick={() => navigate('/dashboard/costs')}>
              <span className="action-icon">📊</span>
              <span className="action-text">Cost Analysis</span>
            </button>
            <button className="action-btn" type="button" onClick={() => navigate('/dashboard/security')}>
              <span className="action-icon">🔒</span>
              <span className="action-text">Security</span>
            </button>
          </div>
        </div>

        {/* Activity Timeline (horizontal scroll) */}
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

      {/* System Status */}
      <div className="system-status-banner">
        <div className="status-indicator">
          <span className="status-dot healthy"></span>
          <span>All Systems Operational</span>
        </div>
        <div className="status-info">
          <span>Last updated: {new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
