from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import os

from app.database import async_engine, AsyncSessionLocal
from app.auth import get_password_hash
from app.models import User, Department, Base

logger = logging.getLogger(__name__)


async def initialize_database():
    """Initialize database with required extensions and tables."""
    try:
        async with async_engine.begin() as conn:
            # Create pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))  # For text search
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gin"))  # For combined indexes

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)

            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


async def create_admin_user():
    """Create or update default admin user on startup."""
    admin_email = os.getenv("ADMIN_EMAIL", "admin@pyramid-computer.de")
    admin_password = os.getenv("ADMIN_PASSWORD", "PyramidAdmin2024!")
    admin_department = os.getenv("ADMIN_DEPARTMENT", "Management")

    async with AsyncSessionLocal() as db:
        try:
            # Check if admin exists
            result = await db.execute(
                text("SELECT id, hashed_password FROM users WHERE email = :email"),
                {"email": admin_email}
            )
            existing_admin = result.first()

            new_password_hash = get_password_hash(admin_password)

            if not existing_admin:
                # Create admin user
                admin = User(
                    email=admin_email,
                    username="admin",
                    hashed_password=new_password_hash,
                    full_name="System Administrator",
                    primary_department=admin_department,
                    is_active=True,
                    is_superuser=True
                )
                db.add(admin)
                await db.commit()
                logger.info(f"Admin user created: {admin_email}")
            else:
                # Update admin password on every startup to ensure it matches .env
                await db.execute(
                    text("UPDATE users SET hashed_password = :password WHERE email = :email"),
                    {"password": new_password_hash, "email": admin_email}
                )
                await db.commit()
                logger.info(f"Admin user password synchronized with environment configuration")
        except Exception as e:
            logger.error(f"Failed to create/update admin user: {str(e)}")
            await db.rollback()
            raise