#!/usr/bin/env python3
"""Reset admin password"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pyramid-rag', 'backend'))

from app.database import SessionLocal
from app.models import User
from app.auth import get_password_hash

# Reset admin password
db = SessionLocal()
try:
    admin = db.query(User).filter(User.email == 'admin@pyramid-computer.de').first()
    if admin:
        # Set password to "admin123"
        admin.hashed_password = get_password_hash("admin123")
        db.commit()
        print("✓ Admin password reset to: admin123")
        print("✓ Email: admin@pyramid-computer.de")
    else:
        print("✗ Admin user not found!")
finally:
    db.close()
