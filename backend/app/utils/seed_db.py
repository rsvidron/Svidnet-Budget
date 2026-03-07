"""
Database seeding utility - creates default admin user
"""
from sqlalchemy.orm import Session
from app.models import User
from app.core.security import get_password_hash
from app.services.categorization_service import CategorizationService
import logging

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_EMAIL = "svidron.robert@gmail.com"
DEFAULT_ADMIN_USERNAME = "robert"
DEFAULT_ADMIN_PASSWORD = "Plexpass"


def seed_default_user(db: Session) -> None:
    """
    Create default admin user if it doesn't exist
    """
    try:
        # Check if admin user already exists
        existing_user = db.query(User).filter(User.email == DEFAULT_ADMIN_EMAIL).first()

        if existing_user:
            logger.info(f"Default admin user already exists: {DEFAULT_ADMIN_EMAIL}")
            return

        # Create default admin user
        logger.info(f"Creating default admin user: {DEFAULT_ADMIN_EMAIL}")

        # Ensure password is within bcrypt's 72 byte limit
        password = DEFAULT_ADMIN_PASSWORD.encode('utf-8')[:72].decode('utf-8')

        admin_user = User(
            email=DEFAULT_ADMIN_EMAIL,
            username=DEFAULT_ADMIN_USERNAME,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_verified=True
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # Initialize default categories for the admin user
        categorization_service = CategorizationService(db)
        categorization_service.initialize_default_categories(admin_user.id)

        logger.info(f"✅ Default admin user created successfully!")
        logger.info(f"   Email: {DEFAULT_ADMIN_EMAIL}")
        logger.info(f"   Username: {DEFAULT_ADMIN_USERNAME}")
        logger.info(f"   Password: {DEFAULT_ADMIN_PASSWORD}")
        logger.info(f"   Categories: 12 default categories initialized")

    except Exception as e:
        logger.error(f"❌ Failed to create default admin user: {e}")
        db.rollback()
