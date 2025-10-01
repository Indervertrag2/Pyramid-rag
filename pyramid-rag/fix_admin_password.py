#!/usr/bin/env python3
"""Fix admin password hash in the database"""

import bcrypt

# Generate a proper bcrypt hash for admin123
password = b'admin123'
salt = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(password, salt).decode('utf-8')

print(f"UPDATE users SET hashed_password = '{hashed}' WHERE email = 'admin@pyramid-computer.de';")
print(f"Generated hash: {hashed}")