from database import SessionLocal
from models import Franchise, Admin, User

db = SessionLocal()

print("=" * 50)
print("CHECKING DATABASE USERS")
print("=" * 50)

# Check Franchise
franchises = db.query(Franchise).all()
print(f"\n📊 FRANCHISES ({len(franchises)}):")
for f in franchises:
    print(f"  - ID: {f.id}")
    print(f"    Email: {f.email}")
    print(f"    Password: {f.password}")
    print(f"    Name: {f.franchise_name}")
    print(f"    Active: {f.is_active}")
    print()

# Check Admins
admins = db.query(Admin).all()
print(f"\n👤 ADMINS ({len(admins)}):")
for a in admins:
    print(f"  - ID: {a.id}")
    print(f"    Email: {a.email}")
    print(f"    Password: {a.password}")
    print(f"    Name: {a.full_name}")
    print(f"    Active: {a.is_active}")
    print()

# Check Users
users = db.query(User).all()
print(f"\n👥 USERS ({len(users)}):")
for u in users[:3]:  # Show first 3 users
    print(f"  - ID: {u.id}")
    print(f"    MLD ID: {u.mld_id}")
    print(f"    Email: {u.email}")
    print(f"    Password: {u.password}")
    print(f"    Name: {u.full_name}")
    print(f"    Active: {u.is_active}")
    print()

print("=" * 50)

db.close()
