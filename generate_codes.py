"""
Generate franchise slugs and group invite codes
"""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import random
import string

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://millancerewards:123456@localhost/millancerewards")

def generate_group_code():
    """Generate unique 6-character group invite code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(6))

def slugify(text):
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = text.replace(' ', '-')
    text = ''.join(c for c in text if c.isalnum() or c == '-')
    return text

def generate_codes():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("=" * 60)
        print("GENERATING FRANCHISE SLUGS AND GROUP CODES")
        print("=" * 60)
        
        # 1. Generate franchise slugs
        print("\n1. Generating franchise slugs...")
        franchises = conn.execute(text("SELECT id, franchise_name FROM franchises"))
        
        for franchise in franchises:
            slug = slugify(franchise.franchise_name)
            # Add number if slug exists
            existing = conn.execute(
                text("SELECT id FROM franchises WHERE franchise_slug = :slug AND id != :id"),
                {"slug": slug, "id": franchise.id}
            ).first()
            
            if existing:
                slug = f"{slug}-{franchise.id}"
            
            conn.execute(
                text("UPDATE franchises SET franchise_slug = :slug WHERE id = :id"),
                {"slug": slug, "id": franchise.id}
            )
            print(f"   ✅ {franchise.franchise_name} → {slug}")
        
        conn.commit()
        
        # 2. Generate group invite codes
        print("\n2. Generating group invite codes...")
        groups = conn.execute(text("SELECT id, group_name FROM groups"))
        
        used_codes = set()
        for group in groups:
            # Generate unique code
            while True:
                code = generate_group_code()
                if code not in used_codes:
                    used_codes.add(code)
                    break
            
            conn.execute(
                text("UPDATE groups SET invite_code = :code WHERE id = :id"),
                {"code": code, "id": group.id}
            )
            print(f"   ✅ {group.group_name} → {code}")
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("CODE GENERATION COMPLETED")
        print("=" * 60)
        
        # Show sample invite links
        print("\n📋 Sample Invite Links:")
        result = conn.execute(text("""
            SELECT 
                f.franchise_slug,
                g.invite_code,
                g.group_name
            FROM groups g
            JOIN franchises f ON g.franchise_id = f.id
            LIMIT 5
        """))
        
        for row in result:
            print(f"   millancefurniture.com/{row.franchise_slug}/{row.invite_code} → {row.group_name}")

if __name__ == "__main__":
    generate_codes()
