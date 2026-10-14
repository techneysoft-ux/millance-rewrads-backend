"""
Fix PostgreSQL enum to add new PlanStatus values
Run this ONCE to update the database
"""

from database import engine
from sqlalchemy import text

def fix_planstatus_enum():
    print("=" * 70)
    print("FIXING PLANSTATUS ENUM IN DATABASE")
    print("=" * 70)
    
    with engine.connect() as conn:
        try:
            # Check current enum values
            print("\n1. Checking current enum values...")
            result = conn.execute(text("""
                SELECT unnest(enum_range(NULL::planstatus))::text as value;
            """))
            current_values = [row[0] for row in result]
            print(f"   Current values: {current_values}")
            
            # Add COMPLETED_WON if not exists
            if 'COMPLETED_WON' not in current_values:
                print("\n2. Adding 'COMPLETED_WON' to enum...")
                conn.execute(text("""
                    ALTER TYPE planstatus ADD VALUE IF NOT EXISTS 'COMPLETED_WON';
                """))
                conn.commit()
                print("   ✅ Added COMPLETED_WON")
            else:
                print("\n2. ✅ COMPLETED_WON already exists")
            
            # Add COMPLETED_FULL if not exists
            if 'COMPLETED_FULL' not in current_values:
                print("\n3. Adding 'COMPLETED_FULL' to enum...")
                conn.execute(text("""
                    ALTER TYPE planstatus ADD VALUE IF NOT EXISTS 'COMPLETED_FULL';
                """))
                conn.commit()
                print("   ✅ Added COMPLETED_FULL")
            else:
                print("\n3. ✅ COMPLETED_FULL already exists")
            
            # Verify new values
            print("\n4. Verifying updated enum values...")
            result = conn.execute(text("""
                SELECT unnest(enum_range(NULL::planstatus))::text as value;
            """))
            new_values = [row[0] for row in result]
            print(f"   New values: {new_values}")
            
            print("\n" + "=" * 70)
            print("ENUM UPDATE COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print("\nYou can now conduct draws without errors.")
            print("The system will be able to set winner status to 'COMPLETED_WON'")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("\nIf you see 'cannot add value to enum type in transaction block',")
            print("you need to run this outside a transaction.")
            raise

if __name__ == "__main__":
    fix_planstatus_enum()
