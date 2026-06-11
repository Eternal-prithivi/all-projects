// =============================================================================
// PAGE: BillingPage.jsx
// ROUTE: /dashboard/billing
// PURPOSE: Subscription, cloud usage, invoices, and payment history
// =============================================================================
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { apiClient } from '../api';
import { useNavigate } from 'react-router-dom';
import { PageSkeleton } from '../components/Skeletons.jsx';
import PageHeader from '../components/ui/PageHeader.jsx';
import { usePageRefresh } from '../hooks/usePageRefresh.js';
import { useNotifications } from '../hooks/useNotifications.js';
import { usePreferences } from '../context/PreferencesContext.jsx';
import { FX_USD_TO_INR, FX_ESTIMATE_LABEL } from '../config/billingConstants.js';
import { getPlanById, PATHS, SUPPORT_EMAIL } from '../data/productFacts.js';
import '../styles/billing.css';

function BillingPage() {
  const [subscription, setSubscription] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem('cache_billing_sub')) || null;
    } catch {
      return null;
    }
  });
  const [paymentHistory, setPaymentHistory] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem('cache_billing_history')) || [];
    } catch {
      return [];
    }
  });
  const [invoices, setInvoices] = useState([]);
  const [currentMonthCosts, setCurrentMonthCosts] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem('cache_billing_costs')) || null;
    } catch {
      return null;
    }
  });
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(() => !sessionStorage.getItem('cache_billing_sub'));
  const [processingPayment, setProcessingPayment] = useState(false);
  const [activeTab, setActiveTab] = useState('payments');
  const navigate = useNavigate();
  const { runPageRefresh, pageRefreshing } = usePageRefresh();
  const { error: notifyError, info: notifyInfo } = useNotifications();
  const { formatCurrency, formatDate } = usePreferences();

  const loadRazorpayScript = useCallback(() => {
    if (document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]')) {
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    document.body.appendChild(script);
  }, []);

  const loadBillingData = useCallback(async () => {
    try {
      if (!sessionStorage.getItem('cache_billing_sub')) {
        setLoading(true);
      }
      const [subRes, historyRes, invoicesRes, plansRes] = await Promise.all([
        apiClient.get('/payments/my-subscription'),
        apiClient.get('/payments/payment-history'),
        apiClient.get('/billing/invoices').catch(() => ({ data: { invoices: [] } })),
        apiClient.get('/payments/plans').catch(() => ({ data: [] })),
      ]);

      setSubscription(subRes.data);
      setPaymentHistory(historyRes.data);
      setInvoices(invoicesRes.data.invoices || []);
      setPlans(plansRes.data || []);
      sessionStorage.setItem('cache_billing_sub', JSON.stringify(subRes.data));
      sessionStorage.setItem('cache_billing_history', JSON.stringify(historyRes.data));
    } catch (error) {
      console.error('Failed to load billing data:', error);
      notifyError('Failed to load billing data.');
    } finally {
      setLoading(false);
    }
  }, [notifyError]);

  const loadCloudCosts = useCallback(async () => {
    try {
      const response = await apiClient.get('/billing/current-month-summary');
      setCurrentMonthCosts(response.data);
      sessionStorage.setItem('cache_billing_costs', JSON.stringify(response.data));
    } catch (error) {
      console.error('Failed to load cloud costs:', error);
    }
  }, []);

  useEffect(() => {
    loadBillingData();
    loadCloudCosts();
    loadRazorpayScript();
  }, [loadBillingData, loadCloudCosts, loadRazorpayScript]);

  const formatINR = (amount) =>
    `₹${Number(amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

  const resolvePlanMeta = (planId) => {
    const fromApi = plans.find((p) => p.plan_id === planId);
    if (fromApi) return fromApi;
    const fallback = getPlanById(planId);
    if (fallback) {
      return {
        plan_id: fallback.plan_id,
        name: fallback.name,
        price_monthly: fallback.price_monthly,
        price_yearly: fallback.price_yearly,
      };
    }
    return { plan_id: planId, name: planId || 'Free', price_monthly: 0, price_yearly: 0 };
  };

  const getPlanDisplayName = (planId) => resolvePlanMeta(planId).name;

  const calculateNextBillingAmount = () => {
    if (!subscription?.plan_id || subscription.plan_id === 'free') return 0;
    const meta = resolvePlanMeta(subscription.plan_id);
    const cycle = subscription.billing_cycle || 'monthly';
    return cycle === 'yearly' ? meta.price_yearly || 0 : meta.price_monthly || 0;
  };

  const billBreakdown = useMemo(() => {
    let cloudCostsUSD = 0;
    if (currentMonthCosts) {
      cloudCostsUSD += currentMonthCosts.costs.aws || 0;
      cloudCostsUSD += currentMonthCosts.costs.gcp || 0;
      cloudCostsUSD += currentMonthCosts.costs.azure || 0;
      cloudCostsUSD += currentMonthCosts.costs.storage_api_total || 0;
      if (subscription?.plan_id === 'free') {
        cloudCostsUSD += currentMonthCosts.costs.platform_fee || 0;
      }
    }
    let subscriptionINR = 0;
    if (subscription?.plan_id && subscription.plan_id !== 'free') {
      const meta = resolvePlanMeta(subscription.plan_id);
      const cycle = subscription.billing_cycle || 'monthly';
      subscriptionINR = cycle === 'yearly' ? meta.price_yearly || 0 : meta.price_monthly || 0;
    }
    const cloudCostsINR = cloudCostsUSD * FX_USD_TO_INR;
    return {
      cloudUSD: cloudCostsUSD,
      cloudINR: cloudCostsINR,
      subscriptionINR,
      totalINR: cloudCostsINR + subscriptionINR,
    };
  }, [currentMonthCosts, subscription, plans]);

  const handlePayNow = async () => {
    if (billBreakdown.totalINR === 0) {
      notifyInfo('No payment due at this time.');
      return;
    }
    if (!subscription?.plan_id || subscription.plan_id === 'free') {
      notifyInfo('Select a paid plan to enable billing.');
      return;
    }

    setProcessingPayment(true);
    try {
      const orderResponse = await apiClient.post('/payments/create-order', {
        plan_id: subscription.plan_id,
        billing_cycle: subscription.billing_cycle || 'monthly',
        cloud_costs_usd: billBreakdown.cloudUSD,
      });

      const { order_id, amount, currency, key_id, plan_name } = orderResponse.data;

      const options = {
        key: key_id,
        amount: amount * 100,
        currency,
        name: 'Zenith Cloud Platform',
        description: `${plan_name} + cloud usage (${formatCurrency(billBreakdown.cloudUSD)})`,
        order_id,
        handler: async function (response) {
          try {
            const verifyResponse = await apiClient.post('/payments/verify-payment', {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            if (verifyResponse.data.success) {
              navigate('/billing/success');
              return;
            }
          } catch (error) {
            console.error('Payment verification failed:', error);
            notifyError('Payment verification failed. Contact support if you were charged.');
          } finally {
            setProcessingPayment(false);
          }
        },
        prefill: {
          name: localStorage.getItem('username') || '',
          email: localStorage.getItem('email') || '',
        },
        theme: { color: '#d4af37' },
        modal: {
          ondismiss: function () {
            setProcessingPayment(false);
            navigate('/billing/cancel');
          },
        },
      };

      const razorpay = new window.Razorpay(options);
      razorpay.open();
    } catch (error) {
      console.error('Error creating order:', error);
      notifyError('Failed to initiate payment. Please try again.');
      setProcessingPayment(false);
    }
  };

  const getStatusBadge = () => {
    if (subscription?.status === 'active' && subscription?.current_period_end) {
      const daysRemaining = Math.ceil(
        (new Date(subscription.current_period_end) - new Date()) / (1000 * 60 * 60 * 24)
      );
      if (daysRemaining < 0) return { text: 'Expired', class: 'status-expired' };
      if (daysRemaining <= 7) return { text: 'Expiring soon', class: 'status-warning' };
      return { text: 'Active', class: 'status-active' };
    }
    return { text: subscription?.status || 'Inactive', class: 'status-inactive' };
  };

  if (loading) {
    return <PageSkeleton />;
  }

  const nextBillingAmount = calculateNextBillingAmount();
  const statusBadge = getStatusBadge();
  const currentPlanName = getPlanDisplayName(subscription?.plan_id || 'free');
  const endDate = subscription?.current_period_end
    ? new Date(subscription.current_period_end)
    : null;
  const daysRemaining = endDate
    ? Math.ceil((endDate - new Date()) / (1000 * 60 * 60 * 24))
    : 0;
  const billingPeriodProgress =
    endDate && subscription?.current_period_start
      ? Math.min(
          100,
          Math.max(
            0,
            ((new Date() - new Date(subscription.current_period_start)) /
              (endDate - new Date(subscription.current_period_start))) *
              100
          )
        )
      : null;

  const cloudUsageUSD =
    currentMonthCosts
      ? (currentMonthCosts.costs.aws || 0) +
        (currentMonthCosts.costs.gcp || 0) +
        (currentMonthCosts.costs.azure || 0) +
        (currentMonthCosts.costs.storage_api_total || 0)
      : 0;

  const isPaidPlan = subscription?.plan_id && subscription.plan_id !== 'free';

  return (
    <div className="billing-page animate-fade-in-up">
      <PageHeader
        className="billing-page-header"
        kicker="Account"
        title="Billing"
        subtitle="Subscription, usage, invoices, and payment history — all in one place."
        actions={
          <button
            type="button"
            className="billing-btn billing-btn--outline"
            onClick={() => navigate('/dashboard/pricing')}
          >
            {isPaidPlan ? 'Change plan' : 'View plans'}
          </button>
        }
        onRefresh={() =>
          runPageRefresh(
            async () => {
              await loadBillingData();
              await loadCloudCosts();
            },
            {
              loadingMessage: 'Refreshing billing…',
              successMessage: 'Billing data refreshed.',
              errorMessage: 'Failed to refresh billing.',
            }
          )
        }
        refreshing={pageRefreshing || loading}
      />

      {/* Summary metrics */}
      <div className="billing-metrics stagger-children">
        <div className="billing-metric-card">
          <span className="billing-metric-label">Current plan</span>
          <span className="billing-metric-value">{currentPlanName}</span>
          <span className="billing-metric-hint capitalize">
            {subscription?.billing_cycle || 'monthly'} billing
          </span>
        </div>
        <div className="billing-metric-card">
          <span className="billing-metric-label">Cloud usage (MTD)</span>
          <span className="billing-metric-value">{formatCurrency(cloudUsageUSD)}</span>
          <span className="billing-metric-hint">Month to date</span>
        </div>
        <div className="billing-metric-card">
          <span className="billing-metric-label">Next renewal</span>
          <span className="billing-metric-value">
            {endDate ? formatDate(endDate) : '—'}
          </span>
          <span className="billing-metric-hint">
            {daysRemaining > 0 ? `${daysRemaining} days left` : 'No active period'}
          </span>
        </div>
        <div className="billing-metric-card billing-metric-card--accent">
          <span className="billing-metric-label">Amount due</span>
          <span className="billing-metric-value">{formatINR(Math.round(billBreakdown.totalINR))}</span>
          <span className="billing-metric-hint">Cloud + subscription (INR)</span>
        </div>
      </div>

      <div className="billing-layout">
        {/* Left column — subscription & payment */}
        <div className="billing-layout-main">
          <section className="zenith-glass-panel billing-panel">
            <div className="billing-panel-header">
              <div>
                <h2 className="billing-panel-title">Subscription</h2>
                <p className="billing-panel-subtitle">
                  {isPaidPlan
                    ? `Your ${currentPlanName} plan renews automatically via Razorpay.`
                    : 'Upgrade to unlock multi-cloud features and remove platform fees.'}
                </p>
              </div>
              <span className={`billing-status-pill ${statusBadge.class}`}>{statusBadge.text}</span>
            </div>

            {billingPeriodProgress != null && daysRemaining > 0 && (
              <div className="billing-period-progress">
                <div className="billing-period-progress-labels">
                  <span>Current billing period</span>
                  <span>{daysRemaining} day{daysRemaining !== 1 ? 's' : ''} remaining</span>
                </div>
                <div className="billing-period-progress-track">
                  <div
                    className="billing-period-progress-fill"
                    style={{ width: `${billingPeriodProgress}%` }}
                  />
                </div>
              </div>
            )}

            <dl className="billing-detail-grid">
              <div className="billing-detail-item">
                <dt>Plan</dt>
                <dd>{currentPlanName}</dd>
              </div>
              <div className="billing-detail-item">
                <dt>Billing cycle</dt>
                <dd className="capitalize">{subscription?.billing_cycle || '—'}</dd>
              </div>
              <div className="billing-detail-item">
                <dt>Renewal date</dt>
                <dd>{endDate ? formatDate(endDate) : '—'}</dd>
              </div>
              <div className="billing-detail-item">
                <dt>Subscription fee</dt>
                <dd className="billing-detail-amount">
                  {isPaidPlan ? formatINR(nextBillingAmount) : 'Free'}
                </dd>
              </div>
            </dl>

            <div className="billing-limits">
              <h3 className="billing-limits-title">Included resources</h3>
              <div className="billing-limits-row">
                <div className="billing-limit-chip">
                  <span className="billing-limit-chip-label">Virtual machines</span>
                  <span className="billing-limit-chip-value">
                    {subscription?.vm_limit === 999
                      ? 'Unlimited'
                      : `${subscription?.vm_limit || 2} VMs`}
                  </span>
                </div>
                <div className="billing-limit-chip">
                  <span className="billing-limit-chip-label">Storage per VM</span>
                  <span className="billing-limit-chip-value">
                    {subscription?.storage_gb === 1000
                      ? '1 TB'
                      : `${subscription?.storage_gb || 10} GB`}
                  </span>
                </div>
              </div>
            </div>

            <div className="billing-panel-actions">
              {!isPaidPlan ? (
                <button
                  type="button"
                  className="billing-btn billing-btn--primary"
                  onClick={() => navigate('/dashboard/pricing')}
                >
                  Upgrade plan
                </button>
              ) : (
                <button
                  type="button"
                  className="billing-btn billing-btn--ghost"
                  onClick={() => navigate('/dashboard/pricing')}
                >
                  Change plan
                </button>
              )}
            </div>
          </section>

          <section className="zenith-glass-panel billing-panel">
            <h2 className="billing-panel-title">Payment method</h2>
            <p className="billing-panel-subtitle">
              Payments are processed securely through Razorpay at checkout.
            </p>
            <div className="billing-payment-provider">
              <div className="billing-payment-provider-icon" aria-hidden>
                <svg width="40" height="40" viewBox="0 0 48 48" fill="none">
                  <rect width="48" height="48" rx="10" fill="url(#rp-grad)" />
                  <path
                    d="M18 28L22 20L26 28L30 20"
                    stroke="white"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <defs>
                    <linearGradient id="rp-grad" x1="0" y1="0" x2="48" y2="48">
                      <stop stopColor="#072654" />
                      <stop offset="1" stopColor="#0B3E8A" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              <div>
                <p className="billing-payment-provider-name">Razorpay</p>
                <p className="billing-payment-provider-meta">
                  Cards, UPI, net banking, and wallets accepted at payment time.
                </p>
              </div>
            </div>
            <div className="billing-payment-methods">
              {['Cards', 'UPI', 'Net banking', 'Wallets'].map((method) => (
                <span key={method} className="billing-payment-method-tag">
                  {method}
                </span>
              ))}
            </div>
          </section>

          <section className="zenith-glass-panel billing-panel billing-panel--muted">
            <h2 className="billing-panel-title">Need help?</h2>
            <ul className="billing-help-list">
              <li>Invoices and receipts are available under the history tabs below.</li>
              <li>Payments are encrypted — card details are never stored on our servers.</li>
              <li>
                Questions about your bill?{' '}
                <button
                  type="button"
                  className="billing-link billing-link--btn"
                  onClick={() => navigate(`${PATHS.support}?new=1`)}
                >
                  Open a support ticket
                </button>{' '}
                or{' '}
                <button
                  type="button"
                  className="billing-link billing-link--btn"
                  onClick={() => navigate('/help?topic=billing')}
                >
                  billing FAQ
                </button>
                . Email{' '}
                <a href={`mailto:${SUPPORT_EMAIL}`} className="billing-link">
                  {SUPPORT_EMAIL}
                </a>
              </li>
            </ul>
          </section>
        </div>

        {/* Right column — usage & bill summary */}
        <aside className="billing-layout-side">
          {currentMonthCosts && (
            <section className="zenith-glass-panel billing-panel">
              <div className="billing-panel-header">
                <div>
                  <h2 className="billing-panel-title">Current period usage</h2>
                  <p className="billing-panel-subtitle">
                    {currentMonthCosts.billing_period} · {currentMonthCosts.days_remaining} days left
                  </p>
                </div>
              </div>

              <div className="billing-provider-costs">
                {[
                  { key: 'aws', label: 'AWS', amount: currentMonthCosts.costs.aws },
                  { key: 'gcp', label: 'GCP', amount: currentMonthCosts.costs.gcp },
                  { key: 'azure', label: 'Azure', amount: currentMonthCosts.costs.azure },
                ].map(({ key, label, amount }) => (
                  <div key={key} className={`billing-provider-cost billing-provider-cost--${key}`}>
                    <span>{label}</span>
                    <strong>{formatCurrency(amount || 0)}</strong>
                  </div>
                ))}
              </div>

              {(currentMonthCosts.costs.storage_api_total > 0 ||
                currentMonthCosts.storage_metering?.operations?.length > 0) && (
                <div className="billing-line-item">
                  <span>Storage API metering</span>
                  <span>{formatCurrency(currentMonthCosts.costs.storage_api_total || 0, 4)}</span>
                </div>
              )}

              {subscription?.plan_id === 'free' && (
                <div className="billing-line-item billing-line-item--muted">
                  <span>Platform fee (free tier)</span>
                  <span>{formatCurrency(currentMonthCosts.costs.platform_fee || 0)}</span>
                </div>
              )}

              <div className="billing-divider" />

              <div className="billing-line-item">
                <span>Cloud usage subtotal</span>
                <span>{formatCurrency(billBreakdown.cloudUSD)}</span>
              </div>
              <div className="billing-line-item billing-line-item--muted">
                <span>{FX_ESTIMATE_LABEL}</span>
                <span>{formatINR(Math.round(billBreakdown.cloudINR))}</span>
              </div>
              {isPaidPlan && (
                <div className="billing-line-item">
                  <span>
                    {currentPlanName} subscription ({subscription?.billing_cycle || 'monthly'})
                  </span>
                  <span>{formatINR(nextBillingAmount)}</span>
                </div>
              )}

              <div className="billing-total-due">
                <span>Total due</span>
                <strong>{formatINR(Math.round(billBreakdown.totalINR))}</strong>
              </div>

              {isPaidPlan ? (
                <button
                  type="button"
                  className={`billing-btn billing-btn--primary billing-btn--block ${processingPayment ? 'is-busy' : ''}`}
                  onClick={handlePayNow}
                  disabled={processingPayment}
                >
                  {processingPayment ? (
                    <>
                      <span className="billing-spinner" aria-hidden /> Processing…
                    </>
                  ) : (
                    `Pay ${formatINR(Math.round(billBreakdown.totalINR))}`
                  )}
                </button>
              ) : (
                <button
                  type="button"
                  className="billing-btn billing-btn--primary billing-btn--block"
                  onClick={() => navigate('/dashboard/pricing')}
                >
                  Upgrade to pay bills
                </button>
              )}

              <p className="billing-footnote">
                Covers cloud pass-through usage and your next subscription period.
              </p>

              {currentMonthCosts.storage_metering?.operations?.length > 0 && (
                <details className="billing-metering-details">
                  <summary>Storage API breakdown</summary>
                  <div className="table-responsive-scroll">
                    <table className="billing-metering-table data-card-table">
                      <thead>
                        <tr>
                          <th>Cloud</th>
                          <th>Operation</th>
                          <th>Count</th>
                          <th>Est.</th>
                        </tr>
                      </thead>
                      <tbody>
                        {currentMonthCosts.storage_metering.operations.map((row) => (
                          <tr key={`${row.csp}-${row.operation}`}>
                            <td data-label="Cloud">{row.csp}</td>
                            <td data-label="Operation">{row.label}</td>
                            <td data-label="Count">{row.count}</td>
                            <td data-label="Est.">{formatCurrency(row.estimated_usd, 4)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              )}
            </section>
          )}
        </aside>
      </div>

      {/* History tabs */}
      <section className="zenith-glass-panel billing-panel billing-history-section">
        <div className="billing-tabs" role="tablist" aria-label="Billing history">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'payments'}
            className={`billing-tab ${activeTab === 'payments' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('payments')}
          >
            Payments
            {paymentHistory.length > 0 && (
              <span className="billing-tab-count">{paymentHistory.length}</span>
            )}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'invoices'}
            className={`billing-tab ${activeTab === 'invoices' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('invoices')}
          >
            Invoices
            {invoices.length > 0 && <span className="billing-tab-count">{invoices.length}</span>}
          </button>
        </div>

        {activeTab === 'payments' && (
          <div role="tabpanel">
            {paymentHistory.length === 0 ? (
              <div className="billing-empty-state">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden>
                  <rect width="48" height="48" rx="12" fill="var(--gold-glow)" />
                  <path
                    d="M16 20h16M16 26h12M16 32h16"
                    stroke="var(--gold-primary)"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
                <p>No payments yet</p>
                <span className="billing-empty-hint">
                  Completed Razorpay transactions will appear here.
                </span>
              </div>
            ) : (
              <div className="billing-table-wrap">
                <table className="billing-table data-card-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Plan</th>
                      <th>Cycle</th>
                      <th>Amount</th>
                      <th>Reference</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paymentHistory.map((payment) => (
                      <tr key={payment.id}>
                        <td data-label="Date">
                          {formatDate(payment.paid_at || payment.created)}
                        </td>
                        <td data-label="Plan">
                          <span className="billing-plan-pill">
                            {getPlanDisplayName(payment.plan_id)}
                          </span>
                        </td>
                        <td data-label="Cycle" className="capitalize">
                          {payment.billing_cycle}
                        </td>
                        <td data-label="Amount" className="billing-table-amount">
                          {formatINR(payment.amount)}
                        </td>
                        <td data-label="Reference">
                          <code className="billing-ref-code">
                            {payment.payment_id?.substring(0, 18)}…
                          </code>
                        </td>
                        <td data-label="Status">
                          <span className="billing-status-pill status-active">Paid</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'invoices' && (
          <div role="tabpanel">
            {invoices.length === 0 ? (
              <div className="billing-empty-state">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none" aria-hidden>
                  <rect width="48" height="48" rx="12" fill="var(--gold-glow)" />
                  <rect
                    x="14"
                    y="12"
                    width="20"
                    height="26"
                    rx="2"
                    stroke="var(--gold-primary)"
                    strokeWidth="2"
                  />
                  <path d="M18 20h12M18 26h8" stroke="var(--gold-primary)" strokeWidth="2" />
                </svg>
                <p>No invoices yet</p>
                <span className="billing-empty-hint">
                  Monthly invoices are generated from your cloud usage at period end.
                </span>
              </div>
            ) : (
              <div className="billing-table-wrap">
                <table className="billing-table data-card-table">
                  <thead>
                    <tr>
                      <th>Invoice</th>
                      <th>Period</th>
                      <th>Amount</th>
                      <th>Due date</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((inv) => (
                      <tr key={inv.invoice_id}>
                        <td data-label="Invoice">
                          <code className="billing-ref-code">{inv.invoice_id}</code>
                        </td>
                        <td data-label="Period">{inv.billing_period}</td>
                        <td data-label="Amount" className="billing-table-amount">
                          {formatCurrency(inv.total)}
                        </td>
                        <td data-label="Due date">{formatDate(inv.due_date)}</td>
                        <td data-label="Status">
                          <span
                            className={`billing-status-pill billing-invoice-status--${inv.status}`}
                          >
                            {inv.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

export default BillingPage;
