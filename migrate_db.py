"""
Database Migration Script
Adds new columns to existing tables for draw system
"""
import psycopg2
from database import DATABASE_URL

def run_migration():
    # Parse database URL
    # Format: postgresql://user:password@host:port/database
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
    if not match:
        print("Error: Could not parse DATABASE_URL")
        return
    
    user, password, host, port, database = match.groups()
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cur = conn.cursor()
        
        print("Connected to database successfully!")
        print("\n🔄 Running migrations...\n")
        
        # Migration 1: Add columns to enrollments table
        print("1. Adding new columns to enrollments table...")
        
        migrations = [
            # Add savings_accumulated
            """
            ALTER TABLE enrollments 
            ADD COLUMN IF NOT EXISTS savings_accumulated FLOAT DEFAULT 0.0;
            """,
            
            # Add is_eligible_for_draw
            """
            ALTER TABLE enrollments 
            ADD COLUMN IF NOT EXISTS is_eligible_for_draw BOOLEAN DEFAULT FALSE;
            """,
            
            # Add has_won_prize
            """
            ALTER TABLE enrollments 
            ADD COLUMN IF NOT EXISTS has_won_prize BOOLEAN DEFAULT FALSE;
            """,
            
            # Add prize_won_month
            """
            ALTER TABLE enrollments 
            ADD COLUMN IF NOT EXISTS prize_won_month INTEGER;
            """,
            
            # Add prize_name
            """
            ALTER TABLE enrollments 
            ADD COLUMN IF NOT EXISTS prize_name VARCHAR(255);
            """,
            
            # Add prize_amount
            """
            ALTER TABLE enrollments 
            ADD COLUMN IF NOT EXISTS prize_amount FLOAT;
            """,
            
            # Add ended_at
            """
            ALTER TABLE enrollments 
            ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP;
            """,
        ]
        
        for migration in migrations:
            cur.execute(migration)
            print("   ✓ Executed")
        
        # Migration 2: Add column to payments table
        print("\n2. Adding savings_credited to payments table...")
        cur.execute("""
            ALTER TABLE payments 
            ADD COLUMN IF NOT EXISTS savings_credited FLOAT DEFAULT 0.0;
        """)
        print("   ✓ Executed")
        
        # Migration 3: Create draw_schedules table
        print("\n3. Creating draw_schedules table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS draw_schedules (
                id SERIAL PRIMARY KEY,
                group_id INTEGER REFERENCES groups(id),
                franchise_id INTEGER REFERENCES franchises(id),
                month_number INTEGER NOT NULL,
                draw_date TIMESTAMP NOT NULL,
                draw_time VARCHAR(50) NOT NULL,
                status VARCHAR(50) DEFAULT 'scheduled',
                conducted_by INTEGER REFERENCES franchises(id),
                conducted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("   ✓ Executed")
        
        # Migration 4: Create draw_results table
        print("\n4. Creating draw_results table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS draw_results (
                id SERIAL PRIMARY KEY,
                draw_schedule_id INTEGER REFERENCES draw_schedules(id),
                group_id INTEGER REFERENCES groups(id),
                enrollment_id INTEGER REFERENCES enrollments(id),
                user_id INTEGER REFERENCES users(id),
                prize_name VARCHAR(255) NOT NULL,
                prize_amount FLOAT NOT NULL,
                month_number INTEGER NOT NULL,
                won_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("   ✓ Executed")
        
        # Migration 5: Create redemptions table
        print("\n5. Creating redemptions table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS redemptions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                enrollment_id INTEGER REFERENCES enrollments(id),
                amount FLOAT NOT NULL,
                redemption_code VARCHAR(100) UNIQUE NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                valid_until TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                used_at_store VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("   ✓ Executed")
        
        # Commit all changes
        conn.commit()
        
        print("\n✅ All migrations completed successfully!")
        print("\n📊 Database schema updated with:")
        print("   • New columns in enrollments table (savings, eligibility, winner info)")
        print("   • New column in payments table (savings_credited)")
        print("   • New table: draw_schedules")
        print("   • New table: draw_results")
        print("   • New table: redemptions")
        
        # Close connection
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if conn:
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MIGRATION - Lucky Draw System")
    print("=" * 60)
    run_migration()
