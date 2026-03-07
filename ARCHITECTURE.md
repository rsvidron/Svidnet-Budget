# Budget App - Architecture Documentation

## Overview

This document describes the architecture and design decisions for the Budget App, a full-stack personal finance management application.

## System Architecture

The application follows a modern three-tier architecture:

1. **Presentation Layer** (Frontend)
   - React-based SPA
   - Responsive UI with Tailwind CSS
   - Client-side routing with React Router
   - State management with Zustand

2. **Application Layer** (Backend API)
   - RESTful API built with FastAPI
   - JWT-based authentication
   - Business logic in service layer
   - Input validation with Pydantic

3. **Data Layer** (Database)
   - SQLAlchemy ORM
   - SQLite for development
   - PostgreSQL recommended for production
   - Normalized relational schema

## Backend Architecture

### Layered Design

```
┌─────────────────────────────────────┐
│         API Routes Layer            │
│  (auth, transactions, categories,   │
│   budgets, goals, analytics)        │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│        Service Layer                │
│  (Business logic, categorization,   │
│   analytics, recurring detection)   │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│         Models Layer                │
│  (SQLAlchemy ORM models)            │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│         Database                    │
│  (SQLite / PostgreSQL)              │
└─────────────────────────────────────┘
```

### Key Components

#### 1. API Routes (`app/api/`)
- **auth.py**: User registration, login, 2FA setup
- **transactions.py**: CRUD operations, upload, export
- **categories.py**: Category management, merging, rules
- **budgets.py**: Budget CRUD operations
- **savings_goals.py**: Goals management and contributions
- **analytics.py**: Dashboard data, trends, insights

#### 2. Services (`app/services/`)
- **CategorizationService**: Automatic transaction categorization
  - Rule-based matching with keywords
  - Learning from past categorizations
  - Priority-based rule application

- **AnalyticsService**: Financial insights and reporting
  - Spending by category aggregation
  - Monthly trend analysis
  - Budget progress tracking
  - Recurring transaction detection

#### 3. Parsers (`app/parsers/`)
- **BaseParser**: Abstract interface for bank parsers
- **PNCParser**: PNC-specific CSV and PDF parsing
- Extensible design for additional banks

#### 4. Models (`app/models/`)
- **User**: Authentication and profile data
- **Transaction**: Financial transactions
- **Category**: Expense/income categories
- **Budget**: Monthly/periodic budgets
- **SavingsGoal**: Savings targets
- **CategorizationRule**: Auto-categorization rules

#### 5. Core (`app/core/`)
- **config.py**: Application configuration
- **database.py**: Database connection and session management
- **security.py**: Authentication, password hashing, JWT, TOTP

## Frontend Architecture

### Component Hierarchy

```
App
├── Router
│   ├── Public Routes
│   │   ├── Login
│   │   └── Register
│   └── Private Routes
│       └── Layout
│           ├── Dashboard
│           ├── Transactions
│           ├── Budgets
│           ├── SavingsGoals
│           └── Categories
```

### State Management

- **Zustand** for global state (authentication)
- Local React state for component-specific data
- No prop drilling - direct state access

### API Communication

- **Axios** HTTP client with interceptors
- Automatic JWT token injection
- Centralized error handling
- Token refresh on 401 responses

### Styling Strategy

- **Tailwind CSS** utility-first approach
- Custom component classes in `index.css`
- Consistent color palette
- Mobile-first responsive design

## Data Flow

### Transaction Upload Flow

```
1. User uploads CSV/PDF file
   ↓
2. File sent to /transactions/upload endpoint
   ↓
3. PNCParser extracts transactions
   ↓
4. CategorizationService categorizes each transaction
   ↓
5. Transactions saved to database
   ↓
6. Response sent to frontend
   ↓
7. UI refreshes transaction list
```

### Automatic Categorization Flow

```
1. New transaction received
   ↓
2. CategorizationService.categorize_transaction()
   ↓
3. Check user-defined rules (by priority)
   ↓
4. If matched → return category_id
   ↓
5. If not matched → check past transactions for same merchant
   ↓
6. If found → return category_id
   ↓
7. If not found → assign "Uncategorized"
```

### Analytics Dashboard Flow

```
1. User navigates to Dashboard
   ↓
2. Frontend calls /analytics/dashboard
   ↓
3. AnalyticsService aggregates data:
   - Spending by category (current month)
   - Monthly trends (6 months)
   - Budget progress (current month)
   - Top merchants (current month)
   ↓
4. Data returned as JSON
   ↓
5. React components render charts
```

## Security Architecture

### Authentication Flow

```
1. User submits credentials
   ↓
2. Backend verifies password hash
   ↓
3. If 2FA enabled → verify TOTP token
   ↓
4. Generate JWT token (expires in 30 min)
   ↓
5. Return token to frontend
   ↓
6. Frontend stores in localStorage
   ↓
7. Token sent in Authorization header for subsequent requests
```

### Security Measures

1. **Password Security**
   - bcrypt hashing with salt
   - Minimum 8 characters enforced

2. **JWT Tokens**
   - HS256 signing algorithm
   - 30-minute expiration
   - User ID in payload

3. **2FA (Optional)**
   - TOTP-based (RFC 6238)
   - Compatible with Google Authenticator
   - QR code provisioning

4. **API Security**
   - CORS protection
   - Input validation (Pydantic)
   - SQL injection prevention (ORM)
   - Authenticated endpoints only

## Database Design

### Entity Relationship Diagram

```
┌─────────┐
│  User   │
└────┬────┘
     │
     ├──────┬──────────┬───────────┬────────────┐
     │      │          │           │            │
┌────▼─────┐ ┌────▼────┐ ┌────▼────┐ ┌────▼────┐ ┌────▼────────────┐
│Transaction│ │Category │ │ Budget  │ │ Goal    │ │Categorization   │
│          │ │         │ │         │ │         │ │Rule             │
└──────────┘ └────┬────┘ └─────────┘ └─────────┘ └─────────────────┘
     │            │
     └────────────┘
     (Many-to-One)
```

### Indexing Strategy

- Primary keys on all tables
- Indexes on foreign keys
- Index on user_id for all user-scoped tables
- Index on transaction date for range queries
- Unique constraints on email and username

### Data Integrity

- Foreign key constraints
- Cascade delete on user deletion
- NOT NULL constraints on required fields
- Enum types for transaction_type
- Check constraints on amounts (positive values)

## Scalability Considerations

### Current Limitations

- SQLite not suitable for high concurrency
- Single-server deployment
- No caching layer
- Synchronous processing

### Future Improvements

1. **Database**
   - Migrate to PostgreSQL
   - Connection pooling
   - Read replicas for analytics

2. **Caching**
   - Redis for session storage
   - Cache frequently accessed data
   - Cache invalidation strategy

3. **Async Processing**
   - Celery for background tasks
   - Async file upload processing
   - Scheduled analytics calculation

4. **API Performance**
   - Pagination for large datasets
   - GraphQL for flexible queries
   - Response compression

5. **Deployment**
   - Docker containers
   - Kubernetes orchestration
   - Load balancing
   - CDN for frontend assets

## Extensibility

### Adding a New Bank Parser

1. Create class inheriting from `BankStatementParser`
2. Implement `parse_csv()` and `parse_pdf()` methods
3. Return standardized transaction format
4. Register parser in upload endpoint

### Adding a New Analytics Report

1. Add method to `AnalyticsService`
2. Create API endpoint in `analytics.py`
3. Create frontend component
4. Add to dashboard or new page

### Adding Machine Learning Categorization

1. Create `MLCategorizationService`
2. Train model on historical transactions
3. Integrate with existing `CategorizationService`
4. Fall back to rule-based if confidence low

## Testing Strategy

### Backend Tests (Recommended)

- Unit tests for services
- Integration tests for API endpoints
- Mock database for fast tests
- Test authentication flows
- Test transaction parsing

### Frontend Tests (Recommended)

- Component tests with React Testing Library
- Integration tests for user flows
- Mock API responses
- Test error handling
- Test responsive layouts

## Performance Optimization

### Backend

- Database query optimization
- Eager loading relationships
- Limit/offset pagination
- Response caching headers

### Frontend

- Code splitting by route
- Lazy loading components
- Memoization for expensive calculations
- Debounced search inputs
- Optimistic UI updates

## Monitoring & Observability

### Recommended Tools

- **Logging**: Structured JSON logs
- **Metrics**: Prometheus
- **Tracing**: OpenTelemetry
- **Error Tracking**: Sentry
- **Uptime Monitoring**: Pingdom

### Key Metrics

- API response times
- Database query performance
- Authentication success/failure rates
- Transaction upload success rates
- Active user count

## Deployment Architecture

### Development
```
Frontend (Vite dev server :3000)
    ↓
Backend (uvicorn :8000)
    ↓
SQLite database
```

### Production (Recommended)
```
CloudFlare CDN
    ↓
Nginx (reverse proxy)
    ↓
┌─────────────────────┐
│ Frontend (static)   │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ Backend (uvicorn)   │
│ (multiple workers)  │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ PostgreSQL          │
└─────────────────────┘
```

## Conclusion

This architecture provides a solid foundation for a personal finance application with room for growth and enhancement. The separation of concerns, use of modern frameworks, and extensible design patterns make it maintainable and scalable.
