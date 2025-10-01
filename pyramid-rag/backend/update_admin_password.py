from app.database import get_db
from app.models import User
from app.auth import get_password_hash

def update_admin_password():
    """Update admin password"""
    db = next(get_db())

    # Find admin user
    admin = db.query(User).filter(User.email == "admin@pyramid-computer.de").first()

    if admin:
        admin.hashed_password = get_password_hash("admin123")
        db.commit()
        print("Admin password updated successfully!")
        print("Email: admin@pyramid-computer.de")
        print("Password: admin123")
    else:
        print("Admin user not found")

    db.close()

if __name__ == "__main__":
    update_admin_password()