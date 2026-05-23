import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { getDashboardStats, apiClient } from "../api.js";
import StatCard from "../components/dashboard/StatCard.jsx";
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
import { DashboardSkeleton } from "../components/Skeletons.jsx";
import '../styles/dashboard-enhanced.css';

function DashboardPage() {
  const { token, user } = useAuth();
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

  useEffect(() => {
    fetchDashboardData();
  }, [token]);

  const fetchDashboardData = async () => {
    if (!token) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Fetch dashboard stats
      const statsData = await getDashboardStats(token);
      setStats(statsData);
      
      // Set VM health from API response
      if (statsData.vm_health) {
        setVmHealth(statsData.vm_health);
      }

      // Fetch budgets
      try {
        const budgetResponse = await apiClient.get('/budgets/status');
        setBudgets(budgetResponse.data.slice(0, 3)); // Top 3 budgets
      } catch (err) {
        console.log('Budgets not available');
      }

      // Fetch recent activity from API
      try {
        const activityResponse = await apiClient.get('/dashboard/recent-activity?limit=4');
        setRecentActivity(activityResponse.data || []);
      } catch (err) {
        console.log('Activity data not available');
        setRecentActivity([]);
      }
      
      // Set cost trend based on actual data
      setCostTrend(statsData.monthly_costs > 0 ? 'up' : 'stable');
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
      setError("Failed to load dashboard data. Please try again.");
      // Only show notification on error
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
          // Update stats with new cost data
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
        getSuccessMessage: (result) => `Cost data refreshed: $${result.monthly_costs.toFixed(2)} (Note: This action costs $0.01)`,
        errorMessage: 'Failed to refresh cost data',
      }
    ).catch((error) => {
      console.error('Failed to refresh costs:', error);
    }).finally(() => {
      setIsRefreshingCosts(false);
    });
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

  const getActivityIcon = (type) => {
    switch(type) {
      case 'vm': return '🖥️';
      case 'storage': return '💾';
      case 'cost': return '💰';
      case 'security': return '🔒';
      default: return '📋';
    }
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'success': return '#28a745';
      case 'warning': return '#ffc107';
      case 'critical': return '#dc3545';
      default: return '#6c757d';
    }
  };

  return (
    <>
      <div className="dashboard-overview">
        <div className="welcome-section">
          <h2>Dashboard Overview</h2>
          <p>Welcome back, {user.username}! Here's a snapshot of your cloud environment.</p>
        </div>

        {/* Main Stats Grid */}
        <div className="stats-grid">
          <StatCard
            title="Monthly Costs"
            value={`$${stats.monthly_costs.toLocaleString()}`}
            icon={<IconDollarSign />}
            type="costs"
            trend={costTrend}
            trendValue="+12.5%"
            action={
              <button 
                className="refresh-costs-btn" 
                onClick={refreshCosts}
                disabled={isRefreshingCosts}
                title="Refresh cost data from AWS (costs $0.01)"
              >
                {isRefreshingCosts ? '🔄' : '↻'} Refresh
              </button>
            }
            subtitle={lastCostUpdate ? `Updated: ${lastCostUpdate}` : 'Using cached data'}
          />
          <StatCard
            title="Active VMs"
            value={stats.active_vms}
            icon={<IconServer />}
            type="vms"
            subtitle={`${vmHealth.healthy} healthy, ${vmHealth.warning} warnings`}
          />
          <StatCard
            title="Storage Used"
            value={`${stats.storage_used_tb} TB`}
            icon={<IconHardDrive />}
            type="storage"
            subtitle="82% of capacity"
          />
          <StatCard
            title="Security Alerts"
            value={stats.security_alerts}
            icon={<IconShieldCheck />}
            type="security"
            subtitle={stats.security_alerts > 0 ? "Needs attention" : "All clear"}
          />
        </div>

        {/* Secondary Info Grid */}
        <div className="info-grid">
          {/* VM Health Overview */}
          <div className="info-card vm-health-card">
            <h3>VM Health Status</h3>
            <div className="vm-health-chart">
              <div className="health-stat">
                <div className="health-circle healthy"></div>
                <div className="health-info">
                  <span className="health-count">{vmHealth.healthy}</span>
                  <span className="health-label">Healthy</span>
                </div>
              </div>
              <div className="health-stat">
                <div className="health-circle warning"></div>
                <div className="health-info">
                  <span className="health-count">{vmHealth.warning}</span>
                  <span className="health-label">Warning</span>
                </div>
              </div>
              <div className="health-stat">
                <div className="health-circle critical"></div>
                <div className="health-info">
                  <span className="health-count">{vmHealth.critical}</span>
                  <span className="health-label">Critical</span>
                </div>
              </div>
            </div>
            <button className="view-details-btn" onClick={() => navigate('/dashboard/vmcluster')}>
              View VM Cluster →
            </button>
          </div>

          {/* Budget Status */}
          <div className="info-card budget-status-card">
            <h3>Budget Status</h3>
            {budgets.length > 0 ? (
              <div className="budget-list">
                {budgets.map((budgetStatus) => {
                  const budget = budgetStatus.budget || budgetStatus;
                  const spend = budget.current_spend || 0;
                  const amount = budget.amount || 1;
                  const utilization = budgetStatus.utilization || ((spend / amount) * 100);
                  const isExceeded = budgetStatus.is_exceeded || spend >= amount;
                  const isNearLimit = budgetStatus.is_near_limit || utilization >= 80;
                  
                  return (
                    <div key={budget.id} className="budget-item">
                      <div className="budget-name">{budget.name}</div>
                      <div className="budget-bar-container">
                        <div 
                          className={`budget-bar ${isExceeded ? 'exceeded' : isNearLimit ? 'warning' : 'normal'}`}
                          style={{ width: `${Math.min(utilization, 100)}%` }}
                        ></div>
                      </div>
                      <div className="budget-info-text">
                        ${spend.toFixed(2)} / ${amount.toFixed(2)} 
                        <span className="budget-percentage"> ({utilization.toFixed(0)}%)</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="no-data">No budgets configured</p>
            )}
            <button className="view-details-btn" onClick={() => navigate('/dashboard/costs')}>
              Manage Budgets →
            </button>
          </div>

          {/* Recent Activity */}
          <div className="info-card activity-card">
            <h3>Recent Activity</h3>
            {recentActivity.length > 0 ? (
              <div className="activity-list">
                {recentActivity.map((activity, index) => (
                  <div key={activity.id || index} className="activity-item">
                    <span className="activity-icon">{getActivityIcon(activity.type || activity.action_type)}</span>
                    <div className="activity-details">
                      <div className="activity-action">{activity.action || activity.description}</div>
                      <div className="activity-resource">{activity.resource || activity.details || ''}</div>
                    </div>
                    <div className="activity-time">{activity.time || activity.timestamp || ''}</div>
                    <div 
                      className="activity-status-dot"
                      style={{ backgroundColor: getStatusColor(activity.status || 'success') }}
                    ></div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">No recent activity — start managing your cloud resources!</p>
            )}
          </div>

          {/* Quick Actions */}
          <div className="info-card quick-actions-card">
            <h3>Quick Actions</h3>
            <div className="quick-actions-grid">
              <button 
                className="action-btn" 
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  navigate('/dashboard/vmcluster');
                }}
              >
                <span className="action-icon">🖥️</span>
                <span className="action-text">Manage VMs</span>
              </button>
              <button 
                className="action-btn" 
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  navigate('/dashboard/storage');
                }}
              >
                <span className="action-icon">📁</span>
                <span className="action-text">Upload Files</span>
              </button>
              <button 
                className="action-btn" 
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  navigate('/dashboard/costs');
                }}
              >
                <span className="action-icon">📊</span>
                <span className="action-text">Cost Analysis</span>
              </button>
              <button 
                className="action-btn" 
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  navigate('/dashboard/security');
                }}
              >
                <span className="action-icon">🔒</span>
                <span className="action-text">Security</span>
              </button>
            </div>
          </div>
        </div>

        {/* System Status Banner */}
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
    </>
  );
}

export default DashboardPage;
