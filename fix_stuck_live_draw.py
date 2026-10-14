#!/usr/bin/env python3
"""
Fix stuck live draws in the database
"""
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:123456@localhost:5432/millancerewards")

print("=" * 60)
print("🔧 FIX STUCK LIVE DRAWS")
print("=" * 60)

try:
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    print(f"\n✅ Connected to database: millancerewards")
    
    # Check for live draws
    print("\n🔍 Checking for stuck 'live' draws...")
    
    result = db.execute(text("""
        SELECT id, group_id, month_number, status, draw_date, conducted_at
        FROM draw_schedules 
        WHERE status = 'live'
        ORDER BY id
    """))
    
    live_draws = result.fetchall()
    
    if not live_draws:
        print("✅ No stuck live draws found!")
        db.close()
        sys.exit(0)
    
    print(f"\n⚠️  Found {len(live_draws)} stuck live draw(s):\n")
    
    for draw in live_draws:
        print(f"  Draw ID: {draw[0]}")
        print(f"  Group: {draw[1]}")
        print(f"  Month: {draw[2]}")
        print(f"  Status: {draw[3]}")
        print(f"  Draw Date: {draw[4]}")
        print(f"  Conducted At: {draw[5]}")
        print()
    
    # Ask for confirmation
    print("\n❓ What would you like to do?")
    print("1. Mark as 'completed' (draw finished)")
    print("2. Mark as 'scheduled' (draw not started yet)")
    print("3. Cancel (do nothing)")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        new_status = "completed"
        print(f"\n🔄 Changing status to '{new_status}'...")
        
        for draw in live_draws:
            db.execute(text("""
                UPDATE draw_schedules 
                SET status = :status,
                    conducted_at = :conducted_at
                WHERE id = :draw_id
            """), {
                "status": new_status,
                "conducted_at": datetime.utcnow(),
                "draw_id": draw[0]
            })
            print(f"  ✅ Draw {draw[0]} → {new_status}")
        
        db.commit()
        print(f"\n✅ Successfully updated {len(live_draws)} draw(s) to '{new_status}'")
        
    elif choice == "2":
        new_status = "scheduled"
        print(f"\n🔄 Changing status to '{new_status}'...")
        
        for draw in live_draws:
            db.execute(text("""
                UPDATE draw_schedules 
                SET status = :status,
                    conducted_at = NULL
                WHERE id = :draw_id
            """), {
                "status": new_status,
                "draw_id": draw[0]
            })
            print(f"  ✅ Draw {draw[0]} → {new_status}")
        
        db.commit()
        print(f"\n✅ Successfully updated {len(live_draws)} draw(s) to '{new_status}'")
        
    elif choice == "3":
        print("\n❌ Cancelled. No changes made.")
    
    else:
        print("\n❌ Invalid choice. No changes made.")
    
    # Verify changes
    result = db.execute(text("""
        SELECT COUNT(*) 
        FROM draw_schedules 
        WHERE status = 'live'
    """))
    
    count = result.fetchone()[0]
    
    if count == 0:
        print("\n✅ No more live draws in database!")
    else:
        print(f"\n⚠️  Still {count} live draw(s) remaining")
    
    db.close()
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ Script completed")
print("=" * 60)
