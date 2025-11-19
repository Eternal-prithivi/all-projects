import React, { useState, useEffect } from 'react';
import { apiClient } from '../api';
import { toast } from 'react-toastify';
import '../styles/billing.css';

function BillingPage() {
  const [invoices, setInvoices] = useState([]);
  const [currentMonthCosts, setCurrentMonthCosts] = useState(null);
  const [currentSummary, setCurrentSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [paymentMethod, setPaymentMethod] = useState(null);
  const [generatingInvoice, setGeneratingInvoice] = useState(false);
  const [budget, setBudget] = useState({
    monthly_budget: 0,
    alert_threshold: 80,
    email_alerts: true
  });
  const [editingBudget, setEditingBudget] = useState(false);
  const [budgetForm, setBudgetForm] = useState({
    monthly_budget: 0,
    alert_threshold: 80,
    email_alerts: true
  });

  useEffect(() => {
    fetchBillingData();
    fetchPaymentMethod();
    fetchBudget();
  }, []);

  const fetchBillingData = async () => {
    try {
      setLoading(true);
      
      // Fetch invoices
      const invoicesResponse = await apiClient.get('/billing/invoices');
      setInvoices(invoicesResponse.data.invoices);
      setCurrentMonthCosts(invoicesResponse.data.current_month_costs);
      
      // Fetch current month summary
      const summaryResponse = await apiClient.get('/billing/current-month-summary');
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
      const response = await apiClient.get('/settings/');
      setPaymentMethod(response.data.billing.payment_method);
    } catch (error) {
      console.error('Failed to fetch payment method:', error);
    }
  };

  const fetchBudget = async () => {
    try {
      const response = await apiClient.get('/billing/budget');
      setBudget(response.data.budget);
      setBudgetForm(response.data.budget);
    } catch (error) {
      console.error('Failed to fetch budget:', error);
    }
  };

  const updateBudget = async () => {
    try {
      await apiClient.put('/billing/budget', budgetForm);
      setBudget(budgetForm);
      setEditingBudget(false);
      toast.success('Budget settings updated successfully!');
    } catch (error) {
      console.error('Failed to update budget:', error);
      toast.error(error.response?.data?.detail || 'Failed to update budget');
    }
  };

  const cancelBudgetEdit = () => {
    setBudgetForm(budget);
    setEditingBudget(false);
  };

  const generateInvoice = async () => {
    try {
      setGeneratingInvoice(true);
      await apiClient.post('/billing/invoices/generate');
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
      await apiClient.put(`/billing/invoices/${invoiceId}/mark-paid`);
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

      {/* Budget Management */}
      <div className="billing-section budget-card">
        <div className="section-header">
          <h2>💰 Monthly Budget</h2>
          {!editingBudget && (
            <button className="btn-edit-budget" onClick={() => setEditingBudget(true)}>
              ✏️ Edit Budget
            </button>
          )}
        </div>

        {editingBudget ? (
          <div className="budget-form">
            <div className="form-group">
              <label>Monthly Budget ($)</label>
              <input
                type="number"
                value={budgetForm.monthly_budget}
                onChange={(e) => setBudgetForm({ ...budgetForm, monthly_budget: parseFloat(e.target.value) || 0 })}
                placeholder="0.00"
                min="0"
                step="10"
              />
            </div>
            <div className="form-group">
              <label>Alert Threshold (%)</label>
              <input
                type="number"
                value={budgetForm.alert_threshold}
                onChange={(e) => setBudgetForm({ ...budgetForm, alert_threshold: parseFloat(e.target.value) || 80 })}
                placeholder="80"
                min="0"
                max="100"
                step="5"
              />
              <small>Get notified when spending reaches this percentage of budget</small>
            </div>
            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={budgetForm.email_alerts}
                  onChange={(e) => setBudgetForm({ ...budgetForm, email_alerts: e.target.checked })}
                />
                Enable email alerts
              </label>
            </div>
            <div className="budget-form-actions">
              <button className="btn-save" onClick={updateBudget}>💾 Save Budget</button>
              <button className="btn-cancel" onClick={cancelBudgetEdit}>Cancel</button>
            </div>
          </div>
        ) : (
          <div className="budget-display">
            {budget.monthly_budget > 0 ? (
              <>
                <div className="budget-overview">
                  <div className="budget-amount">
                    <span className="budget-label">Monthly Budget</span>
                    <span className="budget-value">{formatCurrency(budget.monthly_budget)}</span>
                  </div>
                  {currentSummary && (
                    <>
                      <div className="budget-spent">
                        <span className="budget-label">Spent This Month</span>
                        <span className="budget-value">{formatCurrency(currentSummary.total)}</span>
                      </div>
                      <div className="budget-remaining">
                        <span className="budget-label">Remaining</span>
                        <span className={`budget-value ${currentSummary.total > budget.monthly_budget ? 'over-budget' : ''}`}>
                          {formatCurrency(Math.max(0, budget.monthly_budget - currentSummary.total))}
                        </span>
                      </div>
                    </>
                  )}
                </div>
                {currentSummary && (
                  <div className="budget-progress">
                    <div className="progress-bar">
                      <div 
                        className={`progress-fill ${
                          (currentSummary.total / budget.monthly_budget) * 100 >= budget.alert_threshold 
                            ? 'progress-warning' 
                            : ''
                        } ${
                          currentSummary.total > budget.monthly_budget 
                            ? 'progress-over' 
                            : ''
                        }`}
                        style={{ 
                          width: `${Math.min(100, (currentSummary.total / budget.monthly_budget) * 100)}%` 
                        }}
                      ></div>
                    </div>
                    <div className="progress-info">
                      <span>{((currentSummary.total / budget.monthly_budget) * 100).toFixed(1)}% of budget used</span>
                      {currentSummary.total > budget.monthly_budget && (
                        <span className="over-budget-warning">⚠️ Over budget by {formatCurrency(currentSummary.total - budget.monthly_budget)}</span>
                      )}
                      {(currentSummary.total / budget.monthly_budget) * 100 >= budget.alert_threshold && currentSummary.total <= budget.monthly_budget && (
                        <span className="approaching-limit">⚠️ Approaching budget limit</span>
                      )}
                    </div>
                  </div>
                )}
                <div className="budget-settings">
                  <span>📧 Email alerts: {budget.email_alerts ? 'Enabled' : 'Disabled'}</span>
                  <span>🔔 Alert threshold: {budget.alert_threshold}%</span>
                </div>
              </>
            ) : (
              <div className="no-budget">
                <p>📊 No budget set</p>
                <p className="no-budget-hint">Set a monthly budget to track your cloud spending</p>
                <button className="btn-primary" onClick={() => setEditingBudget(true)}>
                  Set Budget
                </button>
              </div>
            )}
          </div>
        )}
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
