"""
Migration script to add referral system fields
"""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://millancerewards:123456@localhost/millancerewards")

def run_migration():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("=" * 60)
        print("ADDING REFERRAL SYSTEM FIELDS")
        print("=" * 60)
        
        try:
            # 1. Add franchise_slug to franchises table
            print("\n1. Adding franchise_slug to franchises...")
            conn.execute(text("""
                ALTER TABLE franchises 
                ADD COLUMN IF NOT EXISTS franchise_slug VARCHAR(100) UNIQUE
            """))
            conn.commit()
            print("✅ franchise_slug added")
            
            # 2. Add earnings_wallet to franchises table
            print("\n2. Adding earnings_wallet to franchises...")
            conn.execute(text("""
                ALTER TABLE franchises 
                ADD COLUMN IF NOT EXISTS earnings_wallet FLOAT DEFAULT 0.0
            """))
            conn.commit()
            print("✅ earnings_wallet added")
            
            # 3. Add invite_code to groups table
            print("\n3. Adding invite_code to groups...")
            conn.execute(text("""
                ALTER TABLE groups 
                ADD COLUMN IF NOT EXISTS invite_code VARCHAR(20) UNIQUE
            """))
            conn.commit()
            print("✅ invite_code added")
            
            # 4. Add referred_by_franchise_id to users table
            print("\n4. Adding referred_by_franchise_id to users...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS referred_by_franchise_id INTEGER 
                REFERENCES franchises(id)
            """))
            conn.commit()
            print("✅ referred_by_franchise_id added")
            
            # 5. Add referred_by_group_id to users table
            print("\n5. Adding referred_by_group_id to users...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS referred_by_group_id INTEGER 
                REFERENCES groups(id)
            """))
            conn.commit()
            print("✅ referred_by_group_id added")
            
            # 6. Add commission_rate to enrollments table
            print("\n6. Adding commission_rate to enrollments...")
            conn.execute(text("""
                ALTER TABLE enrollments 
                ADD COLUMN IF NOT EXISTS commission_rate FLOAT DEFAULT 0.15
            """))
            conn.commit()
            print("✅ commission_rate added (15% default)")
            
            print("\n" + "=" * 60)
            print("MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    run_migration()
