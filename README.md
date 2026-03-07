# Budget App - Personal Finance Manager

A modern, full-stack personal budgeting application with automatic transaction categorization, budget tracking, and comprehensive analytics.

## Features

### Core Features
- **User Authentication**: Secure JWT-based authentication with optional 2FA (TOTP)
- **Bank Statement Upload**: Import PNC bank statements (CSV and PDF formats)
- **Automatic Categorization**: Smart rule-based transaction categorization
- **Budget Management**: Set and track monthly budgets per category
- **Savings Goals**: Create and monitor progress toward savings goals
- **Analytics Dashboard**: Visual insights with charts and graphs

### Advanced Features
- **Recurring Transaction Detection**: Automatically identify recurring payments
- **Transaction Export**: Export transactions to CSV
- **Category Management**: Create, edit, merge, and delete categories
- **Transaction Filtering**: Search and filter by merchant, category, date
- **Budget Progress Tracking**: Real-time budget vs. actual spending
- **Mobile-Responsive UI**: Works seamlessly on desktop and mobile

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (development) / PostgreSQL (production)
- **ORM**: SQLAlchemy
- **Authentication**: JWT with python-jose
- **Password Hashing**: bcrypt via passlib
- **2FA**: TOTP via pyotp
- **PDF Parsing**: PyPDF2
- **API Documentation**: Auto-generated Swagger UI

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Routing**: React Router v6
- **State Management**: Zustand
- **Styling**: Tailwind CSS
- **Icons**: Heroicons
- **Charts**: Recharts
- **HTTP Client**: Axios
- **Date Utilities**: date-fns

## Project Structure

```
budget-app/
├── backend/
│   ├── app/
│   │   ├── api/              # API route handlers
│   │   │   ├── auth.py
│   │   │   ├── transactions.py
│   │   │   ├── categories.py
│   │   │   ├── budgets.py
│   │   │   ├── savings_goals.py
│   │   │   ├── analytics.py
│   │   │   └── deps.py       # Dependencies (auth)
│   │   ├── core/             # Core configuration
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/           # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── transaction.py
│   │   │   ├── category.py
│   │   │   ├── budget.py
│   │   │   ├── savings_goal.py
│   │   │   └── categorization_rule.py
│   │   ├── schemas/          # Pydantic schemas
│   │   │   ├── user.py
│   │   │   ├── transaction.py
│   │   │   ├── category.py
│   │   │   ├── budget.py
│   │   │   └── savings_goal.py
│   │   ├── services/         # Business logic
│   │   │   ├── categorization_service.py
│   │   │   └── analytics_service.py
│   │   ├── parsers/          # Bank statement parsers
│   │   │   ├── base_parser.py
│   │   │   └── pnc_parser.py
│   │   └── main.py           # FastAPI app entry point
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── src/
    │   ├── components/       # Reusable components
    │   │   └── Layout.jsx
    │   ├── pages/            # Page components
    │   │   ├── Login.jsx
    │   │   ├── Register.jsx
    │   │   ├── Dashboard.jsx
    │   │   ├── Transactions.jsx
    │   │   ├── Budgets.jsx
    │   │   ├── SavingsGoals.jsx
    │   │   └── Categories.jsx
    │   ├── services/         # API services
    │   │   └── api.js
    │   ├── store/            # State management
    │   │   └── authStore.js
    │   ├── App.jsx           # Main app component
    │   ├── main.jsx          # Entry point
    │   └── index.css         # Global styles
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── index.html
```

## Installation & Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd budget-app/backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create environment file:
```bash
cp .env.example .env
```

5. Edit `.env` and update the `SECRET_KEY`:
```bash
# Generate a secure secret key
openssl rand -hex 32
```

6. Run the backend:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd budget-app/frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file (optional):
```bash
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env
```

4. Run the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Usage Guide

### 1. Create an Account
1. Navigate to `http://localhost:3000`
2. Click "Create a new account"
3. Enter email, username, and password
4. Click "Create account"

### 2. Login
1. Enter your email and password
2. If 2FA is enabled, enter your 6-digit TOTP code
3. Click "Sign in"

### 3. Upload Bank Statement
1. Go to "Transactions" page
2. Click "Upload Statement"
3. Select your PNC bank statement (CSV or PDF)
4. Transactions will be automatically imported and categorized

### 4. Manage Categories
1. Go to "Categories" page
2. Create custom categories with colors
3. Use "Recategorize All" to apply new rules

### 5. Set Budgets
1. Go to "Budgets" page
2. Click "New Budget"
3. Select category, amount, and period
4. Track progress on the Dashboard

### 6. Create Savings Goals
1. Go to "Savings Goals" page
2. Click "New Goal"
3. Set target amount and date
4. Contribute to goals regularly

### 7. View Analytics
- Dashboard shows spending by category, trends, and budget progress
- Monthly trends chart shows income vs. expenses
- Top merchants list shows where you spend most

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/totp/setup` - Setup 2FA
- `POST /api/v1/auth/totp/verify` - Verify 2FA token

### Transactions
- `GET /api/v1/transactions/` - List transactions (with filters)
- `POST /api/v1/transactions/` - Create transaction
- `PUT /api/v1/transactions/{id}` - Update transaction
- `DELETE /api/v1/transactions/{id}` - Delete transaction
- `POST /api/v1/transactions/upload` - Upload bank statement
- `POST /api/v1/transactions/export` - Export to CSV

### Categories
- `GET /api/v1/categories/` - List categories
- `POST /api/v1/categories/` - Create category
- `PUT /api/v1/categories/{id}` - Update category
- `DELETE /api/v1/categories/{id}` - Delete category
- `POST /api/v1/categories/{id}/merge/{target_id}` - Merge categories
- `POST /api/v1/categories/recategorize` - Recategorize all transactions

### Budgets
- `GET /api/v1/budgets/` - List budgets
- `POST /api/v1/budgets/` - Create budget
- `PUT /api/v1/budgets/{id}` - Update budget
- `DELETE /api/v1/budgets/{id}` - Delete budget

### Savings Goals
- `GET /api/v1/savings-goals/` - List goals
- `POST /api/v1/savings-goals/` - Create goal
- `PUT /api/v1/savings-goals/{id}` - Update goal
- `DELETE /api/v1/savings-goals/{id}` - Delete goal
- `POST /api/v1/savings-goals/{id}/contribute` - Contribute to goal

### Analytics
- `GET /api/v1/analytics/dashboard` - Get dashboard summary
- `GET /api/v1/analytics/spending-by-category` - Category spending
- `GET /api/v1/analytics/monthly-trends` - Monthly trends
- `GET /api/v1/analytics/budget-progress` - Budget progress
- `GET /api/v1/analytics/top-merchants` - Top merchants
- `GET /api/v1/analytics/recurring-transactions` - Recurring detection

## Database Schema

### Users
- id, email, username, hashed_password
- is_active, is_verified, totp_secret
- created_at, updated_at

### Transactions
- id, user_id, category_id
- date, merchant, description, amount
- transaction_type (debit/credit/transfer)
- is_recurring, recurring_pattern
- is_manually_categorized, source_file

### Categories
- id, user_id, name, color, icon
- parent_id (for subcategories)

### Budgets
- id, user_id, category_id
- amount, period (monthly/quarterly/yearly)
- start_date, end_date

### Savings Goals
- id, user_id, name, description
- target_amount, current_amount
- target_date, is_completed

### Categorization Rules
- id, user_id, category_id
- keyword, priority

## Adding Support for Additional Banks

To add support for a new bank's statement format:

1. Create a new parser in `backend/app/parsers/`:

```python
from .base_parser import BankStatementParser

class NewBankParser(BankStatementParser):
    def parse_csv(self, file_path: str):
        # Implement CSV parsing logic
        pass

    def parse_pdf(self, file_path: str):
        # Implement PDF parsing logic
        pass
```

2. Update the upload endpoint in `backend/app/api/transactions.py` to use the new parser

## Production Deployment

### Backend
1. Update `DATABASE_URL` to use PostgreSQL
2. Set secure `SECRET_KEY`
3. Use production ASGI server (uvicorn with workers)
4. Enable HTTPS
5. Set up proper CORS origins

### Frontend
1. Build production bundle: `npm run build`
2. Serve `dist/` folder with nginx or similar
3. Update `VITE_API_URL` to production API URL

## Security Considerations
- All passwords are hashed using bcrypt
- JWT tokens expire after 30 minutes (configurable)
- 2FA support via TOTP (Google Authenticator compatible)
- SQL injection protection via SQLAlchemy ORM
- CORS protection configured
- Input validation on all endpoints

## Future Enhancements
- Machine learning-based categorization
- Multi-currency support
- Shared budgets for families
- Mobile app (React Native)
- Email notifications for budget alerts
- Integration with Plaid for automatic bank syncing
- Receipt scanning and OCR
- Bill reminders
- Investment tracking

## License
MIT License

## Support
For issues and questions, please open a GitHub issue.
