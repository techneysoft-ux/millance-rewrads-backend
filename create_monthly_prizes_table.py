"""
Database Migration: Create monthly_prizes table for multi-winner system

Run this script to create the new table structure that supports
multiple prizes per month with different values and quantities.
"""

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import sys

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def create_monthly_prizes_table():
    """Create monthly_prizes table"""
    
    engine = create_engine(DATABASE_URL)
    
    create_table_sql = text("""
    CREATE TABLE IF NOT EXISTS monthly_prizes (
        id SERIAL PRIMARY KEY,
        prize_pool_id INTEGER NOT NULL REFERENCES prize_pools(id) ON DELETE CASCADE,
        month_number INTEGER NOT NULL CHECK (month_number >= 1 AND month_number <= 15),
        prize_rank INTEGER NOT NULL CHECK (prize_rank >= 1),
        prize_name VARCHAR(255) NOT NULL,
        prize_amount FLOAT NOT NULL CHECK (prize_amount > 0),
        quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 1),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        UNIQUE(prize_pool_id, month_number, prize_rank)
    );
    
    CREATE INDEX IF NOT EXISTS idx_monthly_prizes_pool_month 
        ON monthly_prizes(prize_pool_id, month_number);
    
    CREATE INDEX IF NOT EXISTS idx_monthly_prizes_pool 
        ON monthly_prizes(prize_pool_id);
    """)
    
    try:
        with engine.connect() as conn:
            conn.execute(create_table_sql)
            conn.commit()
            print("✅ Table 'monthly_prizes' created successfully!")
            print("✅ Indexes created successfully!")
            
            # Show table structure
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'monthly_prizes'
                ORDER BY ordinal_position;
            """))
            
            print("\n📋 Table Structure:")
            print("─" * 80)
            for row in result:
                print(f"  {row[0]:20} {row[1]:15} {'NULL' if row[2] == 'YES' else 'NOT NULL':10} {row[3] or ''}")
            print("─" * 80)
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False
    finally:
        engine.dispose()

def verify_table():
    """Verify table was created"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'monthly_prizes';
            """))
            count = result.scalar()
            
            if count > 0:
                print("\n✅ Verification: Table exists!")
                return True
            else:
                print("\n❌ Verification: Table NOT found!")
                return False
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("=" * 80)
    print("CREATE MONTHLY PRIZES TABLE - Multi-Winner System")
    print("=" * 80)
    print()
    
    print("This will create a new table structure for supporting multiple winners")
    print("per monthly draw with different prize values and quantities.")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response == 'yes':
        print("\n🔄 Creating table...")
        if create_monthly_prizes_table():
            if verify_table():
                print("\n✅ Migration completed successfully!")
                sys.exit(0)
            else:
                print("\n⚠️ Table created but verification failed!")
                sys.exit(1)
        else:
            print("\n❌ Migration failed!")
            sys.exit(1)
    else:
        print("\n❌ Migration cancelled.")
        sys.exit(0)
