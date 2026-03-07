# Railway Deployment Guide

Complete guide to deploy Budget App to Railway with PostgreSQL database.

## Prerequisites

- Railway account (sign up at https://railway.app)
- GitHub account
- Code pushed to https://github.com/rsvidron/Svidnet-Budget.git

## Step 1: Push to GitHub

If you haven't already pushed the code:

```bash
cd budget-app

# Initialize git (already done)
git init
git branch -m main

# Configure git user (use your details)
git config user.email "your-email@example.com"
git config user.name "Your Name"

# Add all files and commit
git add .
git commit -m "Initial commit: Budget App"

# Add remote and push
git remote add origin https://github.com/rsvidron/Svidnet-Budget.git
git push -u origin main
```

## Step 2: Create Railway Project

1. Go to https://railway.app and sign in
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose **rsvidron/Svidnet-Budget**
5. Railway will automatically detect the configuration

## Step 3: Add PostgreSQL Database

1. In your Railway project dashboard, click **"New"**
2. Select **"Database"**
3. Choose **"PostgreSQL"**
4. Railway will automatically create the database and link it
5. The `DATABASE_URL` environment variable will be set automatically

## Step 4: Configure Environment Variables

In the Railway project settings, add these environment variables:

### Required Variables

1. **SECRET_KEY** (Critical - Generate a secure key)
   ```bash
   # Generate with OpenSSL:
   openssl rand -hex 32
   ```
   Example value: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6`

2. **ENVIRONMENT**
   ```
   production
   ```

### Optional Variables

3. **FRONTEND_URL** (If hosting frontend separately)
   ```
   https://your-frontend-domain.com
   ```

4. **ACCESS_TOKEN_EXPIRE_MINUTES** (Default: 30)
   ```
   60
   ```

### Automatic Variables (Set by Railway)

These are automatically provided by Railway:
- `DATABASE_URL` - PostgreSQL connection string
- `PORT` - The port Railway expects your app to run on
- `RAILWAY_PUBLIC_DOMAIN` - Your Railway public URL

## Step 5: Deploy

1. Railway will automatically build and deploy
2. Wait for the build to complete (3-5 minutes)
3. Click on the deployment to see logs
4. Once deployed, click **"Settings"** → **"Generate Domain"** to get a public URL

## Step 6: Access Your Application

Your app will be available at:
```
https://your-app-name.up.railway.app
```

### First-Time Setup

1. Visit your Railway URL
2. Create your first account by clicking "Create a new account"
3. Login and start using the app!

## Step 7: Verify Deployment

### Check Backend Health

Visit: `https://your-app-name.up.railway.app/health`

Should return:
```json
{"status": "healthy"}
```

### Check API Documentation

Visit: `https://your-app-name.up.railway.app/docs`

You should see the Swagger UI with all API endpoints.

### Test the Frontend

The frontend should load at the root URL and allow you to:
1. Register a new account
2. Login
3. Access the dashboard

## Troubleshooting

### Build Fails

**Error: Dependencies not found**
- Check that `requirements.txt` exists in `backend/` folder
- Check that `package.json` exists in `frontend/` folder

**Solution:**
```bash
# Verify files exist
ls backend/requirements.txt
ls frontend/package.json
```

### Database Connection Issues

**Error: "could not connect to server"**
- Verify PostgreSQL database is created in Railway
- Check `DATABASE_URL` environment variable is set

**Solution:**
1. Go to Railway project → Databases → PostgreSQL
2. Copy the `DATABASE_URL` from Variables tab
3. Make sure it starts with `postgresql://` (not `postgres://`)

### Frontend Not Loading

**Symptom: API works but frontend shows errors**

**Check:**
1. Build completed successfully (check logs)
2. Frontend build artifacts exist
3. Backend is serving static files

**Solution:**
```bash
# Rebuild frontend locally to verify
cd frontend
npm run build
```

### CORS Errors

**Error: "Access-Control-Allow-Origin"**

**Solution:**
Add your Railway domain to CORS origins:
1. Set `FRONTEND_URL` environment variable
2. Or update `backend/app/core/config.py` to include your domain
3. Redeploy

### 500 Internal Server Error

**Check the logs:**
1. In Railway dashboard, click on your service
2. Click "View Logs"
3. Look for Python errors

**Common issues:**
- Database migrations not run
- Missing environment variables
- Database connection timeout

**Solution:**
```bash
# Check all required environment variables are set:
- SECRET_KEY
- DATABASE_URL (auto-set by Railway)
- ENVIRONMENT=production
```

## Database Migrations

Railway automatically creates tables on first startup. If you need to modify the database schema:

1. Update your models in `backend/app/models/`
2. Commit and push changes
3. Railway will rebuild and restart

For manual migrations, you can use Alembic:

```bash
# Install Alembic
pip install alembic

# Initialize migrations
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## Production Checklist

Before going live, ensure:

- [ ] `SECRET_KEY` is set to a secure random value (not default)
- [ ] PostgreSQL database is connected
- [ ] Environment is set to `production`
- [ ] CORS origins include your domain
- [ ] Database tables are created
- [ ] Test user registration works
- [ ] Test login works
- [ ] Test transaction upload works
- [ ] SSL/HTTPS is enabled (automatic on Railway)
- [ ] API documentation is accessible at `/docs`

## Monitoring

### View Logs

```bash
# In Railway dashboard:
1. Click your service
2. Click "Deployments"
3. Click latest deployment
4. View real-time logs
```

### Check Database

```bash
# Railway provides a built-in PostgreSQL client:
1. Click PostgreSQL service
2. Click "Data" tab
3. Run SQL queries
```

### Monitor Performance

Railway provides metrics:
- CPU usage
- Memory usage
- Network traffic
- Response times

Access from your service dashboard.

## Scaling

### Vertical Scaling (More Resources)

1. Go to your service settings
2. Upgrade to a higher tier plan
3. Allocate more RAM/CPU

### Horizontal Scaling

Railway Pro plans support:
- Multiple instances
- Load balancing
- Auto-scaling

## Cost Estimation

Railway pricing (as of 2024):

**Hobby Plan (Free)**
- $5 free credit/month
- Shared resources
- Perfect for testing

**Pro Plan ($20/month)**
- $20 in usage credits
- Dedicated resources
- Better performance

**Typical Usage:**
- Backend service: ~$3-5/month
- PostgreSQL database: ~$2-3/month
- Total: ~$5-8/month for small-scale use

## Updating Your App

To deploy updates:

```bash
# Make your changes
git add .
git commit -m "Update: description of changes"
git push origin main
```

Railway will automatically:
1. Detect the push
2. Build the new version
3. Deploy with zero downtime

## Custom Domain

To use your own domain:

1. Go to service settings
2. Click "Networking"
3. Add custom domain
4. Update DNS records as shown
5. Railway will provision SSL certificate

Example DNS records:
```
Type: CNAME
Name: budget (or @)
Value: your-app-name.up.railway.app
```

## Backup Strategy

### Database Backups

Railway Pro includes automatic daily backups. For manual backups:

```bash
# From Railway PostgreSQL service:
1. Click "Data" tab
2. Click "Backups"
3. Create manual backup
```

### Export Your Data

Use the built-in export feature:
1. Login to your app
2. Go to Transactions
3. Click "Export CSV"
4. Save regularly

## Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Rotate SECRET_KEY** regularly
3. **Enable 2FA** for all admin accounts
4. **Monitor access logs** in Railway
5. **Keep dependencies updated**
   ```bash
   pip list --outdated
   npm outdated
   ```

## Support & Resources

- Railway Documentation: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- PostgreSQL Docs: https://www.postgresql.org/docs/

## Next Steps

After successful deployment:

1. **Test thoroughly** - Try all features
2. **Set up monitoring** - Track errors and performance
3. **Configure backups** - Set up automatic backups
4. **Add custom domain** - Professional appearance
5. **Invite users** - Share your app!

## Troubleshooting Commands

```bash
# Check git status
git status

# View commit history
git log --oneline

# Check Railway CLI status (if installed)
railway status

# View environment variables
railway variables

# View logs
railway logs
```

## Railway CLI (Optional)

Install Railway CLI for easier management:

```bash
# Install
npm i -g @railway/cli

# Login
railway login

# Link project
railway link

# View logs
railway logs

# Run locally with Railway env
railway run python backend/app/main.py
```

---

## Quick Reference

### Railway Dashboard URLs
- **Main Dashboard**: https://railway.app/dashboard
- **Project Settings**: Click project → Settings
- **Database Console**: PostgreSQL service → Data tab
- **Logs**: Service → Deployments → View logs

### Important Files for Deployment
- `railway.json` - Railway configuration
- `nixpacks.toml` - Build configuration
- `Procfile` - Start command
- `runtime.txt` - Python version
- `Dockerfile` - Container configuration (optional)
- `.gitignore` - Files to exclude from git

### Environment Variables to Set
```bash
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ENVIRONMENT=production
```

### Health Check Endpoints
- Health: `https://your-app.up.railway.app/health`
- API Docs: `https://your-app.up.railway.app/docs`
- Frontend: `https://your-app.up.railway.app/`

---

**You're all set!** 🚀

Your Budget App is now deployed on Railway with PostgreSQL!
