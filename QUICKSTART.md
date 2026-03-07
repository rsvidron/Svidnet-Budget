# Quick Start Guide

Get the Budget App running in 5 minutes!

## Prerequisites

Make sure you have:
- Python 3.9+ installed
- Node.js 18+ installed
- npm or yarn installed

## Step 1: Backend Setup (2 minutes)

Open a terminal and navigate to the backend folder:

```bash
cd budget-app/backend
```

### Option A: Using the run script (Linux/Mac)
```bash
./run.sh
```

### Option B: Manual setup (All platforms)
```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will start at `http://localhost:8000`

✅ Visit `http://localhost:8000/docs` to see the API documentation

## Step 2: Frontend Setup (2 minutes)

Open a **new terminal** and navigate to the frontend folder:

```bash
cd budget-app/frontend
```

Install dependencies and start the dev server:

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

The frontend will start at `http://localhost:3000`

✅ Open `http://localhost:3000` in your browser

## Step 3: Create Your Account (1 minute)

1. Click **"Create a new account"**
2. Enter:
   - Email: `demo@example.com`
   - Username: `demo`
   - Password: `password123`
3. Click **"Create account"**
4. Login with your new credentials

## Step 4: Import Sample Data

1. Go to the **Transactions** page
2. Click **"Upload Statement"**
3. Select `backend/sample_pnc_statement.csv`
4. Watch your transactions get imported and automatically categorized!

## What's Next?

### Explore Features

1. **Dashboard**: See your spending visualized
2. **Budgets**: Create a budget for groceries or dining
3. **Savings Goals**: Set a goal like "Emergency Fund"
4. **Categories**: Customize your categories and colors

### Try Advanced Features

- **2FA**: Go to Settings (via API) to enable two-factor authentication
- **Export**: Export your transactions to CSV
- **Manual Transactions**: Add transactions manually
- **Category Rules**: Teach the app how to categorize

## Troubleshooting

### Backend won't start?
- Make sure Python 3.9+ is installed: `python --version`
- Check if port 8000 is already in use
- Verify all dependencies installed: `pip list`

### Frontend won't start?
- Make sure Node.js 18+ is installed: `node --version`
- Delete `node_modules` and run `npm install` again
- Check if port 3000 is already in use

### Can't login?
- Make sure the backend is running on port 8000
- Check browser console for errors (F12)
- Verify you created an account first

### Transactions not importing?
- Check the CSV file format matches the sample
- Look for error messages in the backend console
- Verify the file size is under 10MB

## Development Tips

### Hot Reload
Both frontend and backend support hot reload:
- Backend: Edit Python files, server restarts automatically
- Frontend: Edit React files, browser refreshes automatically

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Database
- SQLite database is created automatically at `backend/budget_app.db`
- Use SQLite browser to inspect: https://sqlitebrowser.org/

### Environment Variables

**Backend** (`.env`):
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./budget_app.db
```

**Frontend** (`.env`):
```
VITE_API_URL=http://localhost:8000/api/v1
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system design
- Start customizing for your needs!

## Need Help?

- Backend API not working? Check the terminal for error messages
- Frontend errors? Open browser DevTools (F12) and check Console
- Database issues? Delete `budget_app.db` and restart to start fresh

Enjoy tracking your finances! 💰
