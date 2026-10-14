"""
Update Savings Wallet for All Users Based on Their Payments
This script recalculates and updates savings_wallet for all users
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Database connection
DATABASE_URL = "postgresql://postgres:123456@localhost:5432/millancerewards"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def update_all_user_savings():
    """
    Update savings_wallet for all users based on their payment history
    """
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("UPDATING SAVINGS WALLET FOR ALL USERS")
        print("=" * 60)
        
        # Get all users
        users_query = text("""
            SELECT id, mld_id, full_name, savings_wallet
            FROM users
            ORDER BY id
        """)
        users = db.execute(users_query).fetchall()
        
        print(f"\n📊 Found {len(users)} users")
        
        updated_count = 0
        
        for user in users:
            user_id = user[0]
            mld_id = user[1]
            full_name = user[2]
            current_savings = user[3] or 0
            
            # Calculate total savings from payments
            payments_query = text("""
                SELECT COUNT(*), COALESCE(SUM(amount), 0)
                FROM payments
                WHERE user_id = :user_id 
                AND status = 'PAID'
                AND wallet_used = 'millance_rewards_wallet'
            """)
            result = db.execute(payments_query, {"user_id": user_id}).fetchone()
            payment_count = result[0] or 0
            total_savings = float(result[1] or 0)
            
            if payment_count > 0:
                print(f"\n👤 User: {mld_id} - {full_name}")
                print(f"   Payments from Millance Rewards Wallet: {payment_count}")
                print(f"   Current Savings: ₹{current_savings:,.2f}")
                print(f"   Expected Savings: ₹{total_savings:,.2f}")
                
                if current_savings != total_savings:
                    # Update savings wallet
                    update_query = text("""
                        UPDATE users
                        SET savings_wallet = :savings
                        WHERE id = :user_id
                    """)
                    db.execute(update_query, {"savings": total_savings, "user_id": user_id})
                    
                    print(f"   ✅ UPDATED: ₹{current_savings:,.2f} → ₹{total_savings:,.2f}")
                    updated_count += 1
                else:
                    print(f"   ✓ Already correct")
        
        # Also update enrollments.savings_accumulated
        print(f"\n" + "=" * 60)
        print("UPDATING ENROLLMENT SAVINGS ACCUMULATED")
        print("=" * 60)
        
        enrollments_query = text("""
            SELECT e.id, e.user_id, u.mld_id, e.savings_accumulated,
                   COUNT(p.id) as payment_count,
                   COALESCE(SUM(p.amount), 0) as total_amount
            FROM enrollments e
            JOIN users u ON e.user_id = u.id
            LEFT JOIN payments p ON p.enrollment_id = e.id 
                AND p.status = 'PAID'
                AND p.wallet_used = 'millance_rewards_wallet'
            GROUP BY e.id, e.user_id, u.mld_id, e.savings_accumulated
            HAVING COUNT(p.id) > 0
            ORDER BY e.id
        """)
        enrollments = db.execute(enrollments_query).fetchall()
        
        print(f"\n📊 Found {len(enrollments)} enrollments with payments")
        
        enrollment_updated = 0
        
        for enrollment in enrollments:
            enrollment_id = enrollment[0]
            user_id = enrollment[1]
            mld_id = enrollment[2]
            current_accumulated = enrollment[3] or 0
            payment_count = enrollment[4]
            expected_accumulated = float(enrollment[5])
            
            if current_accumulated != expected_accumulated:
                print(f"\n📝 Enrollment {enrollment_id} (User: {mld_id})")
                print(f"   Payments: {payment_count}")
                print(f"   Current: ₹{current_accumulated:,.2f}")
                print(f"   Expected: ₹{expected_accumulated:,.2f}")
                
                update_enrollment = text("""
                    UPDATE enrollments
                    SET savings_accumulated = :savings
                    WHERE id = :enrollment_id
                """)
                db.execute(update_enrollment, {
                    "savings": expected_accumulated,
                    "enrollment_id": enrollment_id
                })
                
                print(f"   ✅ UPDATED")
                enrollment_updated += 1
        
        db.commit()
        
        print(f"\n" + "=" * 60)
        print("✅ UPDATE COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"📊 Summary:")
        print(f"   - Users updated: {updated_count}")
        print(f"   - Enrollments updated: {enrollment_updated}")
        print(f"   - Total users processed: {len(users)}")
        print(f"   - Total enrollments processed: {len(enrollments)}")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    update_all_user_savings()
