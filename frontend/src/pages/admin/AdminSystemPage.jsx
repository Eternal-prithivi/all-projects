import React, { useState, useEffect } from 'react';
import api from '../../api';
import { toast } from 'react-toastify';
import '../../styles/admin-pages.css';
import { FaServer, FaDatabase, FaCheckCircle, FaExclamationTriangle } from 'react-icons/fa';

const AdminSystemPage = () => {
  const [systemHealth, setSystemHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSystemHealth();
  }, []);

  const fetchSystemHealth = async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/system-health');
      setSystemHealth(res.data);
    } catch (error) {
      toast.error('Failed to load system health');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="spinner"></div>
        <p>Loading system health...</p>
      </div>
    );
  }

  return (
    <div className="admin-system-page">
      <div className="admin-page-header">
        <h1>System Health</h1>
        <p>Monitor platform infrastructure and database status</p>
      </div>

      <div className="health-grid">
        {/* Database Health */}
        <div className="admin-card">
          <div className="card-header">
            <FaDatabase />
            <h2>Database Status</h2>
          </div>
          <div className="card-body">
            <div className={`health-status ${systemHealth.database.healthy ? 'healthy' : 'unhealthy'}`}>
              {systemHealth.database.healthy ? <FaCheckCircle /> : <FaExclamationTriangle />}
              <span>{systemHealth.database.healthy ? 'Healthy' : 'Unhealthy'}</span>
            </div>
            <div className="health-details">
              <div className="detail-row">
                <span>Database Size:</span>
                <strong>{systemHealth.database.size_mb} MB</strong>
              </div>
              <div className="detail-row">
                <span>Collections:</span>
                <strong>{systemHealth.database.collections}</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Collections Info */}
        <div className="admin-card">
          <div className="card-header">
            <FaServer />
            <h2>Collections</h2>
          </div>
          <div className="card-body">
            <div className="collections-list">
              <div className="collection-item">
                <span>Users</span>
                <strong>{systemHealth.collections.users}</strong>
              </div>
              <div className="collection-item">
                <span>VM Assignments</span>
                <strong>{systemHealth.collections.vm_assignments}</strong>
              </div>
              <div className="collection-item">
                <span>Files</span>
                <strong>{systemHealth.collections.files}</strong>
              </div>
              <div className="collection-item">
                <span>Payments</span>
                <strong>{systemHealth.collections.payments}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="admin-card">
        <div className="card-footer">
          <p className="text-muted">Last checked: {formatDate(systemHealth.timestamp)}</p>
          <button onClick={fetchSystemHealth} className="btn-primary">
            Refresh Status
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminSystemPage;
