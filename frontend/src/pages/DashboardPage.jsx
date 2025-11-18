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
import '../styles/dashboard-enhanced.css';

function DashboardPage() {
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [budgets, setBudgets] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [costTrend, setCostTrend] = useState('up');
  const [vmHealth, setVmHealth] = useState({ healthy: 0, warning: 0, critical: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

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

      // Generate mock activity data
      setRecentActivity([
        { id: 1, type: 'vm', action: 'Created VM instance', resource: 'web-server-01', time: '2 hours ago', status: 'success' },
        { id: 2, type: 'storage', action: 'Uploaded files', resource: 'backup-storage', time: '5 hours ago', status: 'success' },
        { id: 3, type: 'cost', action: 'Budget alert triggered', resource: 'Monthly AWS', time: '1 day ago', status: 'warning' },
        { id: 4, type: 'security', action: 'Security scan completed', resource: 'All resources', time: '2 days ago', status: 'success' },
      ]);
      
      // Set cost trend based on data
      setCostTrend('up');
      
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
      setError("Failed to load dashboard data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return <LoadingSpinner size="large" text="Loading dashboard data..." />;
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
            trend={costTrend}
            trendValue="+12.5%"
          />
          <StatCard
            title="Active VMs"
            value={stats.active_vms}
            icon={<IconServer />}
            subtitle={`${vmHealth.healthy} healthy, ${vmHealth.warning} warnings`}
          />
          <StatCard
            title="Storage Used"
            value={`${stats.storage_used_tb} TB`}
            icon={<IconHardDrive />}
            subtitle="82% of capacity"
          />
          <StatCard
            title="Security Alerts"
            value={stats.security_alerts}
            icon={<IconShieldCheck />}
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
            <div className="activity-list">
              {recentActivity.map((activity) => (
                <div key={activity.id} className="activity-item">
                  <span className="activity-icon">{getActivityIcon(activity.type)}</span>
                  <div className="activity-details">
                    <div className="activity-action">{activity.action}</div>
                    <div className="activity-resource">{activity.resource}</div>
                  </div>
                  <div className="activity-time">{activity.time}</div>
                  <div 
                    className="activity-status-dot"
                    style={{ backgroundColor: getStatusColor(activity.status) }}
                  ></div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="info-card quick-actions-card">
            <h3>Quick Actions</h3>
            <div className="quick-actions-grid">
              <button className="action-btn" onClick={() => navigate('/dashboard/vmcluster')}>
                <span className="action-icon">🖥️</span>
                <span className="action-text">Manage VMs</span>
              </button>
              <button className="action-btn" onClick={() => navigate('/dashboard/storage')}>
                <span className="action-icon">📁</span>
                <span className="action-text">Upload Files</span>
              </button>
              <button className="action-btn" onClick={() => navigate('/dashboard/costs')}>
                <span className="action-icon">📊</span>
                <span className="action-text">Cost Analysis</span>
              </button>
              <button className="action-btn" onClick={() => navigate('/dashboard/security')}>
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
