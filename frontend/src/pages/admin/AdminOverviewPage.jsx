import React, { useState, useEffect } from 'react';
import api from '../../api';
import { toast } from 'react-toastify';
import '../../styles/admin-pages.css';
import { 
  FaUsers, FaServer, FaDatabase, FaDollarSign, 
  FaChartLine, FaArrowUp, FaArrowDown
} from 'react-icons/fa';

const AdminOverviewPage = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [activities, setActivities] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      console.log('[AdminOverview] Fetching dashboard data...');
      const [statsRes, activityRes] = await Promise.all([
        api.get('/admin/dashboard'),
        api.get('/admin/recent-activity?limit=8')
      ]);

      console.log('[AdminOverview] Stats response:', statsRes.data);
      console.log('[AdminOverview] Activity response:', activityRes.data);

      setStats(statsRes.data);
      setActivities(activityRes.data.activities);
    } catch (error) {
      console.error('[AdminOverview] Failed to fetch admin data:', error);
      console.error('[AdminOverview] Error response:', error.response?.data);
      console.error('[AdminOverview] Error status:', error.response?.status);
      toast.error(error.response?.data?.detail || 'Failed to load admin dashboard');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="admin-loading">
        <p>Failed to load admin data. Please check your permissions.</p>
      </div>
    );
  }

  return (
    <div className="admin-overview">;
      <div className="admin-page-header">
        <h1>Platform Overview</h1>
        <p>Monitor your platform's key metrics and activity</p>
      </div>

      {/* Stats Grid */}
      <div className="admin-stats-grid">
        <div className="admin-stat-card primary">
          <div className="stat-icon">
            <FaUsers />
          </div>
          <div className="stat-content">
            <h3>{stats.total_users}</h3>
            <p>Total Users</p>
            <div className="stat-meta">
              <span className="stat-badge success">
                {stats.active_users} active
              </span>
            </div>
          </div>
        </div>

        <div className="admin-stat-card success">
          <div className="stat-icon">
            <FaDollarSign />
          </div>
          <div className="stat-content">
            <h3>₹{stats.total_revenue.toLocaleString()}</h3>
            <p>Total Revenue</p>
            <div className="stat-meta">
              <span className="stat-detail">
                ₹{stats.monthly_revenue.toLocaleString()} this month
              </span>
            </div>
          </div>
        </div>

        <div className="admin-stat-card info">
          <div className="stat-icon">
            <FaServer />
          </div>
          <div className="stat-content">
            <h3>{stats.total_vms}</h3>
            <p>Active VMs</p>
            <div className="stat-meta">
              <span className="stat-detail">Running instances</span>
            </div>
          </div>
        </div>

        <div className="admin-stat-card warning">
          <div className="stat-icon">
            <FaDatabase />
          </div>
          <div className="stat-content">
            <h3>{stats.total_storage_gb.toFixed(1)} GB</h3>
            <p>Total Storage</p>
            <div className="stat-meta">
              <span className="stat-detail">Multi-cloud</span>
            </div>
          </div>
        </div>

        <div className="admin-stat-card growth">
          <div className="stat-icon">
            <FaChartLine />
          </div>
          <div className="stat-content">
            <h3>
              {stats.growth_rate > 0 ? <FaArrowUp className="trend-up" /> : <FaArrowDown className="trend-down" />}
              {Math.abs(stats.growth_rate)}%
            </h3>
            <p>User Growth</p>
            <div className="stat-meta">
              <span className="stat-detail">Last 30 days</span>
            </div>
          </div>
        </div>
      </div>

      {/* Subscription Breakdown */}
      <div className="admin-card">
        <div className="card-header">
          <h2>Subscription Distribution</h2>
        </div>
        <div className="card-body">
          <div className="subscription-grid">
            {Object.entries(stats.subscription_breakdown).map(([plan, count]) => {
              const percentage = ((count / stats.total_users) * 100).toFixed(1);
              return (
                <div key={plan} className="subscription-item">
                  <div className="subscription-info">
                    <span className={`plan-badge ${plan}`}>
                      {plan.charAt(0).toUpperCase() + plan.slice(1)}
                    </span>
                    <span className="subscription-count">{count} users</span>
                  </div>
                  <div className="subscription-bar">
                    <div 
                      className={`bar-fill ${plan}`} 
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                  <span className="subscription-percentage">{percentage}%</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="admin-card">
        <div className="card-header">
          <h2>Recent Activity</h2>
        </div>
        <div className="card-body">
          <div className="activity-timeline">
            {activities.map((activity, index) => (
              <div key={index} className={`timeline-item ${activity.type}`}>
                <div className="timeline-marker"></div>
                <div className="timeline-content">
                  <p className="timeline-description">{activity.description}</p>
                  <span className="timeline-time">{formatDate(activity.timestamp)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminOverviewPage;
