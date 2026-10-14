"""
Create franchise_earnings table
"""
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://millancerewards:123456@localhost/millancerewards")

def create_table():
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("Creating franchise_earnings table...")
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS franchise_earnings (
                id SERIAL PRIMARY KEY,
                franchise_id INTEGER REFERENCES franchises(id),
                user_id INTEGER REFERENCES users(id),
                payment_id INTEGER REFERENCES payments(id),
                amount FLOAT NOT NULL,
                commission_rate FLOAT NOT NULL,
                payment_amount FLOAT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.commit()
        
        print("✅ franchise_earnings table created")

if __name__ == "__main__":
    create_table()
