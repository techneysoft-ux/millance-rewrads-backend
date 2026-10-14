"""
Test user draw status API endpoint
"""

import requests
import json

BASE_URL = "http://localhost:8002/api"

def test_user_draw_status():
    print("=" * 70)
    print("TESTING USER DRAW STATUS API")
    print("=" * 70)
    
    # Login as user
    print("\n1. Logging in as user...")
    login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "user@millancefurniture.com",
        "password": "millance",
        "role": "user"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")
    
    # Get draw status
    print("\n2. Calling GET /api/users/draws/status...")
    response = requests.get(f"{BASE_URL}/users/draws/status", headers=headers)
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ API Response:\n")
        print(json.dumps(data, indent=2))
        
        print("\n3. Parsed Data:")
        
        # Enrollment status
        enrollment = data.get("enrollment_status", {})
        print(f"\n   📊 Enrollment Status:")
        print(f"      Has Won: {enrollment.get('has_won')}")
        print(f"      Prize Name: {enrollment.get('prize_name')}")
        print(f"      Prize Amount: ₹{enrollment.get('prize_amount') or 0:,.2f}")
        print(f"      Months Paid: {enrollment.get('months_paid')}")
        print(f"      Savings: ₹{enrollment.get('savings_accumulated') or 0:,.2f}")
        
        # Draw results
        results = data.get("my_results", [])
        print(f"\n   🎯 Draw Results ({len(results)} draws):")
        if results:
            for result in results:
                status_icon = "🏆" if result["status"] == "won" else "❌"
                print(f"      {status_icon} Month {result['month']}: {result['status'].upper()}")
                if result["status"] == "won":
                    print(f"         Prize: {result['prize_name']} - ₹{result['prize_amount']:,.2f}")
                else:
                    print(f"         Winner: MLD {result['winner_mld_id']}")
        else:
            print("      No draw history yet")
        
        # Next draw
        next_draw = data.get("next_draw")
        print(f"\n   📅 Next Draw:")
        if next_draw:
            print(f"      Month: {next_draw.get('month_number')}")
            print(f"      Date: {next_draw.get('draw_date')}")
            print(f"      Eligible: {'✅ Yes' if next_draw.get('eligible') else '❌ No'}")
        else:
            print("      No upcoming draw scheduled")
        
    else:
        print(f"   ❌ Error: {response.text}")
    
    # Get enrollments
    print("\n4. Calling GET /api/enrollments/my...")
    enroll_response = requests.get(f"{BASE_URL}/enrollments/my", headers=headers)
    
    print(f"   Status Code: {enroll_response.status_code}")
    
    if enroll_response.status_code == 200:
        enrollments = enroll_response.json()
        print(f"   ✅ Found {len(enrollments)} enrollment(s)\n")
        
        for idx, enroll in enumerate(enrollments, 1):
            print(f"   Enrollment #{idx}:")
            print(f"      Status: {enroll.get('status')}")
            print(f"      Months Paid: {enroll.get('months_paid')}")
            print(f"      Total Paid: ₹{enroll.get('total_paid'):,.2f}")
            print(f"      Savings: ₹{enroll.get('savings_accumulated'):,.2f}")
    else:
        print(f"   ❌ Error: {enroll_response.text}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    test_user_draw_status()
