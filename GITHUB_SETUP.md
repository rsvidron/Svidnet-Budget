# GitHub Setup Instructions

## Push to GitHub Repository

The code is ready to push to: **https://github.com/rsvidron/Svidnet-Budget.git**

### Option 1: Using GitHub CLI (Recommended)

If you have GitHub CLI installed:

```bash
# Login to GitHub
gh auth login

# Push to repository
git push -u origin main
```

### Option 2: Using Personal Access Token

1. **Generate a Personal Access Token**
   - Go to https://github.com/settings/tokens
   - Click "Generate new token" → "Generate new token (classic)"
   - Give it a name: "Budget App Deploy"
   - Select scopes: `repo` (all sub-scopes)
   - Click "Generate token"
   - **Copy the token immediately** (you won't see it again)

2. **Push with Token**
   ```bash
   # Use token as password
   git push -u origin main

   # When prompted:
   # Username: rsvidron
   # Password: <paste-your-token-here>
   ```

3. **Save Credentials (Optional)**
   ```bash
   # Cache credentials for 1 hour
   git config --global credential.helper 'cache --timeout=3600'

   # Or store permanently (less secure)
   git config --global credential.helper store
   ```

### Option 3: Using SSH Key

1. **Generate SSH Key** (if you don't have one)
   ```bash
   ssh-keygen -t ed25519 -C "rsvidron@gmail.com"
   ```

2. **Add to SSH Agent**
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   ```

3. **Copy Public Key**
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

4. **Add to GitHub**
   - Go to https://github.com/settings/keys
   - Click "New SSH key"
   - Paste your public key
   - Click "Add SSH key"

5. **Change Remote URL to SSH**
   ```bash
   git remote set-url origin git@github.com:rsvidron/Svidnet-Budget.git
   ```

6. **Push**
   ```bash
   git push -u origin main
   ```

### Option 4: Using GitHub Desktop

1. Download GitHub Desktop from https://desktop.github.com
2. Sign in with your GitHub account
3. File → Add Local Repository
4. Select the `budget-app` folder
5. Click "Publish repository"
6. Choose "rsvidron/Svidnet-Budget" as the repository name
7. Click "Publish Repository"

## Verify Push

After pushing, visit:
https://github.com/rsvidron/Svidnet-Budget

You should see all your files including:
- Backend code (Python/FastAPI)
- Frontend code (React)
- Documentation (README, QUICKSTART, etc.)
- Deployment configs (railway.json, Dockerfile, etc.)

## Next Steps

Once pushed to GitHub:

1. **Deploy to Railway** - Follow `RAILWAY_DEPLOYMENT.md`
2. **Set up GitHub Actions** (optional) - For automated testing
3. **Add README badges** - Build status, version, etc.
4. **Configure branch protection** - Protect main branch

## Troubleshooting

### "Permission denied"
- Check your token has `repo` scope
- Verify token hasn't expired
- Try SSH authentication instead

### "Repository not found"
- Verify repository exists: https://github.com/rsvidron/Svidnet-Budget
- Check you have write access
- Ensure remote URL is correct: `git remote -v`

### "Authentication failed"
- Token might be incorrect
- Try creating a new token
- Use SSH method instead

### "Updates were rejected"
```bash
# If repository already has commits, force push (be careful!)
git push -u origin main --force
```

## Current Status

✅ Repository initialized
✅ All files committed
✅ Remote added: https://github.com/rsvidron/Svidnet-Budget.git
⏳ Pending: Push to GitHub (requires authentication)

## Quick Push Command

```bash
# After setting up authentication (choose one method above)
cd /home/user/workspaces/69989b54b0e5d06a8f842722/f439d12d-19bf-447a-8dc9-082a9e8a6638/budget-app
git push -u origin main
```

That's it! Once pushed, you can deploy to Railway.
