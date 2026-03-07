"""
Debug endpoints for system diagnostics and logging
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime
import logging
import os
from app.core.database import get_db
from app.models import User, Category, Transaction, Budget, SavingsGoal
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION
    }


@router.get("/info")
async def system_info() -> Dict[str, Any]:
    """
    Get system information and configuration (non-sensitive)
    """
    return {
        "app": {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
        },
        "database": {
            "url_prefix": settings.DATABASE_URL[:20] + "...",
            "type": "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite"
        },
        "server": {
            "port": settings.PORT,
            "cors_origins_count": len([o for o in settings.CORS_ORIGINS if o]),
        },
        "python_version": os.sys.version,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/db-stats")
async def database_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get database statistics
    """
    try:
        stats = {
            "users": db.query(User).count(),
            "categories": db.query(Category).count(),
            "transactions": db.query(Transaction).count(),
            "budgets": db.query(Budget).count(),
            "savings_goals": db.query(SavingsGoal).count(),
        }

        # Get sample user info (non-sensitive)
        users = db.query(User).limit(5).all()
        user_list = [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ]

        return {
            "counts": stats,
            "sample_users": user_list,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/logs/recent")
async def recent_logs() -> Dict[str, Any]:
    """
    Get recent application logs
    Note: This returns in-memory log records from the current process
    """
    # Get the root logger
    root_logger = logging.getLogger()

    # Try to get handlers
    handlers_info = []
    for handler in root_logger.handlers:
        handlers_info.append({
            "type": type(handler).__name__,
            "level": logging.getLevelName(handler.level),
            "formatter": str(handler.formatter) if handler.formatter else None
        })

    return {
        "logging_config": {
            "root_level": logging.getLevelName(root_logger.level),
            "handlers": handlers_info,
        },
        "note": "For detailed logs, check Railway deployment logs or container stdout",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/test-auth")
async def test_auth_setup(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Test authentication setup - verify default user exists
    """
    try:
        from app.utils.seed_db import DEFAULT_ADMIN_EMAIL

        user = db.query(User).filter(User.email == DEFAULT_ADMIN_EMAIL).first()

        if user:
            return {
                "status": "success",
                "message": "Default admin user exists",
                "user": {
                    "email": user.email,
                    "username": user.username,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "has_password": bool(user.hashed_password),
                    "password_hash_prefix": user.hashed_password[:10] + "..." if user.hashed_password else None
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": f"Default admin user not found: {DEFAULT_ADMIN_EMAIL}",
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Error testing auth setup: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/env-check")
async def environment_check() -> Dict[str, Any]:
    """
    Check environment variables (non-sensitive values only)
    """
    secret_key_env = os.getenv("SECRET_KEY", "")
    secret_key_settings = settings.SECRET_KEY

    env_vars = {
        "PORT": os.getenv("PORT", "not set"),
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "not set"),
        "DATABASE_URL": "set" if os.getenv("DATABASE_URL") else "not set",
        "SECRET_KEY": "set" if os.getenv("SECRET_KEY") else "not set",
        "SECRET_KEY_LENGTH_ENV": len(secret_key_env),
        "SECRET_KEY_LENGTH_SETTINGS": len(secret_key_settings),
        "SECRET_KEY_PREFIX_ENV": secret_key_env[:10] + "..." if secret_key_env else "not set",
        "SECRET_KEY_PREFIX_SETTINGS": secret_key_settings[:10] + "..." if secret_key_settings else "not set",
        "KEYS_MATCH": secret_key_env == secret_key_settings if secret_key_env and secret_key_settings else False,
        "FRONTEND_URL": os.getenv("FRONTEND_URL", "not set"),
        "RAILWAY_PUBLIC_DOMAIN": os.getenv("RAILWAY_PUBLIC_DOMAIN", "not set"),
    }

    return {
        "environment_variables": env_vars,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/test-token")
async def test_token_decode(token: str) -> Dict[str, Any]:
    """
    Test JWT token decoding for debugging
    """
    from app.core.security import decode_access_token, create_access_token
    from jose import jwt

    try:
        # Try to decode
        payload = decode_access_token(token)

        # Also create a test token to compare
        test_token = create_access_token({"sub": 999, "test": True})
        test_payload = decode_access_token(test_token)

        return {
            "status": "success",
            "input_token_payload": payload,
            "test_token": test_token,
            "test_token_payload": test_payload,
            "secret_key_prefix": settings.SECRET_KEY[:10] + "..." if settings.SECRET_KEY else None,
            "secret_key_length": len(settings.SECRET_KEY) if settings.SECRET_KEY else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "secret_key_prefix": settings.SECRET_KEY[:10] + "..." if settings.SECRET_KEY else None,
            "timestamp": datetime.utcnow().isoformat()
        }
