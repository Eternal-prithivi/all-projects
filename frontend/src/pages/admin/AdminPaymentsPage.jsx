import React, { useCallback, useState, useEffect } from 'react';
import api from '../../api';
import { toast } from 'react-toastify';
import '../../styles/admin-pages.css';
import { FaDollarSign, FaFilter, FaCheckCircle, FaTimesCircle, FaClock, FaFileDownload, FaFilePdf } from 'react-icons/fa';
import { exportToCSV, preparePaymentsForExport, exportPaymentsToPDF } from '../../utils/exportUtils';

const AdminPaymentsPage = () => {
  const [loading, setLoading] = useState(true);
  const [payments, setPayments] = useState([]);
  const [stats, setStats] = useState({ total: 0, total_revenue: 0 });
  const [filter, setFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const paymentsPerPage = 20;

  const fetchPayments = useCallback(async () => {
    setLoading(true);
    try {
      const skip = (currentPage - 1) * paymentsPerPage;
      const statusParam = filter === 'all' ? '' : `&status=${filter}`;
      const response = await api.get(`/admin/payments?skip=${skip}&limit=${paymentsPerPage}${statusParam}`);
      
      setPayments(response.data.payments);
      setStats({
        total: response.data.total,
        total_revenue: response.data.total_revenue
      });
    } catch (error) {
      console.error('Failed to fetch payments:', error);
      toast.error('Failed to load payments');
    } finally {
      setLoading(false);
    }
  }, [currentPage, filter]);

  useEffect(() => {
    fetchPayments();
  }, [fetchPayments]);

  const handleExportCSV = () => {
    const exportData = preparePaymentsForExport(payments);
    const filename = `payments_export_${new Date().toISOString().split('T')[0]}.csv`;
    exportToCSV(exportData, filename);
    toast.success('Payments exported to CSV successfully!');
  };

  const handleExportPDF = () => {
    const filename = `payments_report_${new Date().toISOString().split('T')[0]}.pdf`;
    exportPaymentsToPDF(payments, stats, filename);
    toast.success('Payment report generated successfully!');
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'success':
        return <FaCheckCircle style={{ color: '#4caf50' }} />;
      case 'failed':
        return <FaTimesCircle style={{ color: '#f44336' }} />;
      case 'pending':
        return <FaClock style={{ color: '#ff9800' }} />;
      default:
        return <FaClock style={{ color: '#9e9e9e' }} />;
    }
  };

  const totalPages = Math.ceil(stats.total / paymentsPerPage);

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="spinner"></div>
        <p>Loading payments...</p>
      </div>
    );
  }

  return (
    <div className="admin-payments">
      <div className="admin-page-header">
        <div>
          <h1>Payment Transactions</h1>
          <p>Monitor all platform payments and revenue</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={handleExportCSV} className="btn-export" aria-label="Export payment transactions to CSV file">
            <FaFileDownload /> Export CSV
          </button>
          <button onClick={handleExportPDF} className="btn-export-pdf" aria-label="Generate payments report PDF">
            <FaFilePdf /> Export PDF
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', marginBottom: '20px' }}>
        <div className="stat-card">
          <div className="stat-icon stat-icon--gold">
            <FaDollarSign />
          </div>
          <div className="stat-info">
            <p className="stat-label">Total Revenue</p>
            <h3 className="stat-value">₹{stats.total_revenue.toLocaleString()}</h3>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
            <FaCheckCircle />
          </div>
          <div className="stat-info">
            <p className="stat-label">Total Transactions</p>
            <h3 className="stat-value">{stats.total}</h3>
          </div>
        </div>
      </div>

      {/* Filter Buttons */}
      <div className="filter-buttons" style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <button 
          className={filter === 'all' ? 'filter-btn active' : 'filter-btn'}
          onClick={() => { setFilter('all'); setCurrentPage(1); }}
        >
          All
        </button>
        <button 
          className={filter === 'success' ? 'filter-btn active' : 'filter-btn'}
          onClick={() => { setFilter('success'); setCurrentPage(1); }}
        >
          Success
        </button>
        <button 
          className={filter === 'pending' ? 'filter-btn active' : 'filter-btn'}
          onClick={() => { setFilter('pending'); setCurrentPage(1); }}
        >
          Pending
        </button>
        <button 
          className={filter === 'failed' ? 'filter-btn active' : 'filter-btn'}
          onClick={() => { setFilter('failed'); setCurrentPage(1); }}
        >
          Failed
        </button>
      </div>

      {/* Payments Table */}
      <div className="admin-card">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Username</th>
              <th>Plan</th>
              <th>Amount</th>
              <th>Billing Cycle</th>
              <th>Payment ID</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {payments.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '40px' }}>
                  No payments found
                </td>
              </tr>
            ) : (
              payments.map((payment) => (
                <tr key={payment.payment_id}>
                  <td>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      {getStatusIcon(payment.status)}
                      <span className={`status-badge status-${payment.status}`}>
                        {payment.status}
                      </span>
                    </span>
                  </td>
                  <td>{payment.username}</td>
                  <td>
                    <span className="plan-badge">{payment.plan_id || 'N/A'}</span>
                  </td>
                  <td>₹{payment.amount.toLocaleString()}</td>
                  <td>{payment.billing_cycle || 'N/A'}</td>
                  <td>
                    <code style={{ fontSize: '0.85em', color: '#9e9e9e' }}>
                      {payment.razorpay_payment_id ? payment.razorpay_payment_id.substring(0, 20) + '...' : 'N/A'}
                    </code>
                  </td>
                  <td>{payment.created_at ? new Date(payment.created_at).toLocaleDateString() : 'N/A'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <button 
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
            >
              Previous
            </button>
            <span>Page {currentPage} of {totalPages}</span>
            <button 
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPaymentsPage;