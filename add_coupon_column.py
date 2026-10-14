#!/usr/bin/env python3
"""
Add coupon_number column to payments table
"""
import psycopg2
import os
import sys

# Add parent directory to path to import from .env
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

def add_coupon_column():
    """Add coupon_number column to payments table"""
    
    # Try to parse DATABASE_URL first
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Parse: postgresql://postgres:123456@localhost:5432/millancerewards
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
        if match:
            user, password, host, port, dbname = match.groups()
        else:
            # Fallback
            user = "postgres"
            password = "123456"
            host = "localhost"
            port = "5432"
            dbname = "millancerewards"
    else:
        # Get from individual env vars
        dbname = os.getenv("DATABASE_NAME", "millancerewards")
        user = os.getenv("DATABASE_USER", "postgres")
        password = os.getenv("DATABASE_PASSWORD", "123456")
        host = os.getenv("DATABASE_HOST", "localhost")
        port = os.getenv("DATABASE_PORT", "5432")
    
    print(f"🔧 Connecting to database: {dbname} as user: {user}")
    
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        cursor = conn.cursor()
        
        print("🔧 Adding coupon_number column to payments table...")
        
        # Add coupon_number column
        cursor.execute("""
            ALTER TABLE payments 
            ADD COLUMN IF NOT EXISTS coupon_number VARCHAR(20);
        """)
        
        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_payments_coupon_number 
            ON payments(coupon_number);
        """)
        
        conn.commit()
        print("✅ Added coupon_number column to payments table")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    add_coupon_column()
    print("\n✅ Database migration completed!")
