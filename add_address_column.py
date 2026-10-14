"""
Add address column to users table
"""
from sqlalchemy import create_engine, text
from database import DATABASE_URL

def add_address_column():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='address';
        """))
        
        if result.fetchone():
            print("✅ Column 'address' already exists in users table")
        else:
            # Add address column
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN address TEXT;
            """))
            conn.commit()
            print("✅ Successfully added 'address' column to users table")

if __name__ == "__main__":
    print("=" * 60)
    print("ADDING ADDRESS COLUMN TO USERS TABLE")
    print("=" * 60)
    add_address_column()
    print("=" * 60)
    print("MIGRATION COMPLETED")
    print("=" * 60)
