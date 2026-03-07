from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Handle PostgreSQL URL format from Railway (starts with postgres://)
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Configure engine with appropriate settings for SQLite or PostgreSQL
engine_config = {}
if "sqlite" in database_url:
    engine_config["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL settings for production
    engine_config["pool_pre_ping"] = True
    engine_config["pool_size"] = 10
    engine_config["max_overflow"] = 20

engine = create_engine(database_url, **engine_config)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
