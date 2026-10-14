"""
Add PIN column to users table
Run this once: python add_pin_column.py
"""

from database import engine
from sqlalchemy import text

def add_pin_column():
    print("=" * 60)
    print("ADDING PIN COLUMN TO USERS TABLE")
    print("=" * 60)
    
    with engine.connect() as conn:
        try:
            # Add pin column
            print("\nAdding pin column...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS pin VARCHAR(4);
            """))
            conn.commit()
            print("✅ PIN column added successfully")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            raise
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    add_pin_column()
