#!/usr/bin/env python3
"""
Test coupon system functionality
"""
import requests
import json

BASE_URL = "http://localhost:8002/api"

def test_coupon_system():
    """Test coupon generation and retrieval"""
    
    print("🧪 TESTING COUPON SYSTEM")
    print("=" * 50)
    
    # Test 1: Login
    print("\n1️⃣ Testing Login...")
    login_data = {
        "email": "user@example.com",  # Replace with actual test user
        "password": "test123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            token = response.json()["access_token"]
            print("✅ Login successful")
            print(f"   Token: {token[:20]}...")
        else:
            print(f"❌ Login failed: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 2: Get Enrollments
    print("\n2️⃣ Testing Get Enrollments...")
    try:
        response = requests.get(f"{BASE_URL}/enrollments/my", headers=headers)
        if response.status_code == 200:
            enrollments = response.json()
            print(f"✅ Found {len(enrollments)} enrollment(s)")
            if enrollments:
                enrollment_id = enrollments[0]["id"]
                print(f"   Using enrollment ID: {enrollment_id}")
            else:
                print("⚠️  No enrollments found")
                return
        else:
            print(f"❌ Failed: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Test 3: Get Enrollment Details (NEW ENDPOINT)
    print("\n3️⃣ Testing Get Enrollment Details...")
    try:
        response = requests.get(f"{BASE_URL}/enrollments/{enrollment_id}", headers=headers)
        if response.status_code == 200:
            details = response.json()
            print("✅ Enrollment details retrieved")
            print(f"   Group: {details['group']['group_name']}")
            print(f"   Plan: {details['plan']['name']}")
            print(f"   Months Paid: {details['enrollment']['months_paid']}")
            print(f"   Payments with Coupons:")
            for payment in details['payment_history']:
                print(f"      - Month {payment['month']}: {payment['coupon_number'] or 'No coupon'}")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Test Payment (generates coupon)
    print("\n4️⃣ Testing Payment (Coupon Generation)...")
    payment_data = {
        "enrollment_id": enrollment_id,
        "wallet_type": "millance_rewards_wallet",
        "month": "3"  # Replace with next unpaid month
    }
    
    try:
        response = requests.post(f"{BASE_URL}/payments", json=payment_data, headers=headers)
        if response.status_code == 200:
            payment = response.json()
            print("✅ Payment successful")
            print(f"   Payment ID: {payment['id']}")
            print(f"   Month: {payment['month']}")
            print(f"   Coupon: {payment['coupon_number']}")
            print(f"   Amount: ₹{payment['amount']}")
        else:
            print(f"⚠️  Payment test skipped or failed: {response.text}")
    except Exception as e:
        print(f"⚠️  Payment error (expected if insufficient balance): {e}")
    
    # Test 5: Get Draw Status (check coupon in results)
    print("\n5️⃣ Testing Draw Status (Coupon in Results)...")
    try:
        response = requests.get(f"{BASE_URL}/user/draw-status", headers=headers)
        if response.status_code == 200:
            draw_status = response.json()
            print("✅ Draw status retrieved")
            if draw_status.get("my_results"):
                print(f"   Results with Coupons:")
                for result in draw_status["my_results"]:
                    print(f"      - Month {result['month']}: {result['coupon_number'] or 'No coupon'}")
            else:
                print("   No results yet")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 COUPON SYSTEM TEST COMPLETED!")
    print("=" * 50)

if __name__ == "__main__":
    test_coupon_system()
