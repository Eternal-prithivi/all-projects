import React, { useState, useEffect } from 'react';
import { apiClient } from '../api';
import { useNotifications } from "../hooks/useNotifications";
import '../styles/billing.css';

function BillingPage() {
  const [invoices, setInvoices] = useState([]);
  const [currentMonthCosts, setCurrentMonthCosts] = useState(null);
  const [currentSummary, setCurrentSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [paymentMethod, setPaymentMethod] = useState(null);
  const [generatingInvoice, setGeneratingInvoice] = useState(false);
  const [budgets, setBudgets] = useState([]);
  const [showBudgetForm, setShowBudgetForm] = useState(false);
  const [budgetForm, setBudgetForm] = useState({
    name: 'Monthly Cloud Budget',
    amount: '',
    provider: 'all',
    period: 'monthly',
    alert_threshold: 80,
    phone_number: ''
  });

  useEffect(() => {
    fetchBillingData();
    fetchPaymentMethod();
    fetchBudgets();
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
      notifications.error('Failed to load billing data');
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

  const fetchBudgets = async () => {
    try {
      const response = await apiClient.get('/budgets/status');
      setBudgets(response.data);
    } catch (error) {
      console.error('Failed to fetch budgets:', error);
    }
  };

  const createBudget = async (e) => {
    e.preventDefault();
    try {
      await apiClient.post('/budgets/', {
        ...budgetForm,
        amount: parseFloat(budgetForm.amount),
        email_notifications: true
      });
      notifications.success('Budget created successfully!');
      setShowBudgetForm(false);
      setBudgetForm({
        name: 'Monthly Cloud Budget',
        amount: '',
        provider: 'all',
        period: 'monthly',
        alert_threshold: 80,
        phone_number: ''
      });
      fetchBudgets();
    } catch (error) {
      console.error('Failed to create budget:', error);
      notifications.error(error.response?.data?.detail || 'Failed to create budget');
    }
  };

  const deleteBudget = async (budgetId) => {
    try {
      await apiClient.delete(`/budgets/${budgetId}`);
      notifications.success('Budget deleted successfully!');
      fetchBudgets();
    } catch (error) {
      console.error('Failed to delete budget:', error);
      notifications.error(error.response?.data?.detail || 'Failed to delete budget');
    }
  };

  const testSMS = async () => {
    if (!budgetForm.phone_number) {
      notifications.error('Please enter a phone number first');
      return;
    }
    try {
      await apiClient.post(`/budgets/test-sms?phone_number=${encodeURIComponent(budgetForm.phone_number)}&budget_name=${encodeURIComponent(budgetForm.name)}`);
      notifications.success(`Test SMS sent to ${budgetForm.phone_number}`);
    } catch (error) {
      console.error('Failed to send test SMS:', error);
      notifications.error(error.response?.data?.detail || 'Failed to send test SMS');
    }
  };

  const generateInvoice = async () => {
    try {
      setGeneratingInvoice(true);
      await apiClient.post('/billing/invoices/generate');
      notifications.success('Invoice generated successfully!');
      fetchBillingData();
    } catch (error) {
      console.error('Failed to generate invoice:', error);
      notifications.error(error.response?.data?.detail || 'Failed to generate invoice');
    } finally {
      setGeneratingInvoice(false);
    }
  };

  const markAsPaid = async (invoiceId) => {
    try {
      await apiClient.put(`/billing/invoices/${invoiceId}/mark-paid`);
      notifications.success('Invoice marked as paid!');
      fetchBillingData();
    } catch (error) {
      console.error('Failed to mark invoice as paid:', error);
      notifications.error(error.response?.data?.detail || 'Failed to update invoice');
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
    notifications.success('Invoice downloaded');
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
          <h2>💰 Budget Alerts</h2>
          <button 
            className="btn-edit-budget" 
            onClick={() => setShowBudgetForm(!showBudgetForm)}
          >
            {showBudgetForm ? 'Cancel' : '+ Create Budget'}
          </button>
        </div>

        {showBudgetForm && (
          <form onSubmit={createBudget} className="budget-form">
            <div className="form-group">
              <label>Budget Name</label>
              <input
                type="text"
                placeholder="e.g., Monthly Cloud Budget"
                value={budgetForm.name}
                onChange={(e) => setBudgetForm({ ...budgetForm, name: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Amount ($)</label>
              <input
                type="number"
                value={budgetForm.amount}
                onChange={(e) => setBudgetForm({ ...budgetForm, amount: e.target.value })}
                placeholder="0.00"
                min="0"
                step="0.01"
                required
              />
            </div>
            <div className="form-group">
              <label>Provider</label>
              <select 
                value={budgetForm.provider} 
                onChange={(e) => setBudgetForm({ ...budgetForm, provider: e.target.value })}
              >
                <option value="all">All Providers</option>
                <option value="aws">AWS</option>
                <option value="gcp">GCP</option>
                <option value="azure">Azure</option>
              </select>
            </div>
            <div className="form-group">
              <label>Period</label>
              <select 
                value={budgetForm.period} 
                onChange={(e) => setBudgetForm({ ...budgetForm, period: e.target.value })}
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>
            <div className="form-group">
              <label>Alert Threshold (%)</label>
              <input
                type="number"
                value={budgetForm.alert_threshold}
                onChange={(e) => setBudgetForm({ ...budgetForm, alert_threshold: parseInt(e.target.value) || 80 })}
                placeholder="80"
                min="0"
                max="100"
                step="5"
              />
              <small>Get notified when spending reaches this percentage of budget</small>
            </div>
            <div className="form-group">
              <label>Phone Number (Optional)</label>
              <input
                type="tel"
                placeholder="+1234567890"
                value={budgetForm.phone_number}
                onChange={(e) => setBudgetForm({ ...budgetForm, phone_number: e.target.value })}
                pattern="\+[0-9]{10,15}"
                title="Phone number must start with + and include country code"
              />
              <small>📱 Receive SMS alerts when budget threshold is reached</small>
            </div>
            <div className="budget-form-actions">
              <button type="submit" className="btn-save">💾 Create Budget</button>
              {budgetForm.phone_number && (
                <button type="button" onClick={testSMS} className="btn-test-sms">📱 Test SMS</button>
              )}
            </div>
          </form>
        )}

        <div className="budgets-grid">
          {budgets.length === 0 ? (
            <div className="no-budget">
              <p>📊 No budgets configured</p>
              <p className="no-budget-hint">Create budget alerts to monitor your cloud spending and receive notifications</p>
              <button className="btn-primary" onClick={() => setShowBudgetForm(true)}>
                Create First Budget
              </button>
            </div>
          ) : (
            budgets.map(budgetStatus => (
              <div 
                key={budgetStatus.budget.id} 
                className={`budget-item ${budgetStatus.is_exceeded ? 'exceeded' : budgetStatus.is_near_limit ? 'warning' : ''}`}
              >
                <div className="budget-header-row">
                  <h4>{budgetStatus.budget.name}</h4>
                  <button 
                    onClick={() => deleteBudget(budgetStatus.budget.id)} 
                    className="delete-budget-btn"
                    title="Delete budget"
                  >
                    ×
                  </button>
                </div>
                <div className="budget-info">
                  <div className="budget-amount">
                    <span className="budget-label">Spent / Budget</span>
                    <span className="budget-value">
                      ${budgetStatus.budget.current_spend.toFixed(2)} / ${budgetStatus.budget.amount.toFixed(2)}
                    </span>
                  </div>
                  <div className="budget-meta">
                    <span>{budgetStatus.budget.period}</span>
                    <span>•</span>
                    <span>{budgetStatus.budget.provider.toUpperCase()}</span>
                    <span>•</span>
                    <span>{budgetStatus.budget.alert_threshold}% alert</span>
                  </div>
                </div>
                <div className="budget-progress">
                  <div className="progress-bar">
                    <div 
                      className={`progress-fill ${
                        budgetStatus.is_exceeded ? 'progress-over' : 
                        budgetStatus.is_near_limit ? 'progress-warning' : ''
                      }`}
                      style={{ width: `${Math.min(budgetStatus.utilization_percentage, 100)}%` }}
                    ></div>
                  </div>
                  <div className="progress-info">
                    <span>{budgetStatus.utilization_percentage.toFixed(1)}% used</span>
                    <span className={budgetStatus.is_exceeded ? 'over-budget-warning' : ''}>
                      {budgetStatus.is_exceeded 
                        ? `⚠️ Over by $${(budgetStatus.budget.current_spend - budgetStatus.budget.amount).toFixed(2)}`
                        : `$${budgetStatus.remaining_amount.toFixed(2)} remaining`
                      }
                    </span>
                  </div>
                </div>
                {budgetStatus.budget.phone_number && (
                  <div className="budget-alerts">
                    📱 SMS alerts enabled: {budgetStatus.budget.phone_number}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
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
