from app.database import get_db, engine
from app.models import User, Base, Department
from app.auth import get_password_hash

def create_admin_user():
    """Create admin user for testing"""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = next(get_db())

    # Check if admin exists
    existing = db.query(User).filter(User.email == "admin@pyramid.de").first()

    if not existing:
        admin_user = User(
            email="admin@pyramid.de",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            full_name="Admin User",
            primary_department=Department.ENTWICKLUNG,
            is_active=True,
            is_superuser=True
        )

        db.add(admin_user)
        db.commit()
        print("Admin user created successfully!")
        print("Email: admin@pyramid.de")
        print("Password: admin123")
    else:
        print("Admin user already exists")

    db.close()

if __name__ == "__main__":
    create_admin_user()