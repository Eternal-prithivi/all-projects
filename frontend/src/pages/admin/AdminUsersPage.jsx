import React, { useCallback, useState, useEffect } from 'react';
import api from '../../api';
import { toast } from 'react-toastify';
import '../../styles/admin-pages.css';
import { 
  FaSearch, FaCheck, FaBan, FaClock, FaUserPlus, FaFileDownload, FaFilePdf
} from 'react-icons/fa';
import { exportToCSV, prepareUsersForExport, exportUsersToPDF } from '../../utils/exportUtils';
import PageHeader from '../../components/ui/PageHeader.jsx';

const AdminUsersPage = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [pagination, setPagination] = useState({ skip: 0, limit: 20, total: 0 });

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/admin/users?skip=${pagination.skip}&limit=${pagination.limit}&search=${searchTerm}`);
      setUsers(res.data.users);
      setPagination(prev => ({ ...prev, total: res.data.total }));
    } catch {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [pagination.skip, pagination.limit, searchTerm]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleSearch = () => {
    setPagination(prev => ({ ...prev, skip: 0 }));
  };

  const handleStatusUpdate = async (username, newStatus) => {
    if (!window.confirm(`Are you sure you want to ${newStatus} user: ${username}?`)) {
      return;
    }

    try {
      await api.put(`/admin/users/${username}/status?status=${newStatus}`);
      toast.success(`User ${username} ${newStatus}d successfully`);
      fetchUsers();
    } catch (_error) {
      toast.error(`Failed to update user status: ${_error.response?.data?.detail || 'Unknown error'}`);
    }
  };

  const handlePageChange = (newSkip) => {
    setPagination(prev => ({ ...prev, skip: newSkip }));
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'active': return <FaCheck />;
      case 'suspended': return <FaClock />;
      case 'banned': return <FaBan />;
      default: return null;
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString();
  };

  const handleExportCSV = () => {
    const exportData = prepareUsersForExport(users);
    const filename = `users_export_${new Date().toISOString().split('T')[0]}.csv`;
    exportToCSV(exportData, filename);
    toast.success('Users exported to CSV successfully!');
  };

  const handleExportPDF = () => {
    const filename = `users_report_${new Date().toISOString().split('T')[0]}.pdf`;
    exportUsersToPDF(users, filename);
    toast.success('Users report generated successfully!');
  };

  return (
    <div className="admin-users-page">
      <PageHeader
        className="zenith-page-header--row"
        kicker="Admin"
        title="User Management"
        subtitle="Manage platform users and their accounts"
      >
        <div className="zenith-page-header-actions" style={{ display: 'flex', gap: '10px' }}>
          <button onClick={handleExportCSV} className="btn-export" aria-label="Export users data to CSV file">
            <FaFileDownload /> Export CSV
          </button>
          <button onClick={handleExportPDF} className="btn-export-pdf" aria-label="Generate users report PDF">
            <FaFilePdf /> Export PDF
          </button>
        </div>
      </PageHeader>

      {/* Search Bar */}
      <div className="admin-search-section">
        <div className="search-input-group">
          <FaSearch />
          <input 
            type="text" 
            placeholder="Search by username or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button onClick={handleSearch} className="btn-primary">Search</button>
        </div>
      </div>

      {/* Users Table */}
      <div className="admin-card">
        <div className="card-body no-padding">
          {loading ? (
            <div className="admin-loading">
              <div className="spinner"></div>
            </div>
          ) : (
            <div className="table-container">
              <table className="admin-table">
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
                        <div className="user-cell">
                          <div className="user-avatar-small">
                            {user.username.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <strong>{user.username}</strong>
                            <small>Joined {formatDate(user.created_at)}</small>
                          </div>
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
                              className="btn-sm btn-success"
                              onClick={() => handleStatusUpdate(user.username, 'active')}
                            >
                              Activate
                            </button>
                          )}
                          {user.status !== 'suspended' && (
                            <button 
                              className="btn-sm btn-warning"
                              onClick={() => handleStatusUpdate(user.username, 'suspended')}
                            >
                              Suspend
                            </button>
                          )}
                          {user.status !== 'banned' && (
                            <button 
                              className="btn-sm btn-danger"
                              onClick={() => handleStatusUpdate(user.username, 'banned')}
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
          )}
        </div>

        {/* Pagination */}
        <div className="card-footer">
          <div className="pagination">
            <button 
              disabled={pagination.skip === 0}
              onClick={() => handlePageChange(pagination.skip - pagination.limit)}
              className="btn-secondary"
            >
              Previous
            </button>
            <span className="pagination-info">
              Showing {pagination.skip + 1} - {Math.min(pagination.skip + pagination.limit, pagination.total)} of {pagination.total}
            </span>
            <button 
              disabled={pagination.skip + pagination.limit >= pagination.total}
              onClick={() => handlePageChange(pagination.skip + pagination.limit)}
              className="btn-secondary"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminUsersPage;
