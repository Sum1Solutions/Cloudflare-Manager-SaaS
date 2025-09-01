# Cloudflare Access Setup Guide

## What is Cloudflare Access?

Think of it as a security guard that sits IN FRONT of your website. Nobody reaches your app without passing through Cloudflare's authentication first.

## Step 1: Enable Access (5 minutes)

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select `cloudflaremanager.com` (your domain)
3. Click **Zero Trust** in sidebar
4. Click **Access** → **Applications**
5. Click **Add an Application**

## Step 2: Configure Application

### Basic Settings:
- **Type**: Self-hosted
- **Name**: Cloudflare Manager
- **Domain**: `cloudflaremanager.com`
- **Path**: Leave blank (protects entire site)

### Identity Providers (Choose any/all):
- ✅ **Google** (Most users have this)
- ✅ **GitHub** (Developers love this)
- ✅ **One-time PIN** (Email backup)

## Step 3: Create Access Policy

### Name: "Subscribers"

### Rules (combine with OR):
1. **Email ending in** → `@gmail.com` (or remove for any email)
2. **GitHub** → Any GitHub user
3. **Google** → Any Google user

### Advanced (Optional):
```javascript
// Later, you can add custom rules like:
- Check if user paid in your D1 database
- Restrict to specific email domains
- Require 2FA
```

## Step 4: Update Your Code

### In your Pages Functions (`/functions/api/[[path]].js`):

```javascript
export async function onRequest(context) {
  // Get authenticated user from Cloudflare headers
  const email = context.request.headers.get('CF-Access-Authenticated-User-Email');
  const userId = context.request.headers.get('CF-Access-Authenticated-User-Id');
  
  if (!email) {
    return new Response('No authentication found', { status: 401 });
  }
  
  // Check subscription status in D1
  const { env } = context;
  const user = await env.DB.prepare(
    'SELECT * FROM users WHERE email = ? AND subscription_expires > datetime("now")'
  ).bind(email).first();
  
  if (!user) {
    // New user or expired - redirect to payment
    return Response.redirect('/subscribe');
  }
  
  // User is authenticated AND paid!
  // Continue with normal app logic
  context.data.user = user;
  return await context.next();
}
```

### Database Schema:

```sql
-- Simple users table
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  cf_access_id TEXT UNIQUE,
  stripe_customer_id TEXT,
  subscription_expires DATETIME,
  cloudflare_api_key TEXT, -- Encrypted
  cloudflare_email TEXT,
  cloudflare_account_id TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Track their zones
CREATE TABLE user_zones (
  id INTEGER PRIMARY KEY,
  user_id INTEGER,
  zone_id TEXT,
  zone_name TEXT,
  -- ... other zone data
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Step 5: Payment Flow

```javascript
// /functions/subscribe.js
export async function onRequest(context) {
  const email = context.request.headers.get('CF-Access-Authenticated-User-Email');
  
  if (!email) {
    return new Response('Please login first', { status: 401 });
  }
  
  // Create Stripe Checkout session
  const session = await stripe.checkout.sessions.create({
    payment_method_types: ['card'],
    line_items: [{
      price: 'price_xxxxx', // Your $10/year price ID
      quantity: 1,
    }],
    mode: 'subscription',
    success_url: 'https://cloudflaremanager.com/welcome',
    cancel_url: 'https://cloudflaremanager.com/subscribe',
    customer_email: email,
  });
  
  return Response.redirect(session.url);
}
```

## Why This is AMAZING:

### 🔒 **Security**
- **Zero passwords** stored
- **Enterprise-grade** protection
- **DDoS protection** included
- **Bot protection** included
- **Rate limiting** automatic

### 💰 **Cost Effective**
- **FREE** for first 50 users
- Only **$3/user/month** after that
- At 100 users paying $10/year = $1000 revenue
- Your Access cost = $150/year (50 users free + 50 × $3)
- **Profit: $850/year**

### User Experience
1. User visits cloudflaremanager.com
2. Clicks "Sign in with Google"
3. Instantly authenticated
4. If new user → Stripe payment
5. Done! They're using the app

### 🛠️ **Developer Experience**
- **No auth code** to maintain
- **No password resets** to build
- **No 2FA** to implement
- **No session management**
- **No security updates** to worry about

## Comparison to Auth0 Approach:

| What | **Cloudflare Access** | **Auth0** |
|------|---------------------|-----------|
| Integration | 5 lines of code | 100+ lines |
| Login Flow | Happens before app | Redirect to Auth0 and back |
| Cost | $0-150/year | $276/year minimum |
| Speed | Instant (edge network) | API calls needed |
| Maintenance | Zero | SDK updates needed |

## The Magic Part:

Your ENTIRE authentication code becomes:
```javascript
const email = headers.get('CF-Access-Authenticated-User-Email');
// That's it. User is verified.
```

Compare to Auth0:
```javascript
// Install SDK
// Configure OAuth
// Handle callbacks  
// Verify tokens
// Refresh tokens
// Handle errors
// ... 100+ lines
```

## Ready to Set This Up?

1. **Today**: Set up Access on cloudflaremanager.com
2. **Tomorrow**: Add Stripe for payments
3. **Day 3**: Launch!

No passwords. No complexity. Just pure SaaS simplicity.