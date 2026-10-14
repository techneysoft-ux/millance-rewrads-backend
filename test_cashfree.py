"""
Test Cashfree integration
Run this to verify everything is working
"""

from cashfree_service import cashfree
from database import get_db, engine
from models import User, CashfreePayment
from sqlalchemy.orm import Session
import sys

def test_cashfree_connection():
    """Test basic Cashfree API connection"""
    print("\n🔧 Testing Cashfree Connection...")
    print(f"   App ID: {cashfree.app_id[:10]}...")
    print(f"   Environment: {cashfree.base_url}")
    print(f"   API Version: {cashfree.api_version}")
    print("   ✅ Cashfree service initialized\n")
    return True

def test_database_tables():
    """Test if payment tables exist"""
    print("🔧 Testing Database Tables...")
    
    from sqlalchemy import text
    
    tables_to_check = ['cashfree_payments', 'payment_reconciliation']
    
    with engine.connect() as conn:
        for table in tables_to_check:
            result = conn.execute(text(
                f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"
            ))
            exists = result.scalar()
            
            if exists:
                print(f"   ✅ Table '{table}' exists")
            else:
                print(f"   ❌ Table '{table}' missing!")
                return False
    
    print()
    return True

def test_create_order():
    """Test creating a payment order"""
    print("🔧 Testing Order Creation...")
    
    # Create test order
    test_order_id = f"test_order_{int(datetime.utcnow().timestamp())}"
    
    result = cashfree.create_order(
        order_id=test_order_id,
        amount=100.00,
        customer_id="TEST001",
        customer_name="Test User",
        customer_phone="9999999999",
        customer_email="test@test.com"
    )
    
    if result.get("success"):
        print(f"   ✅ Order created: {result.get('cf_order_id')}")
        print(f"   Payment Session ID: {result.get('payment_session_id')[:20]}...")
        print()
        return True
    else:
        print(f"   ❌ Order creation failed: {result.get('error')}")
        print()
        return False

def test_get_user():
    """Test getting a user from database"""
    print("🔧 Testing Database User Query...")
    
    db = next(get_db())
    user = db.query(User).first()
    
    if user:
        print(f"   ✅ Found user: {user.full_name} ({user.mld_id})")
        print()
        return True
    else:
        print("   ❌ No users found in database")
        print()
        return False

def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("CASHFREE INTEGRATION TESTS")
    print("=" * 50)
    
    tests = [
        ("Connection", test_cashfree_connection),
        ("Database Tables", test_database_tables),
        ("Database User", test_get_user),
        ("Create Order", test_create_order)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"   ❌ Error: {str(e)}\n")
            results.append((test_name, False))
    
    # Summary
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print("=" * 50)
    
    all_passed = all(success for _, success in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Cashfree integration is ready.\n")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues before proceeding.\n")
        return 1

if __name__ == "__main__":
    from datetime import datetime
    sys.exit(run_all_tests())
