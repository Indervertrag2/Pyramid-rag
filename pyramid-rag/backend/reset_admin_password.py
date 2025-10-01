#!/usr/bin/env python3
"""Reset admin password with proper bcrypt hash"""

import bcrypt
import psycopg2
import sys

# Database connection
conn_params = {
    'host': 'localhost',
    'port': 15432,
    'database': 'pyramid_rag',
    'user': 'pyramid_user',
    'password': 'pyramid_pass'
}

def reset_admin_password():
    """Reset the admin password to 'admin123'"""
    # Generate proper bcrypt hash
    password = b'admin123'
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password, salt).decode('utf-8')

    print(f"Generated hash: {hashed}")

    try:
        # Connect to database
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()

        # Update admin password
        cur.execute("""
            UPDATE users
            SET hashed_password = %s
            WHERE email = 'admin@pyramid-computer.de'
        """, (hashed,))

        affected = cur.rowcount

        if affected > 0:
            conn.commit()
            print(f"Successfully updated admin password (affected rows: {affected})")
            print("You can now login with:")
            print("  Email: admin@pyramid-computer.de")
            print("  Password: admin123")
        else:
            print("Admin user not found. Creating new admin user...")

            # Create admin user if not exists
            cur.execute("""
                INSERT INTO users (
                    id, email, username, full_name, hashed_password,
                    primary_department, is_superuser, is_active, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(),
                    'admin@pyramid-computer.de',
                    'admin',
                    'System Administrator',
                    %s,
                    'MANAGEMENT',
                    true,
                    true,
                    NOW(),
                    NOW()
                )
            """, (hashed,))

            conn.commit()
            print("Admin user created successfully")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Database error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_admin_password()