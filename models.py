from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum
import random
import string

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    FRANCHISE = "franchise"
    USER = "user"

class PlanStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    COMPLETED_WON = "completed_won"
    COMPLETED_FULL = "completed_full"
    SUSPENDED = "suspended"

class PaymentStatus(str, enum.Enum):
    PAID = "paid"
    PENDING = "pending"
    FAILED = "failed"

class DrawStatus(enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"

def generate_mld_id():
    return ''.join(random.choices(string.digits, k=6))

def generate_group_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def generate_invite_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_coupon_number(db):
    """Generate unique coupon number in format CPN-YYYY-NNNNN"""
    from datetime import datetime
    year = datetime.now().year
    
    # Get the last coupon number for this year
    last_coupon = db.query(Payment).filter(
        Payment.coupon_number.like(f'CPN-{year}-%')
    ).order_by(Payment.id.desc()).first()
    
    if last_coupon and last_coupon.coupon_number:
        # Extract number from last coupon (CPN-2024-00156 -> 156)
        try:
            last_number = int(last_coupon.coupon_number.split('-')[-1])
            next_number = last_number + 1
        except:
            next_number = 1
    else:
        next_number = 1
    
    return f"CPN-{year}-{next_number:05d}"

def slugify(text):
    """Convert text to URL-friendly slug"""
    if not text:
        return None
    text = text.lower()
    text = text.replace(' ', '-')
    text = ''.join(c for c in text if c.isalnum() or c == '-')
    return text

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    mld_id = Column(String(6), unique=True, index=True, default=generate_mld_id)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    full_name = Column(String)
    phone = Column(String)
    address = Column(Text, nullable=True)
    profile_photo = Column(String(500), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    
    # Two Wallets
    millance_rewards_wallet = Column(Float, default=0.0)
    savings_wallet = Column(Float, default=0.0)
    
    # Payment PIN (4-digit, plain text)
    pin = Column(String(4), nullable=True)
    
    # Referral tracking
    referred_by_franchise_id = Column(Integer, ForeignKey("franchises.id"), nullable=True)
    referred_by_group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    enrollments = relationship("Enrollment", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    referred_by_franchise = relationship("Franchise", foreign_keys=[referred_by_franchise_id], back_populates="referred_users")

class Franchise(Base):
    __tablename__ = "franchises"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    franchise_name = Column(String)
    franchise_code = Column(String, unique=True)
    franchise_slug = Column(String, unique=True)  # NEW: For invite URLs
    phone = Column(String)
    address = Column(Text)
    
    is_active = Column(Boolean, default=True)
    earnings_wallet = Column(Float, default=0.0)  # NEW: Referral earnings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prize_pools = relationship("PrizePool", back_populates="franchise")
    plans = relationship("Plan", back_populates="franchise")
    groups = relationship("Group", back_populates="franchise")
    referred_users = relationship("User", foreign_keys="[User.referred_by_franchise_id]", back_populates="referred_by_franchise")  # NEW

class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    full_name = Column(String)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PrizePool(Base):
    __tablename__ = "prize_pools"
    
    id = Column(Integer, primary_key=True, index=True)
    franchise_id = Column(Integer, ForeignKey("franchises.id"))
    name = Column(String)
    description = Column(Text)
    
    # Up to 15 prizes
    prize_1_name = Column(String)
    prize_1_amount = Column(Float)
    prize_2_name = Column(String)
    prize_2_amount = Column(Float)
    prize_3_name = Column(String)
    prize_3_amount = Column(Float)
    prize_4_name = Column(String)
    prize_4_amount = Column(Float)
    prize_5_name = Column(String)
    prize_5_amount = Column(Float)
    prize_6_name = Column(String)
    prize_6_amount = Column(Float)
    prize_7_name = Column(String)
    prize_7_amount = Column(Float)
    prize_8_name = Column(String)
    prize_8_amount = Column(Float)
    prize_9_name = Column(String)
    prize_9_amount = Column(Float)
    prize_10_name = Column(String)
    prize_10_amount = Column(Float)
    prize_11_name = Column(String)
    prize_11_amount = Column(Float)
    prize_12_name = Column(String)
    prize_12_amount = Column(Float)
    prize_13_name = Column(String)
    prize_13_amount = Column(Float)
    prize_14_name = Column(String)
    prize_14_amount = Column(Float)
    prize_15_name = Column(String)
    prize_15_amount = Column(Float)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    franchise = relationship("Franchise", back_populates="prize_pools")
    plans = relationship("Plan", back_populates="prize_pool")
    monthly_prizes = relationship("MonthlyPrize", back_populates="prize_pool", cascade="all, delete-orphan")
    
    @property
    def prizes(self):
        """Convert individual prize columns to a list of prize objects"""
        prizes_list = []
        for i in range(1, 16):
            name = getattr(self, f"prize_{i}_name", None)
            amount = getattr(self, f"prize_{i}_amount", None)
            if name or amount:
                prizes_list.append({"name": name, "amount": amount})
        return prizes_list


class MonthlyPrize(Base):
    __tablename__ = "monthly_prizes"
    
    id = Column(Integer, primary_key=True, index=True)
    prize_pool_id = Column(Integer, ForeignKey("prize_pools.id", ondelete="CASCADE"), nullable=False)
    month_number = Column(Integer, nullable=False)  # 1-15
    prize_rank = Column(Integer, nullable=False)  # 1st, 2nd, 3rd, etc.
    prize_name = Column(String(255), nullable=False)
    prize_amount = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)  # Number of winners for this prize
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prize_pool = relationship("PrizePool", back_populates="monthly_prizes")

class Plan(Base):
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True, index=True)
    franchise_id = Column(Integer, ForeignKey("franchises.id"))
    prize_pool_id = Column(Integer, ForeignKey("prize_pools.id"))
    
    name = Column(String)
    monthly_amount = Column(Float)
    duration_months = Column(Integer, default=11)
    max_members = Column(Integer)
    current_members = Column(Integer, default=0)
    status = Column(SQLEnum(PlanStatus), default=PlanStatus.ACTIVE)
    
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    franchise = relationship("Franchise", back_populates="plans")
    prize_pool = relationship("PrizePool", back_populates="plans")
    groups = relationship("Group", back_populates="plan")
    enrollments = relationship("Enrollment", back_populates="plan")

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    franchise_id = Column(Integer, ForeignKey("franchises.id"))
    plan_id = Column(Integer, ForeignKey("plans.id"))
    
    group_id = Column(String(4), unique=True, default=generate_group_id)
    invite_code = Column(String(20), unique=True, nullable=True)  # NEW: For referral links
    group_name = Column(String)
    max_members = Column(Integer)
    current_members = Column(Integer, default=0)
    status = Column(SQLEnum(PlanStatus), default=PlanStatus.ACTIVE)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    franchise = relationship("Franchise", back_populates="groups")
    plan = relationship("Plan", back_populates="groups")
    enrollments = relationship("Enrollment", back_populates="group")
    draws = relationship("Draw", back_populates="group")

class Enrollment(Base):
    __tablename__ = "enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_id = Column(Integer, ForeignKey("plans.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))
    
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    enrollment_date = Column(DateTime, default=datetime.utcnow)  # NEW: When user enrolled
    status = Column(SQLEnum(PlanStatus), default=PlanStatus.ACTIVE)
    months_paid = Column(Integer, default=0)
    total_paid = Column(Float, default=0.0)
    
    # Savings tracking
    savings_accumulated = Column(Float, default=0.0)
    
    # Draw eligibility
    is_eligible_for_draw = Column(Boolean, default=False)
    
    # Payment deadline policy (NEW enrollments only)
    is_legacy_policy = Column(Boolean, default=False)  # TRUE = old policy, FALSE = deadline policy
    consecutive_missed_payments = Column(Integer, default=0)  # Track consecutive misses
    auto_removed = Column(Boolean, default=False)  # TRUE if removed for non-payment
    removal_date = Column(DateTime, nullable=True)  # When user was auto-removed
    
    # Winner tracking
    has_won_prize = Column(Boolean, default=False)
    prize_won_month = Column(Integer, nullable=True)
    prize_name = Column(String(255), nullable=True)
    prize_amount = Column(Float, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    
    # Coupon system for prize redemption
    coupon_code = Column(String(50), unique=True, nullable=True)
    coupon_status = Column(String(20), default="pending")  # pending, redeemed, expired
    redeemed_at = Column(DateTime, nullable=True)
    redeemed_by_admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    redeemed_by_franchise_id = Column(Integer, ForeignKey("franchises.id"), nullable=True)
    
    # Referral commission tracking
    commission_rate = Column(Float, default=0.15)  # NEW: 15% commission for referred users
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="enrollments")
    plan = relationship("Plan", back_populates="enrollments")
    group = relationship("Group", back_populates="enrollments")
    payments = relationship("Payment", back_populates="enrollment")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"))
    
    amount = Column(Float)
    month = Column(String)
    month_number = Column(Integer, nullable=True)  # NEW: 1, 2, 3... for easy tracking
    payment_date = Column(DateTime)
    payment_deadline = Column(DateTime, nullable=True)  # NEW: Deadline for payment (5th of month)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Overdue tracking (NEW)
    is_overdue = Column(Boolean, default=False)
    days_overdue = Column(Integer, default=0)
    
    wallet_used = Column(String)  # millance_rewards_wallet or savings_wallet
    savings_credited = Column(Float, default=0.0)  # Amount added to savings
    transaction_id = Column(String)
    coupon_number = Column(String(20), nullable=True, index=True)  # NEW: Unique coupon per payment
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    enrollment = relationship("Enrollment", back_populates="payments")

class Draw(Base):
    __tablename__ = "draws"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    
    draw_date = Column(DateTime)
    month = Column(String)
    status = Column(SQLEnum(DrawStatus), default=DrawStatus.SCHEDULED)
    
    winner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    prize_name = Column(String)
    prize_amount = Column(Float)
    
    total_participants = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    group = relationship("Group", back_populates="draws")

class DrawSchedule(Base):
    __tablename__ = "draw_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    franchise_id = Column(Integer, ForeignKey("franchises.id"))
    
    month_number = Column(Integer)  # 1-11
    draw_date = Column(DateTime)
    draw_time = Column(String)  # Store as "HH:MM:SS"
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled
    
    conducted_by = Column(Integer, ForeignKey("franchises.id"), nullable=True)
    conducted_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class DrawResult(Base):
    __tablename__ = "draw_results"
    
    id = Column(Integer, primary_key=True, index=True)
    draw_schedule_id = Column(Integer, ForeignKey("draw_schedules.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    prize_name = Column(String)
    prize_amount = Column(Float)
    month_number = Column(Integer)
    
    won_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class Redemption(Base):
    __tablename__ = "redemptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"))
    
    amount = Column(Float)
    redemption_code = Column(String, unique=True)
    status = Column(String, default="pending")  # pending, used, expired
    
    valid_until = Column(DateTime)
    used_at = Column(DateTime, nullable=True)
    used_at_store = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    transaction_type = Column(String)  # deposit, withdrawal, payment, winning
    amount = Column(Float)
    wallet = Column(String)  # millance_rewards_wallet or savings_wallet
    description = Column(Text)
    
    balance_before = Column(Float)
    balance_after = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="transactions")

class FranchiseEarning(Base):
    __tablename__ = "franchise_earnings"
    
    id = Column(Integer, primary_key=True, index=True)
    franchise_id = Column(Integer, ForeignKey("franchises.id"))
    user_id = Column(Integer, ForeignKey("users.id"))  # Referred user who made payment
    payment_id = Column(Integer, ForeignKey("payments.id"))
    
    amount = Column(Float)  # Commission earned
    commission_rate = Column(Float)  # Rate used (0.15 = 15%)
    payment_amount = Column(Float)  # Original payment amount
    
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============== CASHFREE PAYMENT MODELS ==============

class CashfreePayment(Base):
    __tablename__ = "cashfree_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Cashfree Details
    order_id = Column(String(100), unique=True, nullable=False, index=True)
    cf_order_id = Column(String(100))
    payment_session_id = Column(String(200))
    cf_payment_id = Column(String(100))
    
    # Amount
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="INR")
    
    # Status Tracking
    order_status = Column(String(50), default="CREATED")  # CREATED, ACTIVE, PAID, EXPIRED, CANCELLED, FAILED
    payment_status = Column(String(50), default="PENDING")  # PENDING, SUCCESS, FAILED, USER_DROPPED
    
    # Verification
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    
    # Wallet Credit
    is_credited = Column(Boolean, default=False)
    credited_at = Column(DateTime, nullable=True)
    wallet_before = Column(Float, nullable=True)
    wallet_after = Column(Float, nullable=True)
    
    # Metadata
    payment_method = Column(String(50), nullable=True)
    bank_reference = Column(String(100), nullable=True)
    payment_time = Column(DateTime, nullable=True)
    
    # Error Tracking
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="cashfree_payments")
    reconciliation = relationship("PaymentReconciliation", back_populates="payment", uselist=False)


class PaymentReconciliation(Base):
    __tablename__ = "payment_reconciliation"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("cashfree_payments.id"))
    
    # Issue Type
    issue_type = Column(String(50), nullable=False)  # CREDIT_FAILED, WEBHOOK_MISSED, STATUS_MISMATCH, DUPLICATE
    
    # Cashfree vs Our Status
    cf_status = Column(String(50))
    our_status = Column(String(50))
    
    # Resolution
    is_resolved = Column(Boolean, default=False, index=True)
    resolved_by = Column(Integer, ForeignKey("admins.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Action Taken
    action_taken = Column(String(100), nullable=True)  # MANUAL_CREDIT, AUTO_RETRY, REFUND_INITIATED, MARKED_DUPLICATE
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    payment = relationship("CashfreePayment", back_populates="reconciliation")
    resolved_by_admin = relationship("Admin", foreign_keys=[resolved_by])


# Add relationships to existing models
User.cashfree_payments = relationship("CashfreePayment", back_populates="user")


# ============== COUPON COUNTER MODEL ==============

class CouponCounter(Base):
    __tablename__ = "coupon_counter"
    
    id = Column(Integer, primary_key=True, index=True)
    last_number = Column(Integer, default=0)  # Tracks last sequential coupon number
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
