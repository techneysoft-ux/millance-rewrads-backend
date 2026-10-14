"""
Migration: Add Payment Deadline Policy Fields
- Add payment deadline tracking
- Add consecutive missed payments counter
- Add legacy policy flag
- Add overdue status tracking
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:123456@localhost:5432/millancerewards")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def add_payment_deadline_fields():
    """Add new fields for payment deadline policy"""
    db = SessionLocal()
    
    try:
        print("🔧 Adding payment deadline policy fields...")
        
        # Add fields to enrollments table
        enrollment_fields = [
            "ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS consecutive_missed_payments INTEGER DEFAULT 0",
            "ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS is_legacy_policy BOOLEAN DEFAULT TRUE",  # Existing = TRUE (old policy)
            "ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS auto_removed BOOLEAN DEFAULT FALSE",
            "ALTER TABLE enrollments ADD COLUMN IF NOT EXISTS removal_date TIMESTAMP NULL",
        ]
        
        for sql in enrollment_fields:
            db.execute(text(sql))
            print(f"✅ Executed: {sql[:80]}...")
        
        # Add fields to payments table
        payment_fields = [
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_deadline TIMESTAMP NULL",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS is_overdue BOOLEAN DEFAULT FALSE",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS days_overdue INTEGER DEFAULT 0",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS month_number INTEGER NULL",  # 1, 2, 3... for easy tracking
        ]
        
        for sql in payment_fields:
            db.execute(text(sql))
            print(f"✅ Executed: {sql[:80]}...")
        
        db.commit()
        print("\n✅ All payment deadline policy fields added successfully!")
        
        # Update existing enrollments to set enrollment_date from created_at
        print("\n🔧 Setting enrollment dates for existing records...")
        db.execute(text("""
            UPDATE enrollments 
            SET enrollment_date = created_at 
            WHERE enrollment_date IS NULL
        """))
        db.commit()
        print("✅ Enrollment dates set from created_at")
        
        # Mark all existing enrollments as legacy policy
        print("\n🔧 Marking existing enrollments as legacy policy...")
        result = db.execute(text("""
            UPDATE enrollments 
            SET is_legacy_policy = TRUE
            WHERE is_legacy_policy IS NULL OR is_legacy_policy = FALSE
        """))
        db.commit()
        print(f"✅ Marked {result.rowcount} enrollments as legacy policy (no deadline enforcement)")
        
        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\n📋 Summary:")
        print("   - Added enrollment_date, consecutive_missed_payments, is_legacy_policy")
        print("   - Added auto_removed, removal_date to enrollments")
        print("   - Added payment_deadline, is_overdue, days_overdue to payments")
        print("   - All existing enrollments: is_legacy_policy = TRUE")
        print("   - New enrollments will use deadline policy (is_legacy_policy = FALSE)")
        print("\n")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("PAYMENT DEADLINE POLICY MIGRATION")
    print("="*60 + "\n")
    add_payment_deadline_fields()
