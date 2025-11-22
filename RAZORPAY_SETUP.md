# Razorpay Payment Integration Setup Guide

## 🚀 Quick Setup (15 Minutes)

This guide will help you integrate Razorpay payments into your Cloud Resource Optimization Platform. Razorpay is perfect for Indian businesses - **no invite required**, instant activation, and better fees than Stripe (2% vs 2.9%).

---

## 📋 Prerequisites

- Razorpay account (free signup, instant activation)
- Indian business/individual (PAN card for KYC)
- MongoDB database running
- Backend deployed or running locally

---

## 🔧 Step 1: Create Razorpay Account

### 1.1 Sign Up
1. Go to https://razorpay.com/
2. Click **"Sign Up"** (top right)
3. Fill in:
   - Email address
   - Password
   - Business name
   - Mobile number (you'll get OTP)
4. Verify email and mobile
5. **That's it!** Account created instantly ✅

### 1.2 Complete KYC (Required for Live Mode)
1. Go to **Settings → Account & Settings**
2. Upload:
   - PAN Card (business or personal)
   - Business proof (if company)
   - Bank account details
3. KYC approval takes **24-48 hours**
4. **Can still test immediately with Test Mode!**

---

## 🔑 Step 2: Get API Keys

### 2.1 Test Mode Keys (Available Immediately)
1. Login to Razorpay Dashboard
2. Go to **Settings → API Keys** (left sidebar)
3. Switch to **Test Mode** toggle (top right)
4. Click **"Generate Test Key"**
5. You'll see:
   ```
   Key ID: rzp_test_xxxxxxxxxxxxxx
   Key Secret: yyyyyyyyyyyyyyyyyyyy
   ```
6. **Copy both keys** (Secret is shown only once!)

### 2.2 Live Mode Keys (After KYC Approval)
1. Switch to **Live Mode** toggle
2. Click **"Generate Live Key"**
3. Copy Key ID and Secret
4. Store securely (never commit to Git!)

---

## 🎯 Step 3: Configure Backend

### 3.1 Add Environment Variables

Add these to your **Render.com** backend environment variables:

```bash
# Razorpay Configuration
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=yyyyyyyyyyyyyyyyyyyy
RAZORPAY_WEBHOOK_SECRET=whsec_zzzzzzzzzzzzzzzz  # Get in Step 4
```

**For local testing**, add to `backend/.env`:
```bash
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=yyyyyyyyyyyyyyyyyyyy
RAZORPAY_WEBHOOK_SECRET=whsec_zzzzzzzzzzzzzzzz
```

### 3.2 Install Razorpay SDK (Already Done)

```bash
cd backend
pip install razorpay==1.4.2
```

✅ Already added to `requirements.txt`!

---

## 🔔 Step 4: Setup Webhooks

Webhooks notify your backend when payments succeed/fail.

### 4.1 Configure Webhook Endpoint
1. Go to **Settings → Webhooks** in Razorpay Dashboard
2. Click **"+ Add New Webhook"**
3. Fill in:
   ```
   Webhook URL: https://zenith-backend-707i.onrender.com/api/payments/webhook
   Active Events: Select these 2:
   ✓ payment.captured
   ✓ payment.failed
   ```
4. Click **"Create Webhook"**
5. Copy the **Secret** (looks like `whsec_xxxxx`)
6. Add to environment variables as `RAZORPAY_WEBHOOK_SECRET`

### 4.2 Webhook Security
Your backend automatically verifies webhook signatures using:
```python
razorpay_client.utility.verify_webhook_signature(
    payload, signature, RAZORPAY_WEBHOOK_SECRET
)
```

---

## 💳 Step 5: Test Payment Flow

### 5.1 Test Cards (Test Mode Only)

| Card Number | Scenario | CVV | Expiry |
|------------|----------|-----|---------|
| `4111 1111 1111 1111` | Success | Any 3 digits | Any future date |
| `4012 0010 3714 1112` | Failed Payment | Any | Any |
| `5104 0600 0000 0008` | Success (Mastercard) | Any | Any |

### 5.2 Test Workflow

#### 1. Create Order (Backend)
```bash
curl -X POST https://zenith-backend-707i.onrender.com/api/payments/create-order \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "basic",
    "billing_cycle": "monthly"
  }'

# Response:
{
  "order_id": "order_xxxxxxxxxxxxx",
  "amount": 499,
  "currency": "INR",
  "key_id": "rzp_test_xxxxxx",
  "plan_name": "Basic",
  "billing_cycle": "monthly"
}
```

#### 2. Pay with Razorpay Checkout (Frontend)
```javascript
// Frontend integration (React example)
import logo from './assets/logo.png';

const options = {
  key: response.key_id,  // From Step 1
  amount: response.amount * 100,  // Paise
  currency: response.currency,
  name: "Cloud Resource Optimization",
  description: `${response.plan_name} Plan - ${response.billing_cycle}`,
  image: logo,  // Your logo
  order_id: response.order_id,
  handler: async function (razorpayResponse) {
    // Step 3: Verify payment
    const verifyResponse = await fetch('/api/payments/verify-payment', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(razorpayResponse)
    });
    
    if (verifyResponse.ok) {
      alert('Payment successful! Subscription activated.');
      window.location.href = '/dashboard';
    }
  },
  prefill: {
    name: user.name,
    email: user.email,
    contact: user.phone || ''
  },
  theme: {
    color: '#8B5CF6'  // Purple theme
  }
};

const rzp = new window.Razorpay(options);
rzp.open();
```

#### 3. Verify Payment (Backend)
```bash
curl -X POST https://zenith-backend-707i.onrender.com/api/payments/verify-payment \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "razorpay_order_id": "order_xxxxx",
    "razorpay_payment_id": "pay_xxxxx",
    "razorpay_signature": "signature_xxxxx"
  }'

# Response:
{
  "success": true,
  "message": "Payment verified and subscription activated",
  "plan_id": "basic",
  "valid_until": "2025-12-22T..."
}
```

---

## 📊 Pricing Plans

| Plan | Monthly | Yearly | Features |
|------|---------|--------|----------|
| **Free** | ₹0 | ₹0 | 2 VMs, 10GB, Demo mode |
| **Basic** | ₹499 | ₹4,990 | 5 VMs, 50GB, Real monitoring |
| **Pro** | ₹1,499 | ₹14,990 | 15 VMs, 200GB, AI + API access |
| **Enterprise** | ₹4,999 | ₹49,990 | Unlimited VMs, 1TB, 24/7 support |

### Razorpay Fees
- **2% per transaction** (₹10 on ₹500)
- No setup fees
- No annual fees
- Instant settlements (same day)

**Example**: Basic plan (₹499) → You receive ₹489 (₹10 Razorpay fee)

---

## 🛡️ Security Best Practices

### ✅ DO:
- ✅ Always verify payment signature on backend
- ✅ Store secrets in environment variables (never Git)
- ✅ Use Test Mode keys for development
- ✅ Enable webhook signature verification
- ✅ Log all payment events in MongoDB
- ✅ Handle payment failures gracefully

### ❌ DON'T:
- ❌ Never expose Key Secret to frontend
- ❌ Don't skip signature verification
- ❌ Don't trust frontend data - verify on backend
- ❌ Don't use Live keys in development
- ❌ Don't commit `.env` to Git

---

## 📦 MongoDB Collections

### Collection: `subscriptions`
```javascript
{
  user_id: "john_doe",
  plan_id: "basic",
  status: "active",
  razorpay_payment_id: "pay_xxxxx",
  razorpay_order_id: "order_xxxxx",
  billing_cycle: "monthly",
  current_period_start: ISODate("2025-11-22T..."),
  current_period_end: ISODate("2025-12-22T..."),
  auto_renew: true,
  updated_at: ISODate("2025-11-22T...")
}
```

### Collection: `payment_orders`
```javascript
{
  order_id: "order_xxxxx",
  user_id: "john_doe",
  plan_id: "basic",
  billing_cycle: "monthly",
  amount: 499,
  status: "paid",
  payment_id: "pay_xxxxx",
  created_at: ISODate("2025-11-22T..."),
  paid_at: ISODate("2025-11-22T...")
}
```

### Collection: `users` (updated on subscription)
```javascript
{
  username: "john_doe",
  email: "john@example.com",
  plan_id: "basic",
  vm_limit: 5,
  storage_limit_gb: 50,
  updated_at: ISODate("2025-11-22T...")
}
```

---

## 🚀 Going Live Checklist

### Before Launch:
- [ ] Complete KYC on Razorpay (24-48 hours)
- [ ] Get Live Mode API keys
- [ ] Update environment variables on Render
- [ ] Test with real card in Live Mode
- [ ] Configure webhook with Live URL
- [ ] Add terms & privacy policy URLs
- [ ] Enable 2FA on Razorpay account

### Launch Day:
- [ ] Switch from Test to Live keys
- [ ] Monitor first few payments
- [ ] Check webhook events in Razorpay Dashboard
- [ ] Verify MongoDB subscriptions are created
- [ ] Test user limit updates

---

## 📈 Revenue Projections

**Scenario**: 100 paid users per month

| Plan | Users | Monthly Revenue | Razorpay Fee (2%) | Your Net Revenue |
|------|-------|-----------------|-------------------|------------------|
| Basic | 50 | ₹24,950 | ₹499 | ₹24,451 |
| Pro | 30 | ₹44,970 | ₹899 | ₹44,071 |
| Enterprise | 20 | ₹99,980 | ₹2,000 | ₹97,980 |
| **Total** | **100** | **₹169,900** | **₹3,398** | **₹166,502** |

**Annual Revenue** (if 50% choose yearly plans): ~₹2M+ 🎉

---

## 🐛 Troubleshooting

### Issue: Payment fails with "Invalid Key"
**Solution**: Check if `RAZORPAY_KEY_ID` matches Test/Live mode

### Issue: Webhook not receiving events
**Solution**: 
1. Check webhook URL is public (not localhost)
2. Verify webhook secret matches
3. Check Render logs for errors

### Issue: Signature verification fails
**Solution**: 
1. Ensure `RAZORPAY_WEBHOOK_SECRET` is correct
2. Check webhook payload is not modified
3. Use raw request body (not parsed JSON)

### Issue: Payment successful but subscription not activated
**Solution**:
1. Check MongoDB connection
2. Verify webhook secret is correct
3. Check backend logs for errors
4. Call `/verify-payment` manually from frontend

---

## 📚 Resources

- **Razorpay Docs**: https://razorpay.com/docs/
- **Checkout Integration**: https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/
- **Webhooks**: https://razorpay.com/docs/webhooks/
- **Test Cards**: https://razorpay.com/docs/payments/payments/test-card-details/
- **Dashboard**: https://dashboard.razorpay.com/

---

## 🎉 Next Steps

1. **Complete KYC** on Razorpay (do this first - takes 24-48 hours)
2. **Test payments** with test cards
3. **Add frontend checkout** button
4. **Monitor webhooks** in Razorpay Dashboard
5. **Go live** after KYC approval!

---

## 💡 Why Razorpay > Stripe for India?

| Feature | Razorpay | Stripe |
|---------|----------|--------|
| **Availability** | ✅ Instant | ❌ Invite-only (2-4 weeks) |
| **Fees** | 2% | 2.9% + ₹2 |
| **KYC Time** | 24-48 hours | 1-2 weeks |
| **Indian Cards** | ✅ All cards | ⚠️ Limited |
| **UPI Support** | ✅ Yes | ❌ No |
| **Local Support** | ✅ Phone/Chat | ❌ Email only |
| **Settlements** | Same day | 7 days |

**Winner**: Razorpay 🏆

---

## 🆘 Need Help?

- **Razorpay Support**: support@razorpay.com (24/7)
- **Integration Issues**: Check Render logs
- **Payment Testing**: Use test cards from docs

---

**Happy Monetizing! 💰**

Start earning from your Cloud Resource Optimization Platform in 24-48 hours! 🚀
