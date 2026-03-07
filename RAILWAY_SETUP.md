# Railway Environment Variables Setup

## Required Environment Variables

Railway needs these environment variables to be set for the app to work properly:

### 1. SECRET_KEY (CRITICAL - Currently Missing or Using Default)

The SECRET_KEY is used to sign JWT tokens. Without a proper secret key set in Railway, login tokens will be invalid.

**Generate a secure secret key:**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Set in Railway:**
1. Go to your Railway project dashboard
2. Select your service
3. Go to "Variables" tab
4. Click "New Variable"
5. Name: `SECRET_KEY`
6. Value: (paste the generated secret key)
7. Click "Add"

### 2. DATABASE_URL (Auto-set by Railway)

Railway automatically sets this when you add a PostgreSQL database.
- **Status**: ✅ Already set

### 3. ENVIRONMENT (Optional but Recommended)

Set to "production" for production deployments.

```
ENVIRONMENT=production
```

### 4. PORT (Auto-set by Railway)

Railway automatically sets this.
- **Status**: ✅ Already set (8080)

## Current Issue Diagnosis

**Problem**: Login works (returns 200 OK and token) but subsequent API calls fail with 401 Unauthorized.

**Root Cause**: The SECRET_KEY environment variable is either:
1. Not set in Railway (using default "your-secret-key-change-this-in-production")
2. Set inconsistently between deployments
3. Being read incorrectly

**Solution**: Set a proper SECRET_KEY in Railway environment variables.

## How to Verify After Setting SECRET_KEY

1. Wait for Railway to redeploy (automatic after setting env var)
2. Test login and dashboard access:

```bash
# Test login
TOKEN=$(curl -s -X POST https://noble-manifestation-production.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"svidron.robert@gmail.com","password":"Plexpass"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"

# Test /me endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://noble-manifestation-production.up.railway.app/api/v1/auth/me
```

If the /me endpoint returns your user info (not 401), the issue is fixed!

## Debug Endpoints

Use these endpoints to diagnose issues:

```bash
# Check environment setup
curl https://noble-manifestation-production.up.railway.app/api/v1/debug/env-check

# Check database and user setup
curl https://noble-manifestation-production.up.railway.app/api/v1/debug/db-stats

# Test auth configuration
curl https://noble-manifestation-production.up.railway.app/api/v1/debug/test-auth

# Test overall health
curl https://noble-manifestation-production.up.railway.app/api/v1/debug/health
```

## After Fixing

Once SECRET_KEY is properly set:
1. Clear browser localStorage (or use incognito)
2. Navigate to https://noble-manifestation-production.up.railway.app
3. Login with:
   - Email: svidron.robert@gmail.com
   - Password: Plexpass
4. You should see the dashboard!
