from database import SessionLocal
from models import Franchise, UserRole
from auth import authenticate_user

db = SessionLocal()

print("=" * 50)
print("TESTING FRANCHISE LOGIN")
print("=" * 50)

# Test franchise login
identifier = "franchise@millancefurniture.com"
password = "millance"
role = UserRole.FRANCHISE

print(f"\n🔐 Testing authentication:")
print(f"  Identifier: {identifier}")
print(f"  Password: {password}")
print(f"  Role: {role}")
print(f"  Role value: {role.value}")

# Try to authenticate
user = authenticate_user(db, identifier, password, role)

if user:
    print(f"\n✅ AUTHENTICATION SUCCESSFUL!")
    print(f"  User ID: {user.id}")
    print(f"  Email: {user.email}")
    print(f"  Franchise Name: {user.franchise_name}")
    print(f"  Active: {user.is_active}")
else:
    print(f"\n❌ AUTHENTICATION FAILED!")
    
    # Debug: Check if user exists
    franchise = db.query(Franchise).filter(Franchise.email == identifier).first()
    if franchise:
        print(f"\n🔍 Debug: Franchise EXISTS in database")
        print(f"  Stored password: '{franchise.password}'")
        print(f"  Provided password: '{password}'")
        print(f"  Passwords match: {franchise.password == password}")
    else:
        print(f"\n🔍 Debug: Franchise NOT FOUND in database")

print("\n" + "=" * 50)

db.close()
