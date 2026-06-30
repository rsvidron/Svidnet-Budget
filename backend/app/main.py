from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os
import logging
from sqlalchemy import inspect, text
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api import auth, transactions, categories, budgets, savings_goals, analytics, debug, accounts
from app.utils.seed_db import seed_default_user
from app.utils.migrations import ensure_account_id_column, ensure_normalized_merchant_column, backfill_default_accounts, backfill_normalized_merchant

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
try:
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {e}")
    # Don't fail startup, just log the error

# Idempotent migrations for columns not handled by create_all (existing tables).
try:
    ensure_account_id_column(engine)
except Exception as e:
    logger.error(f"Migration ensure_account_id_column failed: {e}")

try:
    ensure_normalized_merchant_column(engine)
except Exception as e:
    logger.error(f"Migration ensure_normalized_merchant_column failed: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database URL: {settings.DATABASE_URL[:20]}...")
    logger.info(f"Port: {settings.PORT}")

    # Seed default user, then backfill accounts for any user missing them.
    db = SessionLocal()
    try:
        seed_default_user(db)
        backfilled = backfill_default_accounts(db)
        if backfilled:
            logger.info(f"Backfilled default accounts for {backfilled} user(s).")
        backfill_normalized_merchant(db)
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(transactions.router, prefix=f"{settings.API_V1_STR}/transactions", tags=["transactions"])
app.include_router(categories.router, prefix=f"{settings.API_V1_STR}/categories", tags=["categories"])
app.include_router(budgets.router, prefix=f"{settings.API_V1_STR}/budgets", tags=["budgets"])
app.include_router(savings_goals.router, prefix=f"{settings.API_V1_STR}/savings-goals", tags=["savings-goals"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/analytics", tags=["analytics"])
app.include_router(debug.router, prefix=f"{settings.API_V1_STR}/debug", tags=["debug"])
app.include_router(accounts.router, prefix=f"{settings.API_V1_STR}/accounts", tags=["accounts"])


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Serve static files (built frontend) in production
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # If path is API route, skip
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi"):
            return {"error": "Not found"}

        # Serve index.html for all other routes (SPA)
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "Frontend not built"}
else:
    @app.get("/")
    def root():
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "version": settings.VERSION,
            "docs": "/docs",
            "note": "Frontend is served separately in development"
        }
