"""
Lightweight idempotent migrations that run on app startup.
We do not use Alembic — these helpers detect missing columns / data and patch in place.
Safe to run repeatedly on SQLite (dev) and PostgreSQL (Railway).
"""
import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import User, Transaction, Account
from app.models.account import AccountType

logger = logging.getLogger(__name__)


def ensure_account_id_column(engine: Engine) -> None:
    """Add transactions.account_id if missing on an existing transactions table.

    Base.metadata.create_all does NOT add new columns to tables that already exist,
    so we patch the schema here.
    """
    inspector = inspect(engine)
    if "transactions" not in inspector.get_table_names():
        return  # create_all will build it fresh with the column already.

    cols = {c["name"] for c in inspector.get_columns("transactions")}
    if "account_id" in cols:
        return

    dialect = engine.dialect.name
    if dialect == "sqlite":
        ddl = "ALTER TABLE transactions ADD COLUMN account_id INTEGER REFERENCES accounts(id)"
        idx = "CREATE INDEX IF NOT EXISTS ix_transactions_account_id ON transactions(account_id)"
    else:
        # PostgreSQL / generic SQL
        ddl = "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES accounts(id)"
        idx = "CREATE INDEX IF NOT EXISTS ix_transactions_account_id ON transactions(account_id)"

    logger.info("Migration: adding transactions.account_id column")
    with engine.begin() as conn:
        conn.execute(text(ddl))
        try:
            conn.execute(text(idx))
        except Exception as e:
            logger.warning(f"Could not create ix_transactions_account_id index: {e}")


def backfill_default_accounts(db: Session) -> int:
    """For each user that has transactions but no account, create a 'Default' account
    and assign all their account-less transactions to it. Returns the count of users
    that were patched."""
    patched = 0
    user_ids = [
        uid
        for (uid,) in db.query(Transaction.user_id)
        .filter(Transaction.account_id.is_(None))
        .distinct()
        .all()
    ]
    for uid in user_ids:
        if not db.query(User).filter(User.id == uid).first():
            continue
        # Make sure the user has at least one account; create "Default" if missing.
        default = (
            db.query(Account)
            .filter(Account.user_id == uid, Account.is_default == True)
            .first()
        )
        if default is None:
            default = Account(
                user_id=uid,
                name="Default",
                account_type=AccountType.OTHER,
                is_default=True,
            )
            db.add(default)
            db.flush()

        affected = (
            db.query(Transaction)
            .filter(Transaction.user_id == uid, Transaction.account_id.is_(None))
            .update({"account_id": default.id}, synchronize_session=False)
        )
        if affected:
            patched += 1
            logger.info(f"Backfilled {affected} transactions for user_id={uid} to account '{default.name}'")
    db.commit()
    return patched
