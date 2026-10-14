"""
Debug script to test authentication flow
Run this on the VPS: python debug_auth.py
"""
from database import SessionLocal
from models import Franchise, UserRole
from auth import authenticate_user, verify_password

db = SessionLocal()

print("=" * 60)
print("DEBUGGING FRANCHISE AUTHENTICATION")
print("=" * 60)

identifier = "franchise@millancefurniture.com"
password = "millance"
role = UserRole.FRANCHISE

print(f"\n1️⃣  Testing with:")
print(f"   Identifier: {identifier}")
print(f"   Password: {password}")
print(f"   Role: {role}")
print(f"   Role type: {type(role)}")
print(f"   Role value: {role.value}")

# Step 1: Check if franchise exists
print(f"\n2️⃣  Checking database...")
franchise = db.query(Franchise).filter(Franchise.email == identifier).first()

if franchise:
    print(f"   ✅ Franchise found in database")
    print(f"   - ID: {franchise.id}")
    print(f"   - Email: {franchise.email}")
    print(f"   - Stored Password: '{franchise.password}'")
    print(f"   - Password type: {type(franchise.password)}")
    print(f"   - Password length: {len(franchise.password)}")
    print(f"   - Active: {franchise.is_active}")
else:
    print(f"   ❌ Franchise NOT found in database")

# Step 2: Test password verification
print(f"\n3️⃣  Testing password verification...")
print(f"   Provided password: '{password}'")
print(f"   Provided password type: {type(password)}")
print(f"   Provided password length: {len(password)}")

if franchise:
    match = verify_password(password, franchise.password)
    print(f"   Password match result: {match}")
    
    # Manual comparison
    manual_match = password == franchise.password
    print(f"   Manual comparison (password == stored): {manual_match}")
    
    # Character by character comparison
    print(f"\n4️⃣  Character comparison:")
    for i, (c1, c2) in enumerate(zip(password, franchise.password)):
        match_char = "✅" if c1 == c2 else "❌"
        print(f"   [{i}] '{c1}' vs '{c2}' {match_char}")

# Step 3: Test authenticate_user function
print(f"\n5️⃣  Testing authenticate_user function...")
user = authenticate_user(db, identifier, password, role)

if user:
    print(f"   ✅ Authentication SUCCESSFUL")
    print(f"   - User ID: {user.id}")
    print(f"   - Email: {user.email}")
else:
    print(f"   ❌ Authentication FAILED")
    print(f"   Debugging authenticate_user...")
    
    # Test with role as string
    print(f"\n6️⃣  Testing with role as string...")
    role_str = "franchise"
    print(f"   Role: '{role_str}' (type: {type(role_str)})")
    
    # Check what happens in authenticate_user
    print(f"   Checking: role == UserRole.FRANCHISE")
    print(f"   Result: {role == UserRole.FRANCHISE}")
    print(f"   Checking: role_str == UserRole.FRANCHISE")
    print(f"   Result: {role_str == UserRole.FRANCHISE}")
    print(f"   Checking: UserRole(role_str) == UserRole.FRANCHISE")
    try:
        print(f"   Result: {UserRole(role_str) == UserRole.FRANCHISE}")
    except Exception as e:
        print(f"   Error: {e}")

print("\n" + "=" * 60)

db.close()
