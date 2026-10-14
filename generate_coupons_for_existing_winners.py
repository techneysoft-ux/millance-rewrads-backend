"""
Generate coupon codes for existing winners (retroactive)
"""
from database import SessionLocal
from models import Enrollment, CouponCounter
from sqlalchemy import and_

def generate_coupon_code(db, group_id):
    """Generate unique coupon code in format WINNER-{0001}-GROUP{id}"""
    counter = db.query(CouponCounter).first()
    
    if not counter:
        counter = CouponCounter(last_number=0)
        db.add(counter)
        db.flush()
    
    counter.last_number += 1
    coupon_number = str(counter.last_number).zfill(4)
    return f"WINNER-{coupon_number}-GROUP{group_id}"

def generate_coupons_for_existing_winners():
    """Generate coupons for all existing winners who don't have coupon codes"""
    db = SessionLocal()
    
    try:
        print("🔍 Finding existing winners without coupon codes...")
        
        # Find all enrollments where user won prize but no coupon code
        winners = db.query(Enrollment).filter(
            and_(
                Enrollment.has_won_prize == True,
                Enrollment.coupon_code == None
            )
        ).all()
        
        if not winners:
            print("✅ No existing winners found without coupon codes!")
            return
        
        print(f"📋 Found {len(winners)} winners without coupon codes")
        
        for winner in winners:
            try:
                # Generate coupon code
                coupon_code = generate_coupon_code(db, winner.group_id)
                
                # Update enrollment
                winner.coupon_code = coupon_code
                winner.coupon_status = "pending"
                
                print(f"✅ Generated {coupon_code} for enrollment #{winner.id} (User #{winner.user_id}, Prize: {winner.prize_name})")
                
            except Exception as e:
                print(f"❌ Error generating coupon for enrollment #{winner.id}: {e}")
                continue
        
        db.commit()
        print(f"\n🎉 Successfully generated {len(winners)} coupon codes!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_coupons_for_existing_winners()
