#!/usr/bin/env python3
"""Fix database schema issues"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database connection parameters
DB_CONFIG = {
    "host": "localhost",
    "port": 15432,
    "database": "pyramid_rag",
    "user": "pyramid_user",
    "password": "pyramid_secure_pass"
}

def fix_database_schema():
    """Add missing columns and fix schema issues"""

    conn = None
    cursor = None

    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print("Connected to database")

        # Check and add missing columns
        fixes = [
            # Add chat_type column if missing
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name='chat_sessions' AND column_name='chat_type')
                THEN
                    ALTER TABLE chat_sessions ADD COLUMN chat_type VARCHAR(50) DEFAULT 'NORMAL';
                END IF;
            END $$;
            """,

            # Add expires_at column if missing
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name='chat_sessions' AND column_name='expires_at')
                THEN
                    ALTER TABLE chat_sessions ADD COLUMN expires_at TIMESTAMP;
                END IF;
            END $$;
            """,

            # Add folder_path column if missing
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name='chat_sessions' AND column_name='folder_path')
                THEN
                    ALTER TABLE chat_sessions ADD COLUMN folder_path VARCHAR(255);
                END IF;
            END $$;
            """,

            # Create chat_files table if missing
            """
            CREATE TABLE IF NOT EXISTS chat_files (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
                file_name VARCHAR(255) NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                mime_type VARCHAR(100),
                scope VARCHAR(50) DEFAULT 'session',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,

            # Create indexes
            """
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_chat_files_session_id ON chat_files(session_id);
            """,

            # Fix document_chunks table
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name='document_chunks' AND column_name='embedding')
                THEN
                    ALTER TABLE document_chunks ADD COLUMN embedding vector(384);
                END IF;
            END $$;
            """,
        ]

        for i, fix_sql in enumerate(fixes, 1):
            try:
                cursor.execute(fix_sql)
                print(f"Applied fix {i}")
            except Exception as e:
                print(f"Fix {i} failed (might already exist): {e}")

        # Verify tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()
        print("\nExisting tables:")
        for table in tables:
            print(f"  - {table[0]}")

        # Check chat_sessions columns
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'chat_sessions'
            ORDER BY ordinal_position;
        """)

        columns = cursor.fetchall()
        print("\nchat_sessions columns:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")

        print("\nDatabase schema fixed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return True

if __name__ == "__main__":
    fix_database_schema()