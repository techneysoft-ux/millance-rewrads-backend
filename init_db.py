from database import engine, SessionLocal
from models import Base, User, Franchise, Admin, UserRole

def init_database():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if default users exist
        admin_exists = db.query(Admin).filter(Admin.email == "admin@millancefurniture.com").first()
        franchise_exists = db.query(Franchise).filter(Franchise.email == "franchise@millancefurniture.com").first()
        user_exists = db.query(User).filter(User.email == "user@millancefurniture.com").first()
        
        # Create default admin
        if not admin_exists:
            admin = Admin(
                email="admin@millancefurniture.com",
                password="millance",  # Plain text password
                full_name="System Admin",
                is_active=True
            )
            db.add(admin)
            print("✓ Created default admin: admin@millancefurniture.com / millance")
        
        # Create default franchise
        if not franchise_exists:
            franchise = Franchise(
                email="franchise@millancefurniture.com",
                password="millance",  # Plain text password
                franchise_name="Main Franchise",
                franchise_code="MAIN001",
                phone="+91 9876543210",
                address="Main Branch Address",
                is_active=True
            )
            db.add(franchise)
            print("✓ Created default franchise: franchise@millancefurniture.com / millance")
        
        # Create default user
        if not user_exists:
            user = User(
                email="user@millancefurniture.com",
                password="millance",  # Plain text password
                full_name="Test User",
                phone="+91 9876543210",
                role=UserRole.USER,
                millance_rewards_wallet=10000.0,
                savings_wallet=5000.0,
                is_active=True
            )
            db.add(user)
            print("✓ Created default user: user@millancefurniture.com / millance")
            print(f"  MLD ID will be generated: {user.mld_id if hasattr(user, 'mld_id') else 'auto-generated'}")
        
        db.commit()
        print("\n✓ Database initialized successfully!")
        print(f"\nDefault Credentials:")
        print(f"Admin    : admin@millancefurniture.com / millance")
        print(f"Franchise: franchise@millancefurniture.com / millance")
        print(f"User     : user@millancefurniture.com / millance")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing database...")
    init_database()
