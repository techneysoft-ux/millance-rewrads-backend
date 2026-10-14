"""
Quick script to check draw eligibility for debugging
"""
import sys
sys.path.append('.')

from database import SessionLocal
from models import User, Enrollment, DrawSchedule, Group, PlanStatus

def check_eligibility():
    db = SessionLocal()
    
    print("=" * 70)
    print("DRAW ELIGIBILITY CHECK")
    print("=" * 70)
    
    # Find the user
    user = db.query(User).filter(User.mld_id == "866257").first()
    
    if not user:
        print("❌ User with MLD ID 866257 not found!")
        return
    
    print(f"\n✅ User Found: {user.full_name} (MLD: {user.mld_id})")
    print(f"   Email: {user.email}")
    
    # Get enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == user.id
    ).first()
    
    if not enrollment:
        print("❌ No enrollment found for this user!")
        return
    
    print(f"\n📋 Enrollment Details:")
    print(f"   ID: {enrollment.id}")
    print(f"   Group ID: {enrollment.group_id}")
    print(f"   Status: {enrollment.status}")
    print(f"   Months Paid: {enrollment.months_paid}")
    print(f"   Has Won Prize: {enrollment.has_won_prize}")
    print(f"   Is Eligible for Draw: {enrollment.is_eligible_for_draw}")
    
    # Get group info
    group = db.query(Group).filter(Group.id == enrollment.group_id).first()
    if group:
        print(f"\n👥 Group: {group.group_name} ({group.group_id})")
        print(f"   Members: {group.current_members} / {group.max_members}")
    
    # Check for scheduled draws
    print(f"\n📅 Checking Scheduled Draws for Group {enrollment.group_id}...")
    draws = db.query(DrawSchedule).filter(
        DrawSchedule.group_id == enrollment.group_id,
        DrawSchedule.status == "scheduled"
    ).all()
    
    if not draws:
        print("   ⚠️ No scheduled draws found for this group!")
        print("   → Franchise needs to schedule a draw first")
        return
    
    print(f"   Found {len(draws)} scheduled draw(s):\n")
    
    for draw in draws:
        print(f"   Draw ID: {draw.id}")
        print(f"   Month Number: {draw.month_number}")
        print(f"   Draw Date: {draw.draw_date}")
        print(f"   Draw Time: {draw.draw_time}")
        
        # Check eligibility for this specific draw
        is_eligible = (
            enrollment.status == PlanStatus.ACTIVE and
            not enrollment.has_won_prize and
            enrollment.months_paid >= draw.month_number
        )
        
        print(f"   User's Months Paid: {enrollment.months_paid}")
        print(f"   Required for Draw: {draw.month_number}")
        
        if is_eligible:
            print(f"   ✅ USER IS ELIGIBLE for this draw!\n")
        else:
            print(f"   ❌ USER NOT ELIGIBLE:")
            if enrollment.status != PlanStatus.ACTIVE:
                print(f"      - Status is '{enrollment.status}' (needs to be 'active')")
            if enrollment.has_won_prize:
                print(f"      - Already won a prize")
            if enrollment.months_paid < draw.month_number:
                print(f"      - Paid {enrollment.months_paid} months, needs {draw.month_number}")
            print()
    
    # Count total eligible users for each draw
    print(f"\n📊 Eligible Users Count for Each Draw:")
    for draw in draws:
        eligible_count = db.query(Enrollment).filter(
            Enrollment.group_id == draw.group_id,
            Enrollment.status == PlanStatus.ACTIVE,
            Enrollment.has_won_prize == False,
            Enrollment.months_paid >= draw.month_number
        ).count()
        
        print(f"   Draw ID {draw.id} (Month {draw.month_number}): {eligible_count} eligible user(s)")
    
    print("\n" + "=" * 70)
    
    db.close()

if __name__ == "__main__":
    check_eligibility()
