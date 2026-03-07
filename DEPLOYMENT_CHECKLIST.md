# Deployment Checklist

Complete checklist for deploying Budget App to Railway.

## Pre-Deployment

### GitHub Setup
- [ ] GitHub repository created at: https://github.com/rsvidron/Svidnet-Budget.git
- [ ] Code pushed to GitHub (see `GITHUB_SETUP.md`)
- [ ] All files committed (66 files)
- [ ] `.gitignore` configured properly
- [ ] Remote repository accessible

### Code Review
- [ ] All features working locally
- [ ] Backend runs without errors: `cd backend && ./run.sh`
- [ ] Frontend builds successfully: `cd frontend && npm run build`
- [ ] Database schema correct
- [ ] No hardcoded secrets in code
- [ ] Environment variables documented

### Documentation
- [ ] README.md complete
- [ ] QUICKSTART.md tested
- [ ] ARCHITECTURE.md reviewed
- [ ] RAILWAY_DEPLOYMENT.md ready
- [ ] API documentation at `/docs`

## Railway Setup

### Account & Project
- [ ] Railway account created (https://railway.app)
- [ ] GitHub account connected to Railway
- [ ] New project created
- [ ] Repository connected: rsvidron/Svidnet-Budget

### Database Configuration
- [ ] PostgreSQL database added
- [ ] `DATABASE_URL` environment variable auto-set
- [ ] Database connection verified
- [ ] Tables created automatically on first run

### Environment Variables

#### Required Variables
- [ ] `SECRET_KEY` - Generated with `openssl rand -hex 32`
  ```bash
  # Generate:
  openssl rand -hex 32

  # Example: 8f7a9b2c1d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9
  ```

- [ ] `ENVIRONMENT` - Set to `production`

#### Optional Variables
- [ ] `FRONTEND_URL` - If hosting frontend separately
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration (default: 30)
- [ ] `CORS_ORIGINS` - Additional domains for CORS

#### Auto-Set by Railway
- [ ] `DATABASE_URL` - PostgreSQL connection
- [ ] `PORT` - Application port
- [ ] `RAILWAY_PUBLIC_DOMAIN` - Public URL

### Deployment Configuration
- [ ] `railway.json` exists
- [ ] `nixpacks.toml` configured
- [ ] `Procfile` present
- [ ] `runtime.txt` specifies Python 3.11
- [ ] Build command correct
- [ ] Start command correct

## Deployment Process

### Initial Deployment
- [ ] Click "Deploy" in Railway
- [ ] Monitor build logs
- [ ] Wait for build completion (3-5 minutes)
- [ ] Check for build errors
- [ ] Verify deployment successful

### Domain Setup
- [ ] Generate Railway domain
- [ ] Test public URL
- [ ] (Optional) Configure custom domain
- [ ] SSL certificate auto-provisioned

### Testing

#### Backend Health
- [ ] Visit: `https://your-app.up.railway.app/health`
- [ ] Response: `{"status": "healthy"}`

#### API Documentation
- [ ] Visit: `https://your-app.up.railway.app/docs`
- [ ] Swagger UI loads
- [ ] All endpoints visible
- [ ] Can test endpoints

#### Frontend
- [ ] Root URL loads React app
- [ ] Login page accessible
- [ ] Registration page accessible
- [ ] No console errors (F12)
- [ ] Mobile responsive

### User Flow Testing
- [ ] Create new account
  - [ ] Email validation works
  - [ ] Password requirements enforced
  - [ ] Account created successfully

- [ ] Login
  - [ ] Credentials accepted
  - [ ] JWT token received
  - [ ] Redirected to dashboard

- [ ] Dashboard
  - [ ] Page loads without errors
  - [ ] Summary cards display
  - [ ] Charts render (if data exists)

- [ ] Transactions
  - [ ] Upload bank statement (CSV)
  - [ ] Transactions imported
  - [ ] Auto-categorization works
  - [ ] Filter transactions
  - [ ] Edit transaction
  - [ ] Delete transaction

- [ ] Categories
  - [ ] View default categories
  - [ ] Create custom category
  - [ ] Edit category color
  - [ ] Delete category

- [ ] Budgets
  - [ ] Create budget
  - [ ] View budget progress
  - [ ] Edit budget
  - [ ] Delete budget

- [ ] Savings Goals
  - [ ] Create goal
  - [ ] Add contribution
  - [ ] View progress
  - [ ] Delete goal

### Security Verification
- [ ] HTTPS enabled (automatic)
- [ ] JWT tokens working
- [ ] Passwords hashed (bcrypt)
- [ ] SQL injection protection (ORM)
- [ ] CORS configured correctly
- [ ] File upload size limits enforced
- [ ] Input validation working

### Performance Testing
- [ ] Page load time < 3 seconds
- [ ] API response time < 500ms
- [ ] Database queries optimized
- [ ] No N+1 query problems
- [ ] Static files cached

## Post-Deployment

### Monitoring Setup
- [ ] Review Railway metrics
- [ ] Check CPU usage
- [ ] Check memory usage
- [ ] Monitor error rates
- [ ] Set up alerts (optional)

### Backup Configuration
- [ ] Database backups enabled (Railway Pro)
- [ ] Regular data exports scheduled
- [ ] Backup strategy documented

### Documentation Updates
- [ ] Update README with live URL
- [ ] Document environment variables
- [ ] Add deployment date
- [ ] Update version number

### User Onboarding
- [ ] Create admin account
- [ ] Test full workflow
- [ ] Prepare user guide
- [ ] Set up support channel

## Maintenance Plan

### Regular Tasks
- [ ] Weekly: Check error logs
- [ ] Weekly: Review performance metrics
- [ ] Monthly: Database backup verification
- [ ] Monthly: Security updates
- [ ] Quarterly: Dependency updates

### Monitoring Checklist
- [ ] Set up error tracking (Sentry, etc.)
- [ ] Configure uptime monitoring
- [ ] Enable performance monitoring
- [ ] Create status page (optional)

## Rollback Plan

If deployment fails:

1. **Check Logs**
   ```bash
   # In Railway dashboard
   Service → Deployments → View Logs
   ```

2. **Common Issues**
   - Database connection failed → Check DATABASE_URL
   - Build failed → Check dependencies
   - Frontend errors → Check API URL configuration
   - CORS errors → Check CORS_ORIGINS

3. **Rollback Steps**
   - Go to Deployments
   - Click previous successful deployment
   - Click "Redeploy"

4. **Fix and Redeploy**
   ```bash
   # Fix issue locally
   git add .
   git commit -m "Fix: description"
   git push origin main
   ```

## Success Criteria

Deployment is successful when:

✅ All health checks pass
✅ Frontend loads without errors
✅ Users can register and login
✅ Transactions can be uploaded
✅ All CRUD operations work
✅ Dashboard displays correctly
✅ No critical errors in logs
✅ Performance is acceptable
✅ Security measures verified

## Final Verification

Before announcing launch:

- [ ] Test from different browsers (Chrome, Firefox, Safari)
- [ ] Test on mobile devices
- [ ] Test with sample data
- [ ] Verify all features work
- [ ] Check for broken links
- [ ] Review error handling
- [ ] Test edge cases
- [ ] Load test (optional)

## Communication

Once deployed:

- [ ] Announce to stakeholders
- [ ] Share URL with users
- [ ] Provide quick start guide
- [ ] Set up feedback channel
- [ ] Monitor initial usage

## Deployment Info

**Project**: Budget App - Personal Finance Manager
**Repository**: https://github.com/rsvidron/Svidnet-Budget
**Platform**: Railway
**Database**: PostgreSQL
**Deployment Date**: _____________
**Deployed By**: rsvidron
**Production URL**: _____________

---

## Quick Commands

```bash
# View deployment status
railway status

# View logs
railway logs

# Open project in browser
railway open

# Run database migrations (if needed)
railway run alembic upgrade head

# Check environment variables
railway variables
```

## Support Resources

- Railway Docs: https://docs.railway.app
- GitHub Issues: https://github.com/rsvidron/Svidnet-Budget/issues
- PostgreSQL Docs: https://www.postgresql.org/docs/
- FastAPI Docs: https://fastapi.tiangolo.com/

---

**Status**: Ready for Deployment ✅

Follow `RAILWAY_DEPLOYMENT.md` for step-by-step instructions.
