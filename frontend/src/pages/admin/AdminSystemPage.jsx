import React, { useCallback, useState, useEffect } from 'react';
import api from '../../api';
import { toast } from 'react-toastify';
import '../../styles/admin-pages.css';
import { FaServer, FaDatabase, FaCheckCircle, FaExclamationTriangle } from 'react-icons/fa';
import PageHeader from '../../components/ui/PageHeader.jsx';

const AdminSystemPage = () => {
  const [systemHealth, setSystemHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchSystemHealth = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/system-health');
      setSystemHealth(res.data);
    } catch {
      toast.error('Failed to load system health');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSystemHealth();
  }, [fetchSystemHealth]);

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const handleExportAuditCsv = async () => {
    try {
      const res = await api.get('/audit-logs/export', {
        params: { days: 30, format: 'csv' },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `zenith_admin_audit_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Audit log exported');
    } catch {
      toast.error('Failed to export audit log');
    }
  };

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="spinner"></div>
        <p>Loading system health...</p>
      </div>
    );
  }

  const databaseHealth = systemHealth?.database ?? { healthy: false, size_mb: 0, collections: 0 };
  const collections = systemHealth?.collections ?? { users: 0, vm_assignments: 0, files: 0, payments: 0 };

  return (
    <div className="admin-system-page">
      <PageHeader
        kicker="Admin"
        title="System Health"
        subtitle="Monitor platform infrastructure and database status"
        actions={
          <button type="button" className="btn-export" onClick={handleExportAuditCsv}>
            Export audit CSV
          </button>
        }
      />

      <div className="health-grid">
        {/* Database Health */}
        <div className="admin-card">
          <div className="card-header">
            <FaDatabase />
            <h2>Database Status</h2>
          </div>
          <div className="card-body">
            <div className={`health-status ${databaseHealth.healthy ? 'healthy' : 'unhealthy'}`}>
              {databaseHealth.healthy ? <FaCheckCircle /> : <FaExclamationTriangle />}
              <span>{databaseHealth.healthy ? 'Healthy' : 'Unhealthy'}</span>
            </div>
            <div className="health-details">
              <div className="detail-row">
                <span>Database Size:</span>
                <strong>{databaseHealth.size_mb} MB</strong>
              </div>
              <div className="detail-row">
                <span>Collections:</span>
                <strong>{databaseHealth.collections}</strong>
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
                <strong>{collections.users}</strong>
              </div>
              <div className="collection-item">
                <span>VM Assignments</span>
                <strong>{collections.vm_assignments}</strong>
              </div>
              <div className="collection-item">
                <span>Files</span>
                <strong>{collections.files}</strong>
              </div>
              <div className="collection-item">
                <span>Payments</span>
                <strong>{collections.payments}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="admin-card">
        <div className="card-footer">
          <p className="text-muted">Last checked: {formatDate(systemHealth?.timestamp)}</p>
          <button onClick={fetchSystemHealth} className="btn-primary">
            Refresh Status
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminSystemPage;
