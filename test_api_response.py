"""
Test the actual API response for scheduled draws
"""

import requests
import json

BASE_URL = "http://localhost:8002/api"

def test_api():
    print("=" * 70)
    print("TESTING FRANCHISE API RESPONSE")
    print("=" * 70)
    
    # Login
    print("\n1. Logging in as franchise...")
    login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "franchise@millancefurniture.com",
        "password": "millance",
        "role": "franchise"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")
    
    # Get scheduled draws
    print("\n2. Calling GET /api/franchise/draws/scheduled...")
    response = requests.get(f"{BASE_URL}/franchise/draws/scheduled", headers=headers)
    
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ API Response:\n")
        print(json.dumps(data, indent=2))
        
        if len(data) > 0:
            draw = data[0]
            print(f"\n   📊 First Draw Details:")
            print(f"      ID: {draw['id']}")
            print(f"      Group: {draw['group_name']}")
            print(f"      Month: {draw['month_number']}")
            print(f"      Eligible Users: {draw['eligible_users_count']}")
            
            if draw['eligible_users_count'] > 0:
                print(f"\n   ✅ GOOD! Showing {draw['eligible_users_count']} eligible user(s)")
                print(f"   → Conduct Draw should work!")
            else:
                print(f"\n   ❌ PROBLEM! Showing 0 eligible users")
                print(f"   → This needs investigation")
    else:
        print(f"   ❌ Error: {response.text}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_api()
