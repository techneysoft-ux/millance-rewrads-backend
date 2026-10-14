import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def add_profile_photo_column():
    """Add profile_photo column to users table"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'millancerewards'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD')
        )
        cursor = conn.cursor()
        
        # Add profile_photo column
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS profile_photo VARCHAR(500);
        """)
        
        conn.commit()
        print("✅ Added profile_photo column to users table")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    add_profile_photo_column()
