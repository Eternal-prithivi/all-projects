import React, { useState, useEffect } from 'react';
import api from '../api';
import { toast } from 'react-toastify';
import '../styles/billing.css';

function BillingPage() {
  const [invoices, setInvoices] = useState([]);
  const [currentMonthCosts, setCurrentMonthCosts] = useState(null);
  const [currentSummary, setCurrentSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [paymentMethod, setPaymentMethod] = useState(null);
  const [generatingInvoice, setGeneratingInvoice] = useState(false);

  useEffect(() => {
    fetchBillingData();
    fetchPaymentMethod();
  }, []);

  const fetchBillingData = async () => {
    try {
      setLoading(true);
      
      // Fetch invoices
      const invoicesResponse = await api.get('/billing/invoices');
      setInvoices(invoicesResponse.data.invoices);
      setCurrentMonthCosts(invoicesResponse.data.current_month_costs);
      
      // Fetch current month summary
      const summaryResponse = await api.get('/billing/current-month-summary');
      setCurrentSummary(summaryResponse.data);
      
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch billing data:', error);
      toast.error('Failed to load billing data');
      setLoading(false);
    }
  };

  const fetchPaymentMethod = async () => {
    try {
      const response = await api.get('/settings/');
      setPaymentMethod(response.data.billing.payment_method);
    } catch (error) {
      console.error('Failed to fetch payment method:', error);
    }
  };

  const generateInvoice = async () => {
    try {
      setGeneratingInvoice(true);
      await api.post('/billing/invoices/generate');
      toast.success('Invoice generated successfully!');
      fetchBillingData();
    } catch (error) {
      console.error('Failed to generate invoice:', error);
      toast.error(error.response?.data?.detail || 'Failed to generate invoice');
    } finally {
      setGeneratingInvoice(false);
    }
  };

  const markAsPaid = async (invoiceId) => {
    try {
      await api.put(`/billing/invoices/${invoiceId}/mark-paid`);
      toast.success('Invoice marked as paid!');
      fetchBillingData();
    } catch (error) {
      console.error('Failed to mark invoice as paid:', error);
      toast.error(error.response?.data?.detail || 'Failed to update invoice');
    }
  };

  const downloadInvoice = (invoice) => {
    // Create a JSON blob and download it
    const dataStr = JSON.stringify(invoice, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataUri);
    downloadAnchor.setAttribute('download', `${invoice.invoice_id}.json`);
    downloadAnchor.click();
    toast.success('Invoice downloaded');
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'paid':
        return 'status-badge-paid';
      case 'pending':
        return 'status-badge-pending';
      case 'overdue':
        return 'status-badge-overdue';
      default:
        return '';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatCurrency = (amount) => {
    return `$${amount.toFixed(2)}`;
  };

  if (loading) {
    return (
      <div className="billing-page">
        <div className="loading-spinner">Loading billing data...</div>
      </div>
    );
  }

  return (
    <div className="billing-page">
      <div className="billing-header">
        <h1>Billing & Invoices</h1>
        <p>Consolidated billing across AWS, GCP, and Azure</p>
      </div>

      {/* Current Month Summary */}
      {currentSummary && (
        <div className="billing-section current-month-card">
          <div className="section-header">
            <h2>Current Month ({currentSummary.billing_period})</h2>
            <span className="days-remaining">{currentSummary.days_remaining} days remaining</span>
          </div>
          <div className="cost-breakdown">
            <div className="cost-item">
              <span className="cost-label">AWS</span>
              <span className="cost-value">{formatCurrency(currentSummary.costs.aws)}</span>
            </div>
            <div className="cost-item">
              <span className="cost-label">GCP</span>
              <span className="cost-value">{formatCurrency(currentSummary.costs.gcp)}</span>
            </div>
            <div className="cost-item">
              <span className="cost-label">Azure</span>
              <span className="cost-value">{formatCurrency(currentSummary.costs.azure)}</span>
            </div>
            <div className="cost-item">
              <span className="cost-label">Platform Fee</span>
              <span className="cost-value">{formatCurrency(currentSummary.costs.platform_fee)}</span>
            </div>
            <div className="cost-item cost-total">
              <span className="cost-label">Total (Month-to-Date)</span>
              <span className="cost-value">{formatCurrency(currentSummary.total)}</span>
            </div>
          </div>
          <p className="invoice-note">
            💡 Invoice will be generated on {formatDate(currentSummary.invoice_date)}
          </p>
        </div>
      )}

      {/* Payment Method */}
      <div className="billing-section payment-method-card">
        <h2>Payment Method</h2>
        <div className="payment-method-content">
          {paymentMethod ? (
            <div className="payment-method-display">
              <svg width="40" height="32" viewBox="0 0 40 32" fill="none">
                <rect width="40" height="32" rx="4" fill="#667eea"/>
                <rect x="4" y="8" width="32" height="4" fill="white" opacity="0.8"/>
                <rect x="4" y="16" width="12" height="4" fill="white" opacity="0.6"/>
              </svg>
              <div>
                <p className="payment-method-name">{paymentMethod}</p>
                <p className="payment-method-note">Default payment method</p>
              </div>
            </div>
          ) : (
            <p className="no-payment-method">No payment method on file</p>
          )}
          <button className="btn-update-payment" onClick={() => window.location.href = '/dashboard/settings'}>
            Update Payment Method
          </button>
        </div>
      </div>

      {/* Invoice History */}
      <div className="billing-section invoices-card">
        <div className="section-header">
          <h2>Invoice History</h2>
          <button 
            className="btn-generate-invoice" 
            onClick={generateInvoice}
            disabled={generatingInvoice}
          >
            {generatingInvoice ? 'Generating...' : '+ Generate Test Invoice'}
          </button>
        </div>

        {invoices.length === 0 ? (
          <div className="no-invoices">
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <rect width="64" height="64" rx="8" fill="rgba(102, 126, 234, 0.1)"/>
              <path d="M20 28h24M20 36h16M20 44h20" stroke="#667eea" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            <p>No invoices yet</p>
            <button className="btn-primary" onClick={generateInvoice}>
              Generate Your First Invoice
            </button>
          </div>
        ) : (
          <div className="invoices-table-wrapper">
            <table className="invoices-table">
              <thead>
                <tr>
                  <th>Invoice ID</th>
                  <th>Period</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Due Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => (
                  <tr key={invoice.invoice_id}>
                    <td className="invoice-id">{invoice.invoice_id}</td>
                    <td>{invoice.billing_period}</td>
                    <td className="invoice-amount">{formatCurrency(invoice.total)}</td>
                    <td>
                      <span className={`status-badge ${getStatusBadgeClass(invoice.status)}`}>
                        {invoice.status}
                      </span>
                    </td>
                    <td>{formatDate(invoice.due_date)}</td>
                    <td className="invoice-actions">
                      <button 
                        className="btn-action" 
                        onClick={() => downloadInvoice(invoice)}
                        title="Download"
                      >
                        📥
                      </button>
                      {invoice.status !== 'paid' && (
                        <button 
                          className="btn-action btn-pay" 
                          onClick={() => markAsPaid(invoice.invoice_id)}
                          title="Mark as Paid"
                        >
                          ✓ Pay
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default BillingPage;
