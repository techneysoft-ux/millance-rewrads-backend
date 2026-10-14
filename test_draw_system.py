"""
Test script to verify draw system is working correctly
Run this to check if draws can be conducted properly
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8002/api"

# Test credentials
FRANCHISE_EMAIL = "franchise@millancefurniture.com"
FRANCHISE_PASSWORD = "millance"

def test_draw_system():
    print("=" * 60)
    print("DRAW SYSTEM TEST")
    print("=" * 60)
    
    # Login as franchise
    print("\n1. Logging in as franchise...")
    login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": FRANCHISE_EMAIL,
        "password": FRANCHISE_PASSWORD,
        "role": "franchise"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")
    
    # Get scheduled draws
    print("\n2. Fetching scheduled draws...")
    scheduled_response = requests.get(f"{BASE_URL}/franchise/draws/scheduled", headers=headers)
    
    if scheduled_response.status_code != 200:
        print(f"❌ Failed to get scheduled draws: {scheduled_response.text}")
        return
    
    scheduled_draws = scheduled_response.json()
    print(f"✅ Found {len(scheduled_draws)} scheduled draws")
    
    if len(scheduled_draws) == 0:
        print("\n⚠️ No scheduled draws found. Please schedule a draw first.")
        return
    
    # Display scheduled draws
    print("\n3. Scheduled Draw Details:")
    for idx, draw in enumerate(scheduled_draws, 1):
        print(f"\n   Draw #{idx}:")
        print(f"   - ID: {draw['id']}")
        print(f"   - Group: {draw['group_name']}")
        print(f"   - Month: {draw['month_number']}")
        print(f"   - Date: {draw['draw_date']}")
        print(f"   - Eligible Users: {draw['eligible_users_count']}")
    
    # Test conducting the first draw
    if len(scheduled_draws) > 0:
        first_draw = scheduled_draws[0]
        
        if first_draw['eligible_users_count'] == 0:
            print(f"\n⚠️ Draw ID {first_draw['id']} has 0 eligible users!")
            print("   This means either:")
            print("   - No users are enrolled in this group")
            print("   - Users haven't paid for this month yet")
            print("   - Users have already won prizes")
            return
        
        print(f"\n4. Testing conduct draw for Draw ID {first_draw['id']}...")
        conduct_response = requests.post(
            f"{BASE_URL}/franchise/draws/{first_draw['id']}/conduct",
            headers=headers
        )
        
        if conduct_response.status_code != 200:
            print(f"❌ Failed to conduct draw: {conduct_response.text}")
            return
        
        result = conduct_response.json()
        print("✅ Draw conducted successfully!")
        print(f"\n5. Winner Details:")
        print(f"   - Name: {result['winner']['full_name']}")
        print(f"   - MLD ID: {result['winner']['mld_id']}")
        print(f"   - Email: {result['winner']['email']}")
        print(f"   - Prize: {result['prize']['name']}")
        print(f"   - Amount: ₹{result['prize']['amount']:,.2f}")
        print(f"   - Total Benefit: ₹{result['total_benefit']:,.2f}")
    
    # Get draw history
    print("\n6. Fetching draw history...")
    history_response = requests.get(f"{BASE_URL}/franchise/draws/history", headers=headers)
    
    if history_response.status_code != 200:
        print(f"❌ Failed to get draw history: {history_response.text}")
        return
    
    history = history_response.json()
    print(f"✅ Found {len(history)} completed draws")
    
    if len(history) > 0:
        print("\n7. Recent Draw History:")
        for idx, draw in enumerate(history[-3:], 1):  # Show last 3
            print(f"\n   Draw #{idx}:")
            print(f"   - Group: {draw['group_name']}")
            print(f"   - Month: {draw['month_number']}")
            print(f"   - Winner: {draw['winner']['full_name'] if draw['winner'] else 'N/A'}")
            print(f"   - MLD ID: {draw['winner']['mld_id'] if draw['winner'] else 'N/A'}")
            print(f"   - Prize: {draw['prize_name']} - ₹{draw['prize_amount']:,.2f}" if draw['prize_name'] else 'N/A')
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_draw_system()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
