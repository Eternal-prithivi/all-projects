# 💳 Stripe Payment Integration Setup Guide

## Overview
Your platform now includes **subscription billing** with 4 pricing tiers using Stripe. Users can upgrade, downgrade, and manage subscriptions seamlessly.

---

## 🚀 Quick Setup (15 Minutes)

### 1. Create Stripe Account
1. Go to https://dashboard.stripe.com/register
2. Sign up with your email
3. Complete KYC (Aadhaar + PAN for Indian accounts)
4. **Important**: Stay in **Test Mode** until you're ready for real payments

### 2. Get API Keys
1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy these keys:
   ```
   Publishable key: pk_test_xxxxx
   Secret key: sk_test_xxxxx
   ```

### 3. Create Webhook Endpoint
1. Go to https://dashboard.stripe.com/test/webhooks
2. Click **"Add endpoint"**
3. Set endpoint URL:
   ```
   https://zenith-backend-707i.onrender.com/api/payments/webhook
   ```
4. Select events to listen to:
   - ✅ `checkout.session.completed`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
5. Click **"Add endpoint"**
6. Copy the **Webhook signing secret**: `whsec_xxxxx`

### 4. Add Environment Variables to Render
Go to Render Dashboard → Backend Service → Environment:

```bash
# Stripe Keys (Test Mode)
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx
```

Click **Save** → Render will auto-redeploy.

### 5. Install Stripe SDK
```bash
cd backend
pip install stripe
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Add Stripe SDK"
git push origin development
```

---

## 💰 Pricing Plans

### Free Tier (₹0/month)
- 2 VMs (1 performance + 1 storage)
- 10 GB storage per VM
- Demo mode (mock data)
- Community support

### Basic (₹499/month or ₹4,990/year)
- 5 VMs (3 performance + 2 storage)
- 50 GB storage per VM
- Real cloud resources
- Email support (24h response)

### Professional (₹1,499/month or ₹14,990/year)
- 15 VMs (10 performance + 5 storage)
- 200 GB storage per VM
- AI recommendations
- Priority support (4h response)
- API access

### Enterprise (₹4,999/month or ₹49,990/year)
- Unlimited VMs
- 1 TB storage per VM
- Predictive analytics
- 24/7 support (1h response)
- Dedicated account manager

**Note**: Yearly plans save 2 months (17% discount)

---

## 🔌 API Endpoints Added

### User Endpoints
```
GET /api/payments/plans
  → Get all pricing plans

GET /api/payments/my-subscription
  → Get current subscription details

POST /api/payments/create-checkout
  Body: { plan_id: "basic", billing_cycle: "monthly" }
  → Returns Stripe checkout URL

POST /api/payments/cancel-subscription
  → Cancel subscription (access until period ends)

POST /api/payments/reactivate-subscription
  → Reactivate cancelled subscription

GET /api/payments/payment-history
  → Get past invoices and receipts
```

### Admin/Webhook Endpoint
```
POST /api/payments/webhook
  → Stripe webhook handler (automatic)
```

---

## 🎨 Frontend Integration Example

### 1. Pricing Page Component
```jsx
// frontend/src/pages/PricingPage.jsx
import { useState, useEffect } from 'react';
import api from '../api';

function PricingPage() {
  const [plans, setPlans] = useState([]);
  const [currentPlan, setCurrentPlan] = useState(null);
  
  useEffect(() => {
    // Load plans
    api.get('/payments/plans').then(res => setPlans(res.data));
    
    // Load current subscription
    api.get('/payments/my-subscription').then(res => setCurrentPlan(res.data));
  }, []);
  
  const handleUpgrade = async (planId, billingCycle) => {
    try {
      const response = await api.post('/payments/create-checkout', {
        plan_id: planId,
        billing_cycle: billingCycle,
        success_url: `${window.location.origin}/dashboard?payment=success`,
        cancel_url: `${window.location.origin}/pricing?payment=cancelled`
      });
      
      // Redirect to Stripe checkout
      window.location.href = response.data.checkout_url;
    } catch (error) {
      console.error('Payment failed:', error);
    }
  };
  
  return (
    <div className="pricing-container">
      <h1>Choose Your Plan</h1>
      <div className="plans-grid">
        {plans.map(plan => (
          <div key={plan.plan_id} className="plan-card">
            <h2>{plan.name}</h2>
            <p className="price">₹{plan.price_monthly}/month</p>
            <p className="description">{plan.description}</p>
            <ul className="features">
              {plan.features.map((feature, i) => (
                <li key={i}>✓ {feature}</li>
              ))}
            </ul>
            
            {currentPlan?.plan_id === plan.plan_id ? (
              <button disabled>Current Plan</button>
            ) : plan.plan_id === 'free' ? (
              <button disabled>Free Forever</button>
            ) : (
              <button onClick={() => handleUpgrade(plan.plan_id, 'monthly')}>
                Upgrade Now
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default PricingPage;
```

### 2. Add Route
```jsx
// frontend/src/main.jsx
import PricingPage from './pages/PricingPage';

// Add route:
<Route path="/pricing" element={<PricingPage />} />
```

---

## 🧪 Testing Payment Flow

### Test Card Numbers (Stripe Test Mode)
```
✅ Successful payment:
Card: 4242 4242 4242 4242
Expiry: Any future date (e.g., 12/25)
CVC: Any 3 digits (e.g., 123)
ZIP: Any 5 digits (e.g., 12345)

❌ Card declined:
Card: 4000 0000 0000 0002

⚠️ 3D Secure authentication required:
Card: 4000 0025 0000 3155
```

### Test Workflow
1. **Login** to your app as a test user
2. **Go to pricing page** (create the React component above)
3. **Click "Upgrade Now"** on Basic plan
4. **Enter test card**: `4242 4242 4242 4242`
5. **Complete checkout** → Redirected back to dashboard
6. **Check Stripe Dashboard** → You'll see the test subscription
7. **Check MongoDB** → `subscriptions` collection updated
8. **Verify limits** → Try requesting 3rd VM (should work now)

---

## 🔒 Security Best Practices

### ✅ DO:
- ✅ Keep `STRIPE_SECRET_KEY` in environment variables (never in code)
- ✅ Verify webhook signatures (already implemented)
- ✅ Use HTTPS only (Render provides free SSL)
- ✅ Stay in test mode until KYC approved
- ✅ Log all payment events to MongoDB

### ❌ DON'T:
- ❌ Store credit card numbers (let Stripe handle it)
- ❌ Expose secret keys in frontend
- ❌ Skip webhook signature verification
- ❌ Accept payments without proper authentication

---

## 📊 MongoDB Schema

### New Collection: `subscriptions`
```javascript
{
  "_id": ObjectId("..."),
  "user_id": "prithivi",
  "plan_id": "basic",
  "status": "active",
  "subscription_id": "sub_xxxxx", // Stripe subscription ID
  "stripe_customer_id": "cus_xxxxx",
  "current_period_start": ISODate("2025-11-22"),
  "current_period_end": ISODate("2025-12-22"),
  "cancel_at_period_end": false,
  "updated_at": ISODate("2025-11-22")
}
```

### Updated `users` Collection
```javascript
{
  "username": "prithivi",
  "email": "user@example.com",
  "plan_id": "basic",  // NEW: Current plan
  "vm_limit": 5,       // NEW: Max VMs allowed
  "storage_limit_gb": 50  // NEW: Storage quota
}
```

---

## 🚀 Going Live (Production Mode)

### When Ready for Real Payments:
1. **Complete KYC** in Stripe Dashboard
2. **Switch to Live Mode** (toggle in top-right)
3. **Get Live API Keys** from https://dashboard.stripe.com/apikeys
4. **Create Live Webhook** (same URL, but in live mode)
5. **Update Render Environment Variables** with live keys:
   ```bash
   STRIPE_SECRET_KEY=sk_live_xxxxx
   STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
   STRIPE_WEBHOOK_SECRET=whsec_xxxxx  # Live webhook secret
   ```

### Bank Payouts
- Stripe deposits to your bank account every 2-7 days
- Configure payout schedule in Stripe Dashboard → Settings → Payouts

---

## 💡 Revenue Projections

### Example Scenario:
```
10 Basic users:     10 × ₹499  = ₹4,990/month
5 Pro users:        5 × ₹1,499 = ₹7,495/month
1 Enterprise user:  1 × ₹4,999 = ₹4,999/month

Total Monthly Revenue: ₹17,484
Stripe Fees (2.9%):    -₹507
Net Revenue:           ₹16,977/month (₹2,03,724/year)
```

---

## 🛠️ Maintenance Tasks

### Weekly:
- Check Stripe Dashboard for failed payments
- Review webhook logs in Render
- Monitor subscription churn rate

### Monthly:
- Analyze payment success rate
- Review pricing effectiveness
- Send usage reports to customers

### Quarterly:
- Consider price adjustments
- Add new features to plans
- Survey customers for feedback

---

## 🆘 Troubleshooting

### Issue: Webhook not firing
**Solution**: Check Render logs for incoming requests. Verify webhook URL is correct and HTTPS.

### Issue: Payment succeeds but subscription not created
**Solution**: Check `checkout.session.completed` webhook handler logs. Verify MongoDB connection.

### Issue: User charged but no access granted
**Solution**: Check `subscriptions` collection for entry. Manually update if needed:
```javascript
db.subscriptions.updateOne(
  { user_id: "username" },
  { $set: { plan_id: "basic", status: "active" } }
);
```

### Issue: Test card declined
**Solution**: Use `4242 4242 4242 4242` only. Check Stripe Dashboard → Logs for error details.

---

## 📚 Resources

- Stripe Dashboard: https://dashboard.stripe.com
- Stripe Docs: https://stripe.com/docs
- Test Cards: https://stripe.com/docs/testing
- Webhook Testing: https://dashboard.stripe.com/test/webhooks
- Indian Tax Guide: https://stripe.com/docs/india

---

## ✅ Next Steps

1. **Run**: `pip install stripe` in backend
2. **Add Stripe keys** to Render environment
3. **Create pricing page** in frontend
4. **Test with 4242 card** in test mode
5. **Complete KYC** when ready for real payments
6. **Launch!** 🚀

---

**Total Setup Time**: 15-30 minutes
**Cost**: ₹0 setup fee + 2.9% per transaction
**Supported**: Credit/Debit cards, UPI, Netbanking, Wallets
