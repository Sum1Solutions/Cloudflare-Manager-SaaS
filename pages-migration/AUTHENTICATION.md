# Authentication Setup Guide

The Cloudflare Manager Pages migration includes multiple authentication options:

## 1. Built-in Basic Authentication (Current Setup)

**For Development/Testing:**
- Username: `admin`
- Password: `cloudflare123`
- Cookie-based session management
- Logout functionality included

**Features:**
- ✅ Login page with styled UI
- ✅ Session cookies with proper security settings
- ✅ Logout functionality
- ✅ Middleware protection for all routes
- ✅ Automatic redirect to login when unauthorized

## 2. Cloudflare Access (Recommended for Production)

**Setup Steps:**
1. Go to Cloudflare Dashboard → Zero Trust → Access → Applications
2. Add Application → Self-hosted
3. Enter your Pages domain (e.g., `cloudflare-manager.pages.dev`)
4. Configure authentication providers:
   - Google Workspace
   - GitHub
   - Azure AD
   - Email OTP
   - And more...
5. Set access policies (specific users, groups, or domains)

**Benefits:**
- Enterprise-grade SSO
- Multi-factor authentication
- Audit logs
- Team access management
- No code changes required

**To Enable:**
1. Remove or disable `functions/_middleware.js`
2. Configure Access in Cloudflare Dashboard
3. All authentication handled automatically

## 3. Custom Authentication (Advanced)

**Options:**
- JWT tokens
- OAuth integration
- Database-backed user management
- API key authentication

**Implementation:**
- Modify `functions/_middleware.js`
- Add user registration endpoints
- Integrate with external auth providers

## Current Status

✅ **Basic Authentication Active**
- Local testing ready
- Username/password: admin/cloudflare123
- Session management working
- Logout functionality working

## Testing Authentication

**Login Test:**
```bash
curl -X POST http://localhost:8787/auth/login \
  -d "username=admin&password=cloudflare123" \
  -c cookies.txt -L
```

**Authenticated Access:**
```bash
curl -b cookies.txt http://localhost:8787
```

**Logout Test:**
```bash
curl -X POST -b cookies.txt http://localhost:8787/auth/logout \
  -c logout_cookies.txt -L
```

## Security Notes

- Current setup is for development only
- Use Cloudflare Access for production
- Environment variables for credentials in production
- HTTPS required for secure cookies
- Consider rate limiting for login attempts

## Next Steps

1. **For Development:** Keep current basic auth
2. **For Production:** Set up Cloudflare Access
3. **For Enterprise:** Implement custom auth with JWT/OAuth