from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.database import engine, Base, AsyncSessionLocal
# from app.core.config import settings
from app.auth import get_password_hash
from app.models import User, Department

logger = logging.getLogger(__name__)


async def initialize_database():
    """Initialize database with required extensions and tables."""
    try:
        async with engine.begin() as conn:
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
    """Create default admin user if not exists."""
    async with AsyncSessionLocal() as db:
        try:
            # Check if admin exists
            result = await db.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": settings.ADMIN_EMAIL}
            )
            existing_admin = result.scalar_one_or_none()

            if not existing_admin:
                # Create admin user
                admin = User(
                    email=settings.ADMIN_EMAIL,
                    username="admin",
                    hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                    full_name="System Administrator",
                    primary_department=settings.ADMIN_DEPARTMENT,
                    is_active=True,
                    is_superuser=True
                )
                db.add(admin)
                await db.commit()
                logger.info(f"Admin user created: {settings.ADMIN_EMAIL}")
            else:
                logger.info("Admin user already exists")
        except Exception as e:
            logger.error(f"Failed to create admin user: {str(e)}")
            await db.rollback()
            raise