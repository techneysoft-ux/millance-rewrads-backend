"""
Quick check to see what enum values exist in the database
"""

from database import engine
from sqlalchemy import text

def check_enum():
    print("=" * 60)
    print("CHECKING PLANSTATUS ENUM VALUES")
    print("=" * 60)
    
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                SELECT unnest(enum_range(NULL::planstatus))::text as value;
            """))
            
            values = [row[0] for row in result]
            
            print(f"\nCurrent enum values ({len(values)}):")
            for i, val in enumerate(values, 1):
                print(f"  {i}. {val}")
            
            print("\nRequired values for system:")
            required = ['ACTIVE', 'COMPLETED', 'CANCELLED', 'COMPLETED_WON', 'COMPLETED_FULL']
            
            for req in required:
                if req in values:
                    print(f"  ✅ {req}")
                else:
                    print(f"  ❌ {req} - MISSING!")
            
            missing = [r for r in required if r not in values]
            
            if missing:
                print(f"\n⚠️ Missing {len(missing)} enum value(s): {', '.join(missing)}")
                print("\nTo fix, run:")
                print("  python fix_enum.py")
            else:
                print("\n✅ All required enum values exist!")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
    
    print("=" * 60)

if __name__ == "__main__":
    check_enum()
