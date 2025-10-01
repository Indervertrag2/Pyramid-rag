#!/usr/bin/env python3
"""Drop and recreate all database tables"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from app.models import Base

def reset_database():
    """Drop all tables and recreate them"""
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database reset complete!")

if __name__ == "__main__":
    response = input("WARNING: This will delete ALL data! Continue? (yes/no): ")
    if response.lower() == "yes":
        reset_database()
    else:
        print("Database reset cancelled.")