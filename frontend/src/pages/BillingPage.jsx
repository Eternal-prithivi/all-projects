// =============================================================================
// PAGE: BillingPage.jsx  (617 lines)
// ROUTE: /dashboard/billing
// PURPOSE: Invoice management + subscription status — list invoices, download PDF,
//          view current plan, upgrade via Stripe checkout, cancel subscription
// API: Uses apiClient → /api/billing/invoices, /api/payments/create-checkout,
//      /api/payments/status, /api/payments/cancel
// NOTE: Billing (invoices) ≠ Payments (Stripe). Both APIs used here — don't conflate them.
// DO NOT:
//   - Add Stripe keys or secrets in frontend — checkout session is created on the backend
//   - Show invoice totals in hardcoded "$" — use PreferencesContext.currencySymbol
//   - Remove subscription tier display — it drives feature gating in BYOC and other pages
// =============================================================================
import React, { useState, useEffect } from 'react';
import { apiClient } from '../api';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import { PageSkeleton } from '../components/Skeletons.jsx';
import '../styles/billing.css';
import PageHeader from '../components/ui/PageHeader.jsx';

function BillingPage() {
  const [subscription, setSubscription] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('cache_billing_sub')) || null; } catch { return null; }
  });
  const [paymentHistory, setPaymentHistory] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('cache_billing_history')) || []; } catch { return []; }
  });
  const [currentMonthCosts, setCurrentMonthCosts] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('cache_billing_costs')) || null; } catch { return null; }
  });
  // Only show loading skeleton if we have NO cached data at all
  const [loading, setLoading] = useState(() => !sessionStorage.getItem('cache_billing_sub'));
  const [processingPayment, setProcessingPayment] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadBillingData();
    loadCloudCosts();
    loadRazorpayScript();
  }, []);

  const loadRazorpayScript = () => {
    if (document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]')) {
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    document.body.appendChild(script);
  };

  const loadBillingData = async () => {
    try {
      // Only show skeleton if we don't have cached data
      if (!sessionStorage.getItem('cache_billing_sub')) {
        setLoading(true);
      }
      const [subRes, historyRes] = await Promise.all([
        apiClient.get('/payments/my-subscription'),
        apiClient.get('/payments/payment-history')
      ]);
      
      setSubscription(subRes.data);
      setPaymentHistory(historyRes.data);
      sessionStorage.setItem('cache_billing_sub', JSON.stringify(subRes.data));
      sessionStorage.setItem('cache_billing_history', JSON.stringify(historyRes.data));
    } catch (error) {
      console.error('Failed to load billing data:', error);
      toast.error('Failed to load billing data');
    } finally {
      setLoading(false);
    }
  };

  const loadCloudCosts = async () => {
    try {
      const response = await apiClient.get('/billing/current-month-summary');
      setCurrentMonthCosts(response.data);
      sessionStorage.setItem('cache_billing_costs', JSON.stringify(response.data));
    } catch (error) {
      console.error('Failed to load cloud costs:', error);
      // Don't show error toast, costs are optional
    }
  };

  const calculateNextBillingAmount = () => {
    if (!subscription?.plan_id || subscription.plan_id === 'free') return 0;
    
    const plans = {
      basic: { monthly: 499, yearly: 4990 },
      pro: { monthly: 1499, yearly: 14990 },
      enterprise: { monthly: 4999, yearly: 49990 }
    };
    
    return plans[subscription.plan_id]?.[subscription.billing_cycle || 'monthly'] || 0;
  };

  const calculateTotalBill = () => {
    let cloudCostsUSD = 0;
    let subscriptionINR = 0;
    
    // Add cloud usage costs (in USD)
    if (currentMonthCosts) {
      cloudCostsUSD += currentMonthCosts.costs.aws || 0;
      cloudCostsUSD += currentMonthCosts.costs.gcp || 0;
      cloudCostsUSD += currentMonthCosts.costs.azure || 0;
      // Platform fee only for free tier
      if (subscription?.plan_id === 'free') {
        cloudCostsUSD += currentMonthCosts.costs.platform_fee || 0;
      }
    }
    
    // Add subscription fee for next month (in INR)
    subscriptionINR = calculateNextBillingAmount();
    
    // Convert USD to INR (1 USD = 83 INR approx)
    const cloudCostsINR = cloudCostsUSD * 83;
    
    return {
      cloudUSD: cloudCostsUSD,
      cloudINR: cloudCostsINR,
      subscriptionINR: subscriptionINR,
      totalINR: cloudCostsINR + subscriptionINR
    };
  };

  const handlePayNow = async () => {
    const billBreakdown = calculateTotalBill();
    
    if (billBreakdown.totalINR === 0) {
      toast.info('No payment due at this time.');
      return;
    }

    if (!subscription?.plan_id || subscription.plan_id === 'free') {
      toast.info('Please select a plan first to enable billing.');
      return;
    }

    setProcessingPayment(true);
    
    try {
      // Create order for total bill (cloud costs + subscription)
      const orderResponse = await apiClient.post('/payments/create-order', {
        plan_id: subscription.plan_id,
        billing_cycle: subscription.billing_cycle || 'monthly',
        cloud_costs_usd: billBreakdown.cloudUSD  // Include cloud costs in payment
      });

      const { order_id, amount, currency, key_id, plan_name } = orderResponse.data;

      // Open Razorpay checkout
      const options = {
        key: key_id,
        amount: amount * 100, // Convert to paise
        currency: currency,
        name: 'Cloud Resource Optimization',
        description: `Total Bill - ${plan_name} Plan + Cloud Usage ($${billBreakdown.cloudUSD.toFixed(2)})`,
        order_id: order_id,
        handler: async function (response) {
          try {
            const verifyResponse = await apiClient.post('/payments/verify-payment', {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature
            });

            if (verifyResponse.data.success) {
              toast.success('🎉 Payment successful! Subscription renewed.');
              loadBillingData(); // Refresh data
            }
          } catch (error) {
            console.error('Payment verification failed:', error);
            toast.error('Payment verification failed. Please contact support.');
          } finally {
            setProcessingPayment(false);
          }
        },
        prefill: {
          name: localStorage.getItem('username') || '',
          email: localStorage.getItem('email') || '',
        },
        theme: {
          color: 'var(--gold-primary)'
        },
        modal: {
          ondismiss: function() {
            setProcessingPayment(false);
            toast.info('Payment cancelled');
          }
        }
      };

      const razorpay = new window.Razorpay(options);
      razorpay.open();
    } catch (error) {
      console.error('Error creating order:', error);
      toast.error('Failed to initiate payment. Please try again.');
      setProcessingPayment(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatCurrency = (amount) => {
    return `₹${amount.toLocaleString('en-IN')}`;
  };

  const getPlanDisplayName = (planId) => {
    const names = {
      free: 'Free',
      basic: 'Basic',
      pro: 'Pro',
      enterprise: 'Enterprise'
    };
    return names[planId] || planId;
  };

  const getStatusBadge = (status) => {
    if (subscription?.status === 'active' && subscription?.current_period_end) {
      const now = new Date();
      const endDate = new Date(subscription.current_period_end);
      const daysRemaining = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24));
      
      if (daysRemaining < 0) return { text: 'Expired', class: 'status-expired' };
      if (daysRemaining <= 7) return { text: 'Expiring Soon', class: 'status-warning' };
      return { text: 'Active', class: 'status-active' };
    }
    return { text: status || 'Inactive', class: 'status-inactive' };
  };

  if (loading) {
    return <PageSkeleton />;
  }

  const nextBillingAmount = calculateNextBillingAmount();
  const billBreakdown = calculateTotalBill();
  const statusBadge = getStatusBadge(subscription?.status);
  const currentPlanName = getPlanDisplayName(subscription?.plan_id || 'free');
  const now = new Date();
  const endDate = subscription?.current_period_end ? new Date(subscription.current_period_end) : null;
  const daysRemaining = endDate ? Math.ceil((endDate - now) / (1000 * 60 * 60 * 24)) : 0;
  const billingOverview = [
    { label: 'Current plan', value: currentPlanName, detail: subscription?.billing_cycle || 'Monthly' },
    { label: 'Next subscription', value: formatCurrency(nextBillingAmount), detail: subscription?.plan_id === 'free' ? 'No charge due' : 'Plan renewal' },
    { label: 'This month total', value: formatCurrency(Math.round(billBreakdown.totalINR)), detail: 'Cloud + plan cost' },
  ];

  return (
    <div className="billing-page">
      <PageHeader
        className="zenith-page-header--row billing-page-header"
        kicker="Finance center"
        title="Billing & Payments"
        subtitle="Manage your subscription, cloud spend, and renewal timing in one place."
      >
        {subscription?.plan_id !== 'free' && (
          <button
            type="button"
            className="zenith-page-header-actions btn-upgrade-plan-header"
            onClick={() => navigate('/dashboard/pricing')}
          >
            View All Plans
          </button>
        )}
      </PageHeader>

      <div className="billing-overview-grid">
        {billingOverview.map((item) => (
          <div key={item.label} className="billing-overview-card">
            <span className="billing-overview-label">{item.label}</span>
            <strong className="billing-overview-value">{item.value}</strong>
            <span className="billing-overview-detail">{item.detail}</span>
          </div>
        ))}
        <div className="billing-overview-card accent">
          <span className="billing-overview-label">Days remaining</span>
          <strong className="billing-overview-value">{daysRemaining > 0 ? daysRemaining : '—'}</strong>
          <span className="billing-overview-detail">
            {daysRemaining > 0 ? 'Until current period ends' : 'Current period ended'}
          </span>
        </div>
      </div>

      {/* Current Subscription */}
      <div className="billing-section subscription-card">
        <div className="section-header">
          <h2>Current Subscription</h2>
          <span className={`status-badge ${statusBadge.class}`}>
            {statusBadge.text}
          </span>
        </div>

        <div className="subscription-details">
          <div className="sub-detail-row">
            <div className="sub-detail">
              <span className="label">Plan</span>
              <span className="value">{getPlanDisplayName(subscription?.plan_id)}</span>
            </div>
            <div className="sub-detail">
              <span className="label">Billing Cycle</span>
              <span className="value">{subscription?.billing_cycle || 'N/A'}</span>
            </div>
            <div className="sub-detail">
              <span className="label">Next Billing Date</span>
              <span className="value">{formatDate(subscription?.current_period_end)}</span>
            </div>
            <div className="sub-detail">
              <span className="label">Next Payment</span>
              <span className="value amount">{formatCurrency(nextBillingAmount)}</span>
            </div>
          </div>

          {subscription?.plan_id !== 'free' && daysRemaining > 0 && (
            <div className="billing-countdown">
              <div className="countdown-info">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
                </svg>
                <span>
                  {daysRemaining} day{daysRemaining !== 1 ? 's' : ''} remaining in current billing period
                </span>
              </div>
            </div>
          )}

          <div className="subscription-limits">
            <h3>Plan Limits</h3>
            <div className="limits-grid">
              <div className="limit-item">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M2 5a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V5zm3.293 1.293a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 01-1.414-1.414L7.586 10 5.293 7.707a1 1 0 010-1.414zM11 12a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd"/>
                </svg>
                <div>
                  <span className="limit-label">Virtual Machines</span>
                  <span className="limit-value">
                    {subscription?.vm_limit === 999 ? 'Unlimited' : `${subscription?.vm_limit || 2} VMs`}
                  </span>
                </div>
              </div>
              <div className="limit-item">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z"/>
                  <path d="M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z"/>
                  <path d="M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z"/>
                </svg>
                <div>
                  <span className="limit-label">Storage</span>
                  <span className="limit-value">
                    {subscription?.storage_gb === 1000 ? '1 TB' : `${subscription?.storage_gb || 10} GB`}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="subscription-actions">
            {subscription?.plan_id === 'free' ? (
              <button 
                className="btn-upgrade-plan"
                onClick={() => navigate('/dashboard/pricing')}
              >
                ⬆️ Upgrade Plan
              </button>
            ) : (
              <>
                <button 
                  className={`btn-pay-now ${processingPayment ? 'processing' : ''}`}
                  onClick={handlePayNow}
                  disabled={processingPayment}
                >
                  {processingPayment ? (
                    <>
                      <span className="spinner"></span> Processing...
                    </>
                  ) : (
                    `💳 Pay Total Bill - ${formatCurrency(Math.round(billBreakdown.totalINR))}`
                  )}
                </button>
                <button 
                  className="btn-change-plan"
                  onClick={() => navigate('/dashboard/pricing')}
                >
                  Change Plan
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Current Month Cloud Costs */}
      {currentMonthCosts && (
        <div className="billing-section cloud-costs-card">
          <div className="section-header">
            <h2>Cloud Usage Costs (This Month)</h2>
            <span className="days-remaining-badge">
              {currentMonthCosts.days_remaining} days remaining
            </span>
          </div>
          <div className="costs-grid">
            <div className="cost-card aws">
              <div className="cost-header">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6.76 12.94l-.03.06-.02.07c0 .07.02.13.06.19l.03.03.06.06.04.02.09.02h2.83l.09-.02c.02-.01.03-.02.04-.02l.06-.06.03-.03a.33.33 0 00.06-.19v-.06l-.03-.07-.06-.11-.05-.05-2.06-2.7 2.07-2.71a.48.48 0 00.08-.17v-.06c0-.07-.02-.13-.06-.19l-.03-.03-.06-.06-.04-.02-.09-.02H6.95l-.09.02-.04.02-.06.06-.03.03-.06.08L4.86 9.7l-.97-1.32-.06-.08-.03-.03-.06-.06-.04-.02-.09-.02H.83l-.09.02c-.02.01-.03.02-.04.02l-.06.06L.6 8.3a.33.33 0 00-.06.19v.06l.03.07.06.11.05.05 2.06 2.7-2.07 2.71a.48.48 0 00-.08.17v.06c0 .07.02.13.06.19l.03.03.06.06.04.02.09.02h2.78l.09-.02c.02-.01.03-.02.04-.02l.06-.06.03-.03.06-.08 1.81-2.37.97 1.32zm9.64-2.88a.39.39 0 00-.15-.08 1.23 1.23 0 00-.24-.02h-.56V8.73c0-.16-.06-.29-.18-.41a.55.55 0 00-.41-.18h-1.09a.55.55 0 00-.41.18.55.55 0 00-.18.41v1.23h-.57c-.08 0-.16.01-.24.02a.39.39 0 00-.15.08.41.41 0 00-.08.15c-.01.07-.02.15-.02.24v.82c0 .09.01.17.02.24.01.06.04.11.08.15a.39.39 0 00.15.08c.08.01.16.02.24.02h.57v3.07c0 .9.21 1.56.63 1.98.42.42 1.03.63 1.82.63.25 0 .49-.01.73-.03.23-.02.44-.05.61-.09.08-.02.15-.06.2-.12.05-.06.08-.14.08-.24v-.88c0-.09-.03-.17-.08-.24-.05-.06-.13-.1-.24-.1h-.06l-.21.02-.28.02c-.23 0-.4-.06-.51-.17s-.17-.3-.17-.56v-3.29h1.09c.08 0 .16-.01.24-.02a.39.39 0 00.15-.08c.04-.04.07-.09.08-.15.01-.07.02-.15.02-.24v-.82c0-.09-.01-.17-.02-.24a.41.41 0 00-.08-.15zM23.6 12.94c-.03.17-.08.32-.16.45-.08.13-.2.23-.36.3-.16.07-.37.11-.62.11-.23 0-.43-.03-.59-.09-.16-.06-.29-.14-.39-.24s-.17-.22-.22-.36c-.05-.14-.07-.28-.07-.44 0-.16.02-.3.06-.43.04-.13.11-.24.19-.34.08-.1.19-.18.32-.25.13-.06.29-.1.46-.12l1.39-.17v.48c0 .28-.03.52-.07.73zm1.65-3.2c-.08-.36-.21-.67-.4-.92-.19-.25-.44-.44-.75-.57-.31-.13-.69-.19-1.14-.19-.3 0-.59.03-.86.08-.27.05-.51.11-.71.18-.1.04-.17.09-.21.16-.04.06-.06.13-.06.21v.9c0 .12.04.2.11.23.07.03.13.02.18-.02.23-.1.47-.18.72-.23.25-.05.49-.07.72-.07.38 0 .66.08.84.23.18.15.27.39.27.71v.31l-1.59.19c-.35.04-.66.11-.93.21-.27.1-.5.23-.68.38-.18.15-.32.33-.41.53-.09.2-.14.42-.14.66 0 .23.04.46.13.68.09.22.22.41.39.58.17.17.38.3.63.4.25.1.54.15.87.15.47 0 .87-.08 1.2-.25.33-.17.62-.38.85-.64v.48c0 .11.04.2.12.27.08.07.18.1.3.1h1.16c.08 0 .16-.01.24-.02a.39.39 0 00.15-.08c.04-.04.07-.09.08-.15.01-.07.02-.15.02-.24v-3.35c0-.47-.05-.9-.14-1.27z"/>
                </svg>
                <span>AWS</span>
              </div>
              <div className="cost-amount">${currentMonthCosts.costs.aws.toFixed(2)}</div>
            </div>
            <div className="cost-card gcp">
              <div className="cost-header">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12.19 2.38a9.344 9.344 0 0 1 9.45 9.311 9.344 9.344 0 0 1-9.396 9.457h-.03l-.026-.001c-.02-.001-.038.005-.057.001a9.344 9.344 0 0 1-9.145-9.485A9.344 9.344 0 0 1 12.17 2.379zm-.08 4.787a4.574 4.574 0 1 0 4.614 4.532 4.573 4.573 0 0 0-4.614-4.532z"/>
                </svg>
                <span>GCP</span>
              </div>
              <div className="cost-amount">${currentMonthCosts.costs.gcp.toFixed(2)}</div>
            </div>
            <div className="cost-card azure">
              <div className="cost-header">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M5.483 21.3H21.15l-3.371-5.708h-5.824zm9.694-12.307L11.725 2.7H5.08l7.531 13.067 4.153-7.214zM2.85 21.3h9.026L6.084 11.937z"/>
                </svg>
                <span>Azure</span>
              </div>
              <div className="cost-amount">${currentMonthCosts.costs.azure.toFixed(2)}</div>
            </div>
            {subscription?.plan_id === 'free' && (
              <div className="cost-card platform">
                <div className="cost-header">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
                  </svg>
                  <span>Platform Fee</span>
                </div>
                <div className="cost-amount">${currentMonthCosts.costs.platform_fee.toFixed(2)}</div>
                <div className="cost-note-small">⭐ Removed on paid plans</div>
              </div>
            )}
          </div>
          <div className="cost-breakdown-summary">
            <div className="summary-row">
              <span>Cloud Usage (AWS + GCP + Azure)</span>
              <span className="summary-amount">
                ${(currentMonthCosts.costs.aws + currentMonthCosts.costs.gcp + currentMonthCosts.costs.azure).toFixed(2)} USD
              </span>
            </div>
            <div className="summary-row conversion-row">
              <span>  └─ Converted to INR (@ ₹83/USD)</span>
              <span className="summary-amount">{formatCurrency(Math.round(billBreakdown.cloudINR))}</span>
            </div>
            {subscription?.plan_id === 'free' && (
              <>
                <div className="summary-row">
                  <span>Platform Fee</span>
                  <span className="summary-amount">${currentMonthCosts.costs.platform_fee.toFixed(2)} USD</span>
                </div>
                <div className="summary-row conversion-row">
                  <span>  └─ Converted to INR</span>
                  <span className="summary-amount">{formatCurrency(Math.round(currentMonthCosts.costs.platform_fee * 83))}</span>
                </div>
              </>
            )}
            {subscription?.plan_id !== 'free' && (
              <div className="summary-row highlight">
                <span>Subscription - {getPlanDisplayName(subscription?.plan_id)} ({subscription?.billing_cycle || 'monthly'})</span>
                <span className="summary-amount">{formatCurrency(nextBillingAmount)}</span>
              </div>
            )}
          </div>
          <div className="total-cost">
            <span className="total-label">Total Bill Due</span>
            <span className="total-amount">{formatCurrency(Math.round(billBreakdown.totalINR))}</span>
          </div>
          {subscription?.plan_id === 'free' ? (
            <button 
              className="btn-upgrade-plan" 
              onClick={() => navigate('/dashboard/pricing')}
            >
              ⬆️ Upgrade Plan to Pay Bills
            </button>
          ) : (
            <button 
              className="btn-pay-now" 
              onClick={handlePayNow}
              disabled={processingPayment}
            >
              {processingPayment ? (
                <>
                  <span className="spinner"></span>
                  Processing...
                </>
              ) : (
                `Pay Total Bill - ${formatCurrency(Math.round(billBreakdown.totalINR))}`
              )}
            </button>
          )}
          <div className="cost-note">
            💡 Pay now to cover cloud usage + subscription for the next month
          </div>
        </div>
      )}

      {/* Payment Method */}
      <div className="billing-section payment-method-card">
        <h2>Payment Method</h2>
        <div className="payment-method-content">
          <div className="payment-method-display">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <rect width="48" height="48" rx="8" fill="url(#razorpay-gradient)"/>
              <path d="M18 28L22 20L26 28L30 20" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <defs>
                <linearGradient id="razorpay-gradient" x1="0" y1="0" x2="48" y2="48">
                  <stop stopColor="#072654"/>
                  <stop offset="1" stopColor="#0B3E8A"/>
                </linearGradient>
              </defs>
            </svg>
            <div>
              <p className="payment-method-name">Razorpay</p>
              <p className="payment-method-note">Cards, UPI, Net Banking, Wallets</p>
              <p className="payment-method-description">
                Secure payment processing powered by Razorpay. All major payment methods supported.
              </p>
            </div>
          </div>
          <div className="payment-badges">
            <span className="payment-badge">💳 Cards</span>
            <span className="payment-badge">📱 UPI</span>
            <span className="payment-badge">🏦 Net Banking</span>
            <span className="payment-badge">👛 Wallets</span>
          </div>
        </div>
      </div>

      {/* Payment History */}
      <div className="billing-section payment-history-card">
        <div className="section-header">
          <h2>Payment History</h2>
          <span className="history-count">{paymentHistory.length} transaction{paymentHistory.length !== 1 ? 's' : ''}</span>
        </div>

        {paymentHistory.length === 0 ? (
          <div className="no-history">
            <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
              <rect width="80" height="80" rx="12" fill="var(--gold-glow)"/>
              <path d="M30 35h20M30 45h15M30 55h20" stroke="var(--gold-primary)" strokeWidth="3" strokeLinecap="round"/>
              <rect x="25" y="25" width="30" height="35" rx="2" stroke="var(--gold-primary)" strokeWidth="2"/>
            </svg>
            <p>No payment history yet</p>
            {subscription?.plan_id === 'free' && (
              <button className="btn-primary" onClick={() => navigate('/dashboard/pricing')}>
                Upgrade to View Payments
              </button>
            )}
          </div>
        ) : (
          <div className="payment-history-table-wrapper">
            <table className="payment-history-table data-card-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Plan</th>
                  <th>Billing Cycle</th>
                  <th>Amount</th>
                  <th>Payment ID</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {paymentHistory.map((payment) => (
                  <tr key={payment.id}>
                    <td className="payment-date" data-label="Date">{formatDate(payment.paid_at || payment.created)}</td>
                    <td data-label="Plan">
                      <span className="plan-badge">{getPlanDisplayName(payment.plan_id)}</span>
                    </td>
                    <td className="billing-cycle" data-label="Billing cycle">{payment.billing_cycle}</td>
                    <td className="payment-amount" data-label="Amount">{formatCurrency(payment.amount)}</td>
                    <td className="payment-id" data-label="Payment ID">
                      <code>{payment.payment_id?.substring(0, 20)}...</code>
                    </td>
                    <td data-label="Status">
                      <span className="payment-status-badge success">
                        ✓ Paid
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Billing Info */}
      <div className="billing-section billing-info-card">
        <h3>Billing Information</h3>
        <div className="billing-info-content">
          <div className="info-item">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd"/>
            </svg>
            <p>Payments are processed securely through Razorpay. You will be charged on your next billing date.</p>
          </div>
          <div className="info-item">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd"/>
            </svg>
            <p>All payment information is encrypted and stored securely. We never store your card details.</p>
          </div>
          <div className="info-item">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z"/>
            </svg>
            <p>Need help? Contact our support team at support@zenith.com or call +91-XXXXXXXXXX</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BillingPage;
