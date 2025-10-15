
import asyncio
from sqlalchemy.future import select
from app.database import SessionLocal
from app.models import User
from app.auth import get_password_hash

async def reset_admin_password():
    """
    Connects to the database and resets the password for the default admin user.
    """
    async with SessionLocal() as session:
        async with session.begin():
            admin_email = "admin@pyramid-computer.de"
            new_password = "PyramidAdmin2024!"

            # Find the admin user
            result = await session.execute(
                select(User).where(User.email == admin_email)
            )
            admin_user = result.scalar_one_or_none()

            if admin_user:
                print(f"Found admin user: {admin_user.email}")
                # Hash the new password and update the user object
                hashed_password = get_password_hash(new_password)
                admin_user.hashed_password = hashed_password
                print(f"Successfully reset password for {admin_email}")
            else:
                print(f"Admin user {admin_email} not found.")

if __name__ == "__main__":
    print("Starting admin password reset...")
    asyncio.run(reset_admin_password())
