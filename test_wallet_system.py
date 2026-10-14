"""
Test Wallet & PIN System
"""

import requests
import json

BASE_URL = "http://localhost:8002/api"

def test_wallet_system():
    print("=" * 70)
    print("TESTING WALLET & PIN SYSTEM")
    print("=" * 70)
    
    # Login as user
    print("\n1. Logging in as user...")
    login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "identifier": "user@millancefurniture.com",
        "password": "millance",
        "role": "user"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    user_data = login_response.json()["user_data"]
    mld_id = user_data["mld_id"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✅ Login successful - MLD ID: {mld_id}")
    
    # Check PIN status
    print("\n2. Checking PIN status...")
    pin_status = requests.get(f"{BASE_URL}/users/pin/status", headers=headers)
    print(f"   Status: {pin_status.json()}")
    
    has_pin = pin_status.json().get("has_pin")
    
    if not has_pin:
        # Set PIN
        print("\n3. Setting PIN (1234)...")
        set_pin = requests.post(
            f"{BASE_URL}/users/pin/set",
            headers=headers,
            json={"pin": "1234"}
        )
        if set_pin.status_code == 200:
            print("   ✅ PIN set successfully")
        else:
            print(f"   ❌ Failed: {set_pin.text}")
    else:
        print("\n3. PIN already set")
    
    # Test PIN verify (public endpoint)
    print("\n4. Testing PIN verify...")
    verify = requests.post(
        f"{BASE_URL}/users/pin/verify",
        json={"mld_id": mld_id, "pin": "1234"}
    )
    if verify.status_code == 200:
        print("   ✅ PIN verified successfully")
    else:
        print(f"   ❌ Failed: {verify.text}")
    
    # Get wallet balance
    print("\n5. Getting wallet balance...")
    wallet = requests.get(f"{BASE_URL}/users/wallet", headers=headers)
    wallet_data = wallet.json()
    print(f"   Millance Rewards: ₹{wallet_data['millance_rewards_wallet']:.2f}")
    print(f"   Savings: ₹{wallet_data['savings_wallet']:.2f}")
    
    # Test wallet payment
    if wallet_data['millance_rewards_wallet'] >= 100:
        print("\n6. Testing wallet payment (₹100 from Millance Rewards)...")
        payment = requests.post(
            f"{BASE_URL}/users/wallet/pay",
            json={
                "mld_id": mld_id,
                "amount": 100.0,
                "pin": "1234",
                "wallet_type": "millance_rewards_wallet"
            }
        )
        if payment.status_code == 200:
            result = payment.json()
            print("   ✅ Payment successful")
            print(f"   Transaction ID: {result['transaction_id']}")
            print(f"   Amount Paid: ₹{result['amount_paid']:.2f}")
            print(f"   New Balance: ₹{result['new_balance']:.2f}")
        else:
            print(f"   ❌ Failed: {payment.text}")
    else:
        print("\n6. Skipping payment test (insufficient balance)")
    
    # Get transactions
    print("\n7. Getting transactions...")
    
    # All transactions
    all_trans = requests.get(f"{BASE_URL}/users/transactions", headers=headers)
    print(f"   All: {len(all_trans.json())} transactions")
    
    # Store purchases only
    store_trans = requests.get(
        f"{BASE_URL}/users/transactions?transaction_type=store",
        headers=headers
    )
    print(f"   Store purchases: {len(store_trans.json())} transactions")
    
    if store_trans.json():
        latest = store_trans.json()[0]
        print(f"\n   Latest store purchase:")
        print(f"   - Amount: ₹{latest['amount']:.2f}")
        print(f"   - Date: {latest['created_at']}")
        print(f"   - Description: {latest['description']}")
    
    # Test change PIN
    print("\n8. Testing change PIN (to 5678)...")
    change_pin = requests.post(
        f"{BASE_URL}/users/pin/change",
        headers=headers,
        json={"new_pin": "5678"}
    )
    if change_pin.status_code == 200:
        print("   ✅ PIN changed successfully")
        
        # Verify new PIN
        verify_new = requests.post(
            f"{BASE_URL}/users/pin/verify",
            json={"mld_id": mld_id, "pin": "5678"}
        )
        if verify_new.status_code == 200:
            print("   ✅ New PIN verified")
        
        # Change back to 1234
        requests.post(
            f"{BASE_URL}/users/pin/change",
            headers=headers,
            json={"new_pin": "1234"}
        )
        print("   ✅ PIN changed back to 1234")
    else:
        print(f"   ❌ Failed: {change_pin.text}")
    
    # Test password change
    print("\n9. Testing password change...")
    change_pass = requests.post(
        f"{BASE_URL}/users/password/change",
        headers=headers,
        json={"new_password": "millance"}
    )
    if change_pass.status_code == 200:
        print("   ✅ Password changed successfully (set back to 'millance')")
    else:
        print(f"   ❌ Failed: {change_pass.text}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_wallet_system()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
