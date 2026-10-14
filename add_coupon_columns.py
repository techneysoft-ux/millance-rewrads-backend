"""
Migration script to add coupon columns to enrollments table
"""
from database import engine
from sqlalchemy import text

def add_coupon_columns():
    """Add coupon-related columns to enrollments table"""
    
    with engine.connect() as conn:
        print("🔧 Adding coupon columns to enrollments table...")
        
        try:
            # Add coupon_code column
            conn.execute(text("""
                ALTER TABLE enrollments 
                ADD COLUMN IF NOT EXISTS coupon_code VARCHAR(50) UNIQUE
            """))
            print("✅ Added coupon_code column")
            
            # Add coupon_status column
            conn.execute(text("""
                ALTER TABLE enrollments 
                ADD COLUMN IF NOT EXISTS coupon_status VARCHAR(20) DEFAULT 'pending'
            """))
            print("✅ Added coupon_status column")
            
            # Add redeemed_at column
            conn.execute(text("""
                ALTER TABLE enrollments 
                ADD COLUMN IF NOT EXISTS redeemed_at TIMESTAMP
            """))
            print("✅ Added redeemed_at column")
            
            # Add redeemed_by_admin_id column
            conn.execute(text("""
                ALTER TABLE enrollments 
                ADD COLUMN IF NOT EXISTS redeemed_by_admin_id INTEGER REFERENCES admins(id)
            """))
            print("✅ Added redeemed_by_admin_id column")
            
            # Add redeemed_by_franchise_id column
            conn.execute(text("""
                ALTER TABLE enrollments 
                ADD COLUMN IF NOT EXISTS redeemed_by_franchise_id INTEGER REFERENCES franchises(id)
            """))
            print("✅ Added redeemed_by_franchise_id column")
            
            conn.commit()
            print("✅ All coupon columns added successfully!")
            
        except Exception as e:
            print(f"❌ Error adding columns: {e}")
            conn.rollback()
            
        # Create coupon_counter table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS coupon_counter (
                    id SERIAL PRIMARY KEY,
                    last_number INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✅ Created coupon_counter table")
            
            # Insert initial counter if not exists
            conn.execute(text("""
                INSERT INTO coupon_counter (last_number)
                SELECT 0
                WHERE NOT EXISTS (SELECT 1 FROM coupon_counter)
            """))
            print("✅ Initialized coupon counter")
            
            conn.commit()
            print("✅ Coupon counter table created successfully!")
            
        except Exception as e:
            print(f"❌ Error creating coupon_counter table: {e}")
            conn.rollback()

if __name__ == "__main__":
    add_coupon_columns()
    print("\n🎉 Migration completed!")
