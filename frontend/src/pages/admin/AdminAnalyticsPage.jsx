import React, { useState, useEffect } from 'react';
import api from '../../api';
import { toast } from 'react-toastify';
import '../../styles/admin-pages.css';
import { FaChartLine, FaUsers, FaServer, FaDollarSign, FaFileDownload, FaFilePdf } from 'react-icons/fa';
import { exportToCSV, prepareAnalyticsForExport, exportAnalyticsToPDF } from '../../utils/exportUtils';

const AdminAnalyticsPage = () => {
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState(null);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const response = await api.get('/admin/analytics');
      setAnalytics(response.data);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
      toast.error('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!analytics) return;
    const exportData = prepareAnalyticsForExport(analytics);
    const filename = `analytics_export_${new Date().toISOString().split('T')[0]}.csv`;
    exportToCSV(exportData, filename);
    toast.success('Analytics exported to CSV successfully!');
  };

  const handleExportPDF = () => {
    if (!analytics) return;
    const filename = `analytics_report_${new Date().toISOString().split('T')[0]}.pdf`;
    exportAnalyticsToPDF(analytics, filename);
    toast.success('Analytics report generated successfully!');
  };

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="spinner"></div>
        <p>Loading analytics...</p>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="admin-loading">
        <p>Failed to load analytics data</p>
      </div>
    );
  }

  return (
    <div className="admin-analytics">
      <div className="admin-page-header">
        <div>
          <h1>Platform Analytics</h1>
          <p>Detailed insights into platform performance</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={handleExportCSV} className="btn-export" aria-label="Export analytics data to CSV file">
            <FaFileDownload /> Export CSV
          </button>
          <button onClick={handleExportPDF} className="btn-export-pdf" aria-label="Generate analytics report PDF">
            <FaFilePdf /> Export PDF
          </button>
        </div>
      </div>

      {/* Revenue Trends */}
      <div className="analytics-section">
        <h2><FaDollarSign /> Revenue Trends (Last 6 Months)</h2>
        <div className="chart-container">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Month</th>
                <th>Revenue (₹)</th>
              </tr>
            </thead>
            <tbody>
              {analytics.revenue_trends.map((item, idx) => (
                <tr key={idx}>
                  <td>{item.month}</td>
                  <td>₹{item.revenue.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* User Growth */}
      <div className="analytics-section">
        <h2><FaUsers /> User Growth (Last 6 Months)</h2>
        <div className="chart-container">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Month</th>
                <th>New Users</th>
              </tr>
            </thead>
            <tbody>
              {analytics.user_growth.map((item, idx) => (
                <tr key={idx}>
                  <td>{item.month}</td>
                  <td>{item.new_users}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* VM Usage */}
      <div className="analytics-section">
        <h2><FaServer /> VM Usage (Last 6 Months)</h2>
        <div className="chart-container">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Month</th>
                <th>VMs Created</th>
              </tr>
            </thead>
            <tbody>
              {analytics.vm_usage.map((item, idx) => (
                <tr key={idx}>
                  <td>{item.month}</td>
                  <td>{item.vms_created}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Plan Distribution */}
      <div className="analytics-section">
        <h2><FaChartLine /> Plan Distribution</h2>
        <div className="plan-distribution">
          {Object.entries(analytics.plan_distribution).map(([plan, count]) => (
            <div key={plan} className="plan-stat">
              <span className="plan-name">{plan.toUpperCase()}</span>
              <span className="plan-count">{count} users</span>
            </div>
          ))}
        </div>
      </div>

      {/* Top Spenders */}
      <div className="analytics-section">
        <h2><FaDollarSign /> Top 10 Spenders</h2>
        <div className="chart-container">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Username</th>
                <th>Total Spent (₹)</th>
              </tr>
            </thead>
            <tbody>
              {analytics.top_spenders.map((spender, idx) => (
                <tr key={idx}>
                  <td>#{idx + 1}</td>
                  <td>{spender._id}</td>
                  <td>₹{spender.total_spent.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AdminAnalyticsPage;