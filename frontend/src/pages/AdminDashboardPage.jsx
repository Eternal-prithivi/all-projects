import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { toast } from 'react-toastify';
import '../styles/admin-dashboard.css';
import { 
  FaUsers, FaServer, FaDatabase, FaDollarSign, 
  FaChartLine, FaBan, FaCheck, FaClock,
  FaUserPlus, FaSearch, FaShieldAlt
} from 'react-icons/fa';

const AdminDashboardPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [activities, setActivities] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTab, setSelectedTab] = useState('overview');
  const [usersPagination, setUsersPagination] = useState({ skip: 0, limit: 10, total: 0 });

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    setLoading(true);
    try {
      const [statsRes, usersRes, activityRes, healthRes] = await Promise.all([
        api.get('/admin/dashboard'),
        api.get('/admin/users?skip=0&limit=10'),
        api.get('/admin/recent-activity?limit=10'),
        api.get('/admin/system-health')
      ]);

      setStats(statsRes.data);
      setUsers(usersRes.data.users);
      setUsersPagination({ skip: 0, limit: 10, total: usersRes.data.total });
      setActivities(activityRes.data.activities);
      setSystemHealth(healthRes.data);
    } catch (error) {
      console.error('Admin data fetch error:', error);
      if (error.response?.status === 403) {
        toast.error('Access denied. Admin privileges required.');
        navigate('/dashboard');
      } else {
        toast.error('Failed to load admin dashboard');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUserStatusUpdate = async (username, newStatus) => {
    if (!window.confirm(`Are you sure you want to ${newStatus} user: ${username}?`)) {
      return;
    }

    try {
      await api.put(`/admin/users/${username}/status?status=${newStatus}`);
      toast.success(`User ${username} ${newStatus}d successfully`);
      // Refresh users list
      const usersRes = await api.get(`/admin/users?skip=${usersPagination.skip}&limit=${usersPagination.limit}`);
      setUsers(usersRes.data.users);
    } catch (error) {
      toast.error(`Failed to update user status: ${error.response?.data?.detail || 'Unknown error'}`);
    }
  };

  const handleSearch = async () => {
    try {
      const usersRes = await api.get(`/admin/users?skip=0&limit=10&search=${searchTerm}`);
      setUsers(usersRes.data.users);
      setUsersPagination({ skip: 0, limit: 10, total: usersRes.data.total });
    } catch (error) {
      toast.error('Search failed');
    }
  };

  const handlePageChange = async (newSkip) => {
    try {
      const usersRes = await api.get(`/admin/users?skip=${newSkip}&limit=${usersPagination.limit}&search=${searchTerm}`);
      setUsers(usersRes.data.users);
      setUsersPagination({ ...usersPagination, skip: newSkip });
    } catch (error) {
      toast.error('Failed to load users');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'active': return <FaCheck className="status-icon active" />;
      case 'suspended': return <FaClock className="status-icon suspended" />;
      case 'banned': return <FaBan className="status-icon banned" />;
      default: return null;
    }
  };

  const getActivityIcon = (type) => {
    switch(type) {
      case 'user_registration': return <FaUserPlus />;
      case 'vm_created': return <FaServer />;
      case 'payment': return <FaDollarSign />;
      default: return <FaClock />;
    }
  };

  if (loading) {
    return (
      <div className="admin-dashboard loading">
        <div className="spinner"></div>
        <p>Loading admin dashboard...</p>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      <div className="admin-header">
        <div className="header-content">
          <FaShieldAlt className="admin-icon" />
          <div>
            <h1>Admin Dashboard</h1>
            <p>Platform Management & Analytics</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="admin-tabs">
        <button 
          className={selectedTab === 'overview' ? 'active' : ''} 
          onClick={() => setSelectedTab('overview')}
        >
          Overview
        </button>
        <button 
          className={selectedTab === 'users' ? 'active' : ''} 
          onClick={() => setSelectedTab('users')}
        >
          User Management
        </button>
        <button 
          className={selectedTab === 'activity' ? 'active' : ''} 
          onClick={() => setSelectedTab('activity')}
        >
          Recent Activity
        </button>
        <button 
          className={selectedTab === 'system' ? 'active' : ''} 
          onClick={() => setSelectedTab('system')}
        >
          System Health
        </button>
      </div>

      {/* Overview Tab */}
      {selectedTab === 'overview' && stats && (
        <div className="admin-content">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon users">
                <FaUsers />
              </div>
              <div className="stat-info">
                <h3>{stats.total_users}</h3>
                <p>Total Users</p>
                <span className="stat-detail">{stats.active_users} active</span>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon vms">
                <FaServer />
              </div>
              <div className="stat-info">
                <h3>{stats.total_vms}</h3>
                <p>Active VMs</p>
                <span className="stat-detail">Running instances</span>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon storage">
                <FaDatabase />
              </div>
              <div className="stat-info">
                <h3>{stats.total_storage_gb.toFixed(2)} GB</h3>
                <p>Total Storage</p>
                <span className="stat-detail">Multi-cloud</span>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon revenue">
                <FaDollarSign />
              </div>
              <div className="stat-info">
                <h3>₹{stats.total_revenue.toLocaleString()}</h3>
                <p>Total Revenue</p>
                <span className="stat-detail">₹{stats.monthly_revenue.toLocaleString()} this month</span>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon growth">
                <FaChartLine />
              </div>
              <div className="stat-info">
                <h3>{stats.growth_rate > 0 ? '+' : ''}{stats.growth_rate}%</h3>
                <p>User Growth</p>
                <span className="stat-detail">Last 30 days</span>
              </div>
            </div>
          </div>

          <div className="subscriptions-breakdown">
            <h2>Subscription Breakdown</h2>
            <div className="subscription-bars">
              {Object.entries(stats.subscription_breakdown).map(([plan, count]) => (
                <div key={plan} className="subscription-bar">
                  <div className="bar-label">
                    <span className="plan-name">{plan.charAt(0).toUpperCase() + plan.slice(1)}</span>
                    <span className="plan-count">{count} users</span>
                  </div>
                  <div className="bar-container">
                    <div 
                      className={`bar-fill ${plan}`} 
                      style={{ width: `${(count / stats.total_users) * 100}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Users Tab */}
      {selectedTab === 'users' && (
        <div className="admin-content">
          <div className="users-header">
            <div className="search-bar">
              <FaSearch />
              <input 
                type="text" 
                placeholder="Search users by username or email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button onClick={handleSearch}>Search</button>
            </div>
          </div>

          <div className="users-table-container">
            <table className="users-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Plan</th>
                  <th>VMs</th>
                  <th>Storage</th>
                  <th>Spent</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.username}>
                    <td>
                      <div className="user-info">
                        <strong>{user.username}</strong>
                        <small>Joined {formatDate(user.created_at)}</small>
                      </div>
                    </td>
                    <td>{user.email}</td>
                    <td>
                      <span className={`plan-badge ${user.subscription_plan}`}>
                        {user.subscription_plan}
                      </span>
                    </td>
                    <td>{user.active_vms}</td>
                    <td>{user.storage_used_gb.toFixed(2)} GB</td>
                    <td>₹{user.total_spent.toLocaleString()}</td>
                    <td>
                      <span className={`status-badge ${user.status}`}>
                        {getStatusIcon(user.status)}
                        {user.status}
                      </span>
                    </td>
                    <td>
                      <div className="action-buttons">
                        {user.status !== 'active' && (
                          <button 
                            className="btn-activate"
                            onClick={() => handleUserStatusUpdate(user.username, 'active')}
                          >
                            Activate
                          </button>
                        )}
                        {user.status !== 'suspended' && (
                          <button 
                            className="btn-suspend"
                            onClick={() => handleUserStatusUpdate(user.username, 'suspended')}
                          >
                            Suspend
                          </button>
                        )}
                        {user.status !== 'banned' && (
                          <button 
                            className="btn-ban"
                            onClick={() => handleUserStatusUpdate(user.username, 'banned')}
                          >
                            Ban
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pagination">
            <button 
              disabled={usersPagination.skip === 0}
              onClick={() => handlePageChange(usersPagination.skip - usersPagination.limit)}
            >
              Previous
            </button>
            <span>
              Showing {usersPagination.skip + 1} - {Math.min(usersPagination.skip + usersPagination.limit, usersPagination.total)} of {usersPagination.total}
            </span>
            <button 
              disabled={usersPagination.skip + usersPagination.limit >= usersPagination.total}
              onClick={() => handlePageChange(usersPagination.skip + usersPagination.limit)}
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Activity Tab */}
      {selectedTab === 'activity' && (
        <div className="admin-content">
          <h2>Recent Platform Activity</h2>
          <div className="activity-list">
            {activities.map((activity, index) => (
              <div key={index} className={`activity-item ${activity.type}`}>
                <div className="activity-icon">
                  {getActivityIcon(activity.type)}
                </div>
                <div className="activity-details">
                  <p className="activity-description">{activity.description}</p>
                  <span className="activity-time">{formatDate(activity.timestamp)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Health Tab */}
      {selectedTab === 'system' && systemHealth && (
        <div className="admin-content">
          <h2>System Health</h2>
          <div className="health-grid">
            <div className="health-card">
              <h3>Database</h3>
              <div className={`health-status ${systemHealth.database.healthy ? 'healthy' : 'unhealthy'}`}>
                {systemHealth.database.healthy ? '✓ Healthy' : '✗ Unhealthy'}
              </div>
              <p>Size: {systemHealth.database.size_mb} MB</p>
              <p>Collections: {systemHealth.database.collections}</p>
            </div>

            <div className="health-card">
              <h3>Collections</h3>
              <ul className="collections-list">
                <li>Users: {systemHealth.collections.users}</li>
                <li>VM Assignments: {systemHealth.collections.vm_assignments}</li>
                <li>Files: {systemHealth.collections.files}</li>
                <li>Payments: {systemHealth.collections.payments}</li>
              </ul>
            </div>
          </div>
          <p className="health-timestamp">Last checked: {formatDate(systemHealth.timestamp)}</p>
        </div>
      )}
    </div>
  );
};

export default AdminDashboardPage;
