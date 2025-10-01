from app.database import get_db, engine
from app.models import User, Base

def list_users():
    """List all users in database"""
    db = next(get_db())
    users = db.query(User).all()

    print("Users in database:")
    for user in users:
        print(f"- Email: {user.email}, Username: {user.username}, Department: {user.primary_department}")

    db.close()

if __name__ == "__main__":
    list_users()