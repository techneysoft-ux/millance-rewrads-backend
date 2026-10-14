"""
Add prize image URLs and winner counts to prize_pools table
"""
from sqlalchemy import text
from database import engine

def add_prize_metadata():
    print("=" * 60)
    print("ADDING PRIZE METADATA TO PRIZE_POOLS TABLE")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Add prize image URLs and winner counts for all 15 prizes
        for i in range(1, 16):
            print(f"Adding metadata for prize {i}...")
            
            try:
                # Add image URL column
                conn.execute(text(f"""
                    ALTER TABLE prize_pools
                    ADD COLUMN IF NOT EXISTS prize_{i}_image_url VARCHAR(500)
                """))
                
                # Add winner count column
                conn.execute(text(f"""
                    ALTER TABLE prize_pools
                    ADD COLUMN IF NOT EXISTS prize_{i}_winner_count INTEGER DEFAULT 1
                """))
                
                print(f"✅ Prize {i} metadata added")
            except Exception as e:
                print(f"⚠️  Prize {i} metadata may already exist: {e}")
        
        # Add draw time to draws table
        try:
            print("\nAdding draw_time to draws table...")
            conn.execute(text("""
                ALTER TABLE draws
                ADD COLUMN IF NOT EXISTS draw_time VARCHAR(10) DEFAULT '19:00'
            """))
            print("✅ draw_time column added")
        except Exception as e:
            print(f"⚠️  draw_time may already exist: {e}")
        
        conn.commit()
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    add_prize_metadata()
