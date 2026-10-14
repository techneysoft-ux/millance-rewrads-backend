from database import SessionLocal
from models import Admin, Franchise, User

def check_users():
    db = SessionLocal()
    
    try:
        # Check Admin
        admin = db.query(Admin).filter(Admin.email == "admin@millancefurniture.com").first()
        print("=" * 60)
        print("ADMIN CHECK")
        print("=" * 60)
        if admin:
            print(f"✓ Admin exists:")
            print(f"  ID: {admin.id}")
            print(f"  Email: {admin.email}")
            print(f"  Password: {admin.password}")
            print(f"  Full Name: {admin.full_name}")
            print(f"  Active: {admin.is_active}")
        else:
            print("✗ Admin NOT found!")
            print("Run: python init_db.py to create default users")
        
        print("\n" + "=" * 60)
        print("FRANCHISE CHECK")
        print("=" * 60)
        franchise = db.query(Franchise).filter(Franchise.email == "franchise@millancefurniture.com").first()
        if franchise:
            print(f"✓ Franchise exists:")
            print(f"  ID: {franchise.id}")
            print(f"  Email: {franchise.email}")
            print(f"  Password: {franchise.password}")
            print(f"  Name: {franchise.franchise_name}")
            print(f"  Active: {franchise.is_active}")
        else:
            print("✗ Franchise NOT found!")
        
        print("\n" + "=" * 60)
        print("USER CHECK")
        print("=" * 60)
        user = db.query(User).filter(User.email == "user@millancefurniture.com").first()
        if user:
            print(f"✓ User exists:")
            print(f"  ID: {user.id}")
            print(f"  Email: {user.email}")
            print(f"  Password: {user.password}")
            print(f"  MLD ID: {user.mld_id}")
            print(f"  Full Name: {user.full_name}")
            print(f"  Active: {user.is_active}")
        else:
            print("✗ User NOT found!")
        
        print("\n" + "=" * 60)
        print("ALL USERS COUNT")
        print("=" * 60)
        admin_count = db.query(Admin).count()
        franchise_count = db.query(Franchise).count()
        user_count = db.query(User).count()
        print(f"Admins: {admin_count}")
        print(f"Franchises: {franchise_count}")
        print(f"Users: {user_count}")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()
