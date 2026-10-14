"""
Create payment tables for Cashfree integration
Run this file to create all payment-related tables
"""

from sqlalchemy import create_engine, text
from database import get_db, engine
import os
from dotenv import load_dotenv

load_dotenv()

def create_payment_tables():
    """Create all payment-related tables"""
    
    print("🔧 Creating payment tables...")
    
    # SQL for cashfree_payments table
    cashfree_payments_sql = """
    CREATE TABLE IF NOT EXISTS cashfree_payments (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) NOT NULL,
        
        -- Cashfree Details
        order_id VARCHAR(100) UNIQUE NOT NULL,
        cf_order_id VARCHAR(100),
        payment_session_id VARCHAR(200),
        cf_payment_id VARCHAR(100),
        
        -- Amount
        amount DECIMAL(10, 2) NOT NULL,
        currency VARCHAR(3) DEFAULT 'INR',
        
        -- Status Tracking
        order_status VARCHAR(50) DEFAULT 'CREATED',
        payment_status VARCHAR(50) DEFAULT 'PENDING',
        
        -- Verification
        is_verified BOOLEAN DEFAULT FALSE,
        verified_at TIMESTAMP,
        
        -- Wallet Credit
        is_credited BOOLEAN DEFAULT FALSE,
        credited_at TIMESTAMP,
        wallet_before DECIMAL(10, 2),
        wallet_after DECIMAL(10, 2),
        
        -- Metadata
        payment_method VARCHAR(50),
        bank_reference VARCHAR(100),
        payment_time TIMESTAMP,
        
        -- Error Tracking
        error_code VARCHAR(50),
        error_message TEXT,
        retry_count INTEGER DEFAULT 0,
        
        -- Timestamps
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_cf_order_id ON cashfree_payments(order_id);
    CREATE INDEX IF NOT EXISTS idx_cf_user_id ON cashfree_payments(user_id);
    CREATE INDEX IF NOT EXISTS idx_cf_payment_status ON cashfree_payments(payment_status);
    CREATE INDEX IF NOT EXISTS idx_cf_created_at ON cashfree_payments(created_at DESC);
    """
    
    # SQL for payment_reconciliation table
    reconciliation_sql = """
    CREATE TABLE IF NOT EXISTS payment_reconciliation (
        id SERIAL PRIMARY KEY,
        payment_id INTEGER REFERENCES cashfree_payments(id),
        
        -- Issue Type
        issue_type VARCHAR(50) NOT NULL,
        
        -- Cashfree vs Our Status
        cf_status VARCHAR(50),
        our_status VARCHAR(50),
        
        -- Resolution
        is_resolved BOOLEAN DEFAULT FALSE,
        resolved_by INTEGER REFERENCES admins(id),
        resolved_at TIMESTAMP,
        resolution_notes TEXT,
        
        -- Action Taken
        action_taken VARCHAR(100),
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_reconciliation_unresolved ON payment_reconciliation(is_resolved, created_at);
    CREATE INDEX IF NOT EXISTS idx_reconciliation_payment ON payment_reconciliation(payment_id);
    """
    
    try:
        with engine.connect() as conn:
            # Create cashfree_payments table
            print("  ✓ Creating cashfree_payments table...")
            conn.execute(text(cashfree_payments_sql))
            conn.commit()
            
            # Create payment_reconciliation table
            print("  ✓ Creating payment_reconciliation table...")
            conn.execute(text(reconciliation_sql))
            conn.commit()
            
        print("✅ All payment tables created successfully!")
        
        # Verify tables exist
        verify_sql = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('cashfree_payments', 'payment_reconciliation')
        ORDER BY table_name;
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(verify_sql))
            tables = [row[0] for row in result]
            print(f"\n📊 Tables created: {', '.join(tables)}")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    create_payment_tables()
