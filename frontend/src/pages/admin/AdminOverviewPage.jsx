import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api';
import { toast } from 'react-toastify';
import '../../styles/admin-pages.css';
import '../../styles/dashboard-enhanced.css';
import StatCard from '../../components/dashboard/StatCard.jsx';
import PageRefreshButton from '../../components/ui/PageRefreshButton.jsx';
import AdminPortalGateBanner from '../../components/admin/AdminPortalGateBanner.jsx';
import { parseAdminPortalGateError } from '../../utils/adminPortalGate.js';
import { usePageRefresh } from '../../hooks/usePageRefresh.js';
import { 
  FaUsers, FaServer, FaDatabase, FaDollarSign,
  FaChartLine, FaHistory, FaCogs
} from 'react-icons/fa';

const AdminOverviewPage = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [activities, setActivities] = useState([]);
  const [gateError, setGateError] = useState(null);
  const { runPageRefresh, pageRefreshing } = usePageRefresh();

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    if (hour < 21) return 'Good evening';
    return 'Good night';
  }, []);

  const formattedDate = useMemo(
    () => new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' }),
    []
  );

  const fetchData = useCallback(async () => {
    setLoading(true);
    setGateError(null);
    try {
      const [statsRes, activityRes] = await Promise.all([
        api.get('/admin/dashboard'),
        api.get('/admin/recent-activity?limit=8')
      ]);

      setStats(statsRes.data);
      setActivities(activityRes.data.activities);
    } catch (error) {
      const portalGate = parseAdminPortalGateError(error);
      if (portalGate) {
        setGateError(portalGate);
        setStats(null);
        setActivities([]);
      } else {
        toast.error(error.response?.data?.detail?.message || error.response?.data?.detail || 'Failed to load admin dashboard');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  const totalSubscriptions = useMemo(() => {
    if (!stats?.subscription_breakdown) return 0;
    return Object.values(stats.subscription_breakdown).reduce((sum, count) => sum + count, 0);
  }, [stats]);

  const subscriptionEntries = useMemo(() => {
    if (!stats?.subscription_breakdown) return [];
    return Object.entries(stats.subscription_breakdown);
  }, [stats]);

  const activeRate = useMemo(() => {
    if (!stats?.total_users) return '0.0';
    return ((stats.active_users / stats.total_users) * 100).toFixed(1);
  }, [stats]);

  const growthTrend = (stats?.growth_rate ?? 0) >= 0 ? 'up' : 'down';
  const growthValue = Math.abs(stats?.growth_rate || 0).toFixed(1);

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
      <div className="admin-overview dashboard-overview">
        <AdminPortalGateBanner gateError={gateError} />
        {!gateError && (
          <div className="admin-loading">
            <p>Failed to load admin data. Please check your permissions.</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="admin-overview dashboard-overview">
      <AdminPortalGateBanner gateError={gateError} />
      <div className="mc-greeting">
        <div className="mc-greeting-text">
          <span className="mc-kicker">
            <span className="mc-kicker-dot"></span>
            Admin command center
          </span>
          <h2>{greeting}, admin</h2>
          <p className="greeting-date">{formattedDate} — platform operations at a glance</p>
        </div>
        <PageRefreshButton
          onClick={() =>
            runPageRefresh(fetchData, {
              loadingMessage: 'Refreshing admin overview…',
              successMessage: 'Admin overview refreshed.',
              errorMessage: 'Failed to refresh admin overview.',
            })
          }
          busy={pageRefreshing || loading}
        />
      </div>

      <div className="bento-grid">
        <StatCard
          title="Platform Users"
          value={stats.total_users.toLocaleString()}
          icon={<FaUsers />}
          type="security"
          size="lg"
          subtitle={`${stats.active_users} active • ${activeRate}% active rate`}
          action={<Link to="/admin/users" className="btn-primary">Review users</Link>}
        >
          <div className="subscription-grid">
            {subscriptionEntries.map(([plan, count]) => {
              const percentage = totalSubscriptions > 0 ? ((count / totalSubscriptions) * 100).toFixed(1) : '0.0';
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
        </StatCard>

        <StatCard
          title="Total Revenue"
          value={`₹${stats.total_revenue.toLocaleString()}`}
          icon={<FaDollarSign />}
          type="costs"
          size="md"
          subtitle={`₹${stats.monthly_revenue.toLocaleString()} this month`}
        />

        <StatCard
          title="Active VMs"
          value={stats.total_vms.toLocaleString()}
          icon={<FaServer />}
          type="vms"
          size="md"
          subtitle="Running instances across the platform"
        />

        <StatCard
          title="Total Storage"
          value={`${Number(stats.total_storage_gb).toFixed(1)} GB`}
          icon={<FaDatabase />}
          type="storage"
          size="md"
          subtitle="Multi-cloud footprint"
        />

        <StatCard
          title="User Growth"
          value={`${growthValue}%`}
          icon={<FaChartLine />}
          type="security"
          size="md"
          subtitle="Last 30 days"
          trend={growthTrend}
          trendValue={growthValue}
        />
      </div>

      <div className="bento-grid">
        <div className="bento-card size-md" data-type="security">
          <div className="stat-card-header">
            <div className="stat-icon">
              <FaCogs />
            </div>
            <h3 className="card-title">Quick Actions</h3>
          </div>
          <div className="card-content">
            <div className="admin-quick-actions">
              <Link to="/admin/users" className="btn-primary">Manage Users</Link>
              <Link to="/admin/analytics" className="btn-primary">Open Analytics</Link>
              <Link to="/admin/system" className="btn-primary">View System</Link>
              <Link to="/admin/support" className="btn-primary">Support Inbox</Link>
              <Link to="/admin/settings" className="btn-primary">Admin Settings</Link>
            </div>
          </div>
        </div>

        <div className="bento-card size-md" data-type="costs">
          <div className="stat-card-header">
            <div className="stat-icon">
              <FaHistory />
            </div>
            <h3 className="card-title">Recent Activity</h3>
          </div>
          <div className="card-content">
            {activities.length > 0 ? (
              <div className="activity-timeline">
                {activities.map((activity, index) => (
                  <div key={activity.id || index} className={`timeline-item ${activity.type}`}>
                    <div className="timeline-marker"></div>
                    <div className="timeline-content">
                      <p className="timeline-description">{activity.description}</p>
                      <span className="timeline-time">{formatDate(activity.timestamp)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-state-copy">No recent activity yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminOverviewPage;
