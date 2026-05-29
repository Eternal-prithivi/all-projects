// frontend/src/pages/PricingPage.jsx

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api';
import { toast } from 'react-toastify';
import { PageSkeleton } from '../components/Skeletons.jsx';
import '../styles/pricing.css';

const PricingPage = () => {
  const [plans, setPlans] = useState([]);
  const [currentSubscription, setCurrentSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processingPlanId, setProcessingPlanId] = useState(null);
  const [billingCycle, setBillingCycle] = useState('monthly'); // monthly or yearly
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
    loadRazorpayScript();
  }, []);

  const loadRazorpayScript = () => {
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    document.body.appendChild(script);
  };

  const loadData = async () => {
    try {
      const [plansRes, subRes] = await Promise.all([
        apiClient.get('/payments/plans'),
        apiClient.get('/payments/my-subscription')
      ]);
      setPlans(plansRes.data);
      setCurrentSubscription(subRes.data);
    } catch (error) {
      console.error('Error loading data:', error);
      toast.error('Failed to load pricing plans');
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (planId, billingCycle) => {
    if (planId === 'free') {
      toast.info('You are already on the free tier');
      return;
    }

    setProcessingPlanId(planId);
    
    try {
      // Step 1: Create Razorpay order
      const orderResponse = await apiClient.post('/payments/create-order', {
        plan_id: planId,
        billing_cycle: billingCycle
      });

      const { order_id, amount, currency, key_id, plan_name } = orderResponse.data;

      // Step 2: Open Razorpay checkout
      const options = {
        key: key_id,
        amount: amount * 100, // Convert to paise
        currency: currency,
        name: 'Cloud Resource Optimization',
        description: `${plan_name} Plan - ${billingCycle}`,
        order_id: order_id,
        handler: async function (response) {
          // Step 3: Verify payment
          try {
            const verifyResponse = await apiClient.post('/payments/verify-payment', {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature
            });

            if (verifyResponse.data.success) {
              toast.success('🎉 Payment successful! Subscription activated.');
              setTimeout(() => {
                navigate('/dashboard');
                window.location.reload(); // Reload to update limits
              }, 2000);
            }
          } catch (error) {
            console.error('Payment verification failed:', error);
            toast.error('Payment verification failed. Please contact support.');
          }
        },
        prefill: {
          name: localStorage.getItem('username') || '',
          email: localStorage.getItem('email') || '',
        },
        theme: {
          color: '#d4af37'
        },
        modal: {
          ondismiss: function() {
            setProcessingPlanId(null);
            toast.info('Payment cancelled');
          }
        }
      };

      const razorpay = new window.Razorpay(options);
      razorpay.open();
    } catch (error) {
      console.error('Error creating order:', error);
      toast.error('Failed to initiate payment. Please try again.');
      setProcessingPlanId(null);
    }
  };

  if (loading) {
    return (
      <div className="pricing-page">
        <div className="pricing-container">
          <PageSkeleton />
        </div>
      </div>
    );
  }

  return (
    <div className="pricing-page">
      <div className="pricing-container">
        <div className="pricing-header">
          <h1>Choose Your Plan</h1>
          <p>Select the perfect plan for your cloud resource needs</p>
          {currentSubscription && (
            <div className="current-plan-badge">
              Current Plan: <strong>{currentSubscription.plan_name}</strong>
            </div>
          )}
        </div>

        <div className="pricing-toggle">
          <button 
            className={`toggle-btn ${billingCycle === 'monthly' ? 'active' : ''}`}
            onClick={() => setBillingCycle('monthly')}
          >
            Monthly
          </button>
          <button 
            className={`toggle-btn ${billingCycle === 'yearly' ? 'active' : ''}`}
            onClick={() => setBillingCycle('yearly')}
          >
            Yearly (Save 17%)
          </button>
        </div>

        <div className="pricing-grid">
          {plans.map((plan) => {
            const isCurrentPlan = currentSubscription?.plan_id === plan.plan_id;
            const isFeatured = plan.plan_id === 'pro' && !isCurrentPlan;
            const isPlanDisabled = plan.plan_id === 'free' || processingPlanId !== null;

            return (
              <div
                key={plan.plan_id}
                className={`pricing-card ${isCurrentPlan ? 'current-plan' : ''} ${
                  isFeatured ? 'featured' : ''
                }`}
              >
                {isFeatured && (
                  <div className="featured-badge">Most Popular</div>
                )}

                <div className="plan-header">
                  {isCurrentPlan && (
                    <span className="pricing-kicker your-plan-chip">Your plan</span>
                  )}
                  <h3>{plan.name}</h3>
                  <p className="plan-description">{plan.description}</p>
                </div>

                <div className="plan-price">
                  {plan.price_monthly === 0 ? (
                    <>
                      <span className="price">₹0</span>
                      <span className="period">/forever</span>
                    </>
                  ) : (
                    <>
                      <span className="price">
                        ₹{billingCycle === 'yearly' ? plan.price_yearly : plan.price_monthly}
                      </span>
                      <span className="period">/{billingCycle === 'yearly' ? 'year' : 'month'}</span>
                    </>
                  )}
                </div>

                {plan.price_yearly > 0 && billingCycle === 'monthly' && (
                  <div className="yearly-price">
                    or ₹{plan.price_yearly}/year (save ₹{plan.price_monthly * 12 - plan.price_yearly})
                  </div>
                )}
                {plan.price_yearly > 0 && billingCycle === 'yearly' && (
                  <div className="yearly-price">
                    Save ₹{plan.price_monthly * 12 - plan.price_yearly} compared to monthly
                  </div>
                )}

                <ul className="plan-features">
                  {plan.features.map((feature, index) => (
                    <li key={index}>
                      <svg className="check-icon" viewBox="0 0 20 20" fill="currentColor">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                      {feature}
                    </li>
                  ))}
                </ul>

                <div className="plan-action">
                  {isCurrentPlan ? (
                    <button className="btn-current" disabled>
                      Current Plan
                    </button>
                  ) : plan.plan_id === 'free' ? (
                    <button className="btn-free" disabled>
                      Free Forever
                    </button>
                  ) : (
                    <button
                      className={`btn-upgrade ${
                        processingPlanId === plan.plan_id ? 'processing' : ''
                      }`}
                      onClick={() => handleUpgrade(plan.plan_id, billingCycle)}
                      disabled={isPlanDisabled}
                    >
                      {processingPlanId === plan.plan_id ? (
                        <>
                          <span className="spinner"></span> Processing...
                        </>
                      ) : (
                        'Upgrade Now'
                      )}
                    </button>
                  )}
                </div>

                {plan.plan_id !== 'free' && (
                  <div className="plan-limits">
                    <small>
                      {plan.vm_limit === 999 ? 'Unlimited' : plan.vm_limit} VMs •{' '}
                      {plan.storage_gb === 1000 ? '1TB' : `${plan.storage_gb}GB`} Storage
                    </small>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="pricing-footer">
          <div className="faq-section">
            <h2>Frequently Asked Questions</h2>
            <div className="faq-grid">
              <div className="faq-item">
                <h4>🔒 Is payment secure?</h4>
                <p>Yes! We use Razorpay's secure payment gateway with industry-standard encryption.</p>
              </div>
              <div className="faq-item">
                <h4>💳 What payment methods are accepted?</h4>
                <p>Credit cards, debit cards, UPI, net banking, and wallets via Razorpay.</p>
              </div>
              <div className="faq-item">
                <h4>🔄 Can I cancel anytime?</h4>
                <p>Yes, you can cancel your subscription anytime. Access continues until the end of your billing period.</p>
              </div>
              <div className="faq-item">
                <h4>💰 Is there a refund policy?</h4>
                <p>Yes, we offer a 7-day money-back guarantee if you're not satisfied.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PricingPage;
