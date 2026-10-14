from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from models import UserRole, PlanStatus as ModelPlanStatus, PaymentStatus as ModelPaymentStatus

# Re-export for backward compatibility
PlanStatus = ModelPlanStatus
PaymentStatus = ModelPaymentStatus

# Auth Schemas
class LoginRequest(BaseModel):
    identifier: str  # Email or MLD ID
    password: str
    role: Optional[UserRole] = UserRole.USER

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: UserRole
    user_data: dict

# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str

class UserResponse(BaseModel):
    id: int
    mld_id: str
    email: str
    full_name: str
    phone: str
    address: Optional[str]
    profile_photo: Optional[str] = None
    millance_rewards_wallet: float
    savings_wallet: float
    role: UserRole
    is_active: bool
    created_at: datetime
    password: Optional[str] = None  # Include password for admin view
    
    class Config:
        from_attributes = True

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

# Franchise Schemas
class FranchiseCreate(BaseModel):
    email: EmailStr
    password: str
    franchise_name: str
    franchise_code: str
    phone: Optional[str] = None
    address: Optional[str] = None

class FranchiseResponse(BaseModel):
    id: int
    email: str
    franchise_name: str
    franchise_code: str
    phone: str
    address: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Prize Pool Schemas
class PrizeItem(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None

class PrizePoolCreate(BaseModel):
    name: str
    description: Optional[str] = None
    prizes: List[PrizeItem]  # Up to 15 prizes

class PrizePoolResponse(BaseModel):
    id: int
    franchise_id: int
    name: str
    description: Optional[str]
    prizes: List[PrizeItem]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Plan Schemas
class PlanCreate(BaseModel):
    prize_pool_id: int
    name: str
    monthly_amount: float
    duration_months: int = 11
    max_members: int
    description: Optional[str] = None

class PlanResponse(BaseModel):
    id: int
    franchise_id: int
    name: str
    monthly_amount: float
    duration_months: int
    max_members: int
    current_members: int
    status: PlanStatus
    created_at: datetime
    
    class Config:
        from_attributes = True

# Group Schemas
class GroupCreate(BaseModel):
    plan_id: int
    group_name: str
    max_members: int

class GroupResponse(BaseModel):
    id: int
    group_id: str
    invite_code: Optional[str]
    group_name: str
    plan_id: int
    max_members: int
    current_members: int
    status: PlanStatus
    created_at: datetime
    
    class Config:
        from_attributes = True

# Enrollment Schemas
class EnrollmentCreate(BaseModel):
    plan_id: int
    group_id: int
    wallet_type: str  # millance_rewards_wallet or savings_wallet

class EnrollmentResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int
    group_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: PlanStatus
    months_paid: int
    total_paid: float
    savings_accumulated: Optional[float] = 0.0  # Savings earned from payments
    latest_payment_coupon: Optional[str] = None  # NEW: Latest payment coupon code
    group_enrollment: Optional[dict] = None  # NEW: Group enrollment progress data
    
    class Config:
        from_attributes = True

# Payment Schemas
class PaymentCreate(BaseModel):
    enrollment_id: int
    wallet_type: str  # millance_rewards_wallet or savings_wallet
    month: str

class PaymentResponse(BaseModel):
    id: int
    user_id: int
    enrollment_id: int
    amount: float
    month: str
    status: PaymentStatus
    payment_date: Optional[datetime]
    wallet_used: str
    coupon_number: Optional[str] = None  # NEW: Coupon number
    
    class Config:
        from_attributes = True

# Transaction Schemas
class TransactionCreate(BaseModel):
    transaction_type: str
    amount: float
    wallet: str
    description: Optional[str] = None

class TransactionResponse(BaseModel):
    id: int
    user_id: int
    transaction_type: str
    amount: float
    wallet: str
    description: Optional[str]
    balance_before: float
    balance_after: float
    created_at: datetime
    
    class Config:
        from_attributes = True

# Wallet Schemas
class WalletDepositRequest(BaseModel):
    wallet_type: str  # millance_rewards_wallet or savings_wallet
    amount: float

class WalletResponse(BaseModel):
    millance_rewards_wallet: float
    savings_wallet: float


# Draw Schedule Schemas
class DrawScheduleCreate(BaseModel):
    group_id: int
    month_number: int
    draw_date: str  # YYYY-MM-DD
    draw_time: str  # HH:MM:SS

class DrawScheduleResponse(BaseModel):
    id: int
    group_id: int
    month_number: int
    draw_date: datetime
    draw_time: str
    status: str
    conducted_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Draw Result Schemas
class DrawResultResponse(BaseModel):
    id: int
    draw_schedule_id: int
    group_id: int
    user_id: int
    prize_name: str
    prize_amount: float
    month_number: int
    won_at: datetime
    
    class Config:
        from_attributes = True

# Redemption Schemas
class RedemptionCreate(BaseModel):
    enrollment_id: int
    amount: float

class RedemptionResponse(BaseModel):
    id: int
    user_id: int
    enrollment_id: int
    amount: float
    redemption_code: str
    status: str
    valid_until: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

# Enhanced Enrollment Response
class EnrollmentDetailResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int
    group_id: int
    start_date: datetime
    end_date: datetime
    status: PlanStatus
    months_paid: int
    total_paid: float
    savings_accumulated: float
    is_eligible_for_draw: bool
    has_won_prize: bool
    prize_won_month: Optional[int]
    prize_name: Optional[str]
    prize_amount: Optional[float]
    ended_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# PIN Schemas
class PINSetRequest(BaseModel):
    pin: str  # 4-digit string

class PINChangeRequest(BaseModel):
    new_pin: str  # 4-digit string

class PINVerifyRequest(BaseModel):
    mld_id: str
    pin: str

# Wallet Payment Schemas
class WalletPaymentRequest(BaseModel):
    mld_id: str
    amount: float
    pin: str
    wallet_type: str  # "millance_rewards_wallet" or "savings_wallet"

class WalletPaymentAuthRequest(BaseModel):
    amount: float
    pin: str
    wallet_type: str  # "millance_rewards_wallet" or "savings_wallet"

class WalletPaymentResponse(BaseModel):
    success: bool
    message: str
    transaction_id: int
    new_balance: float
    amount_paid: float

# Password Change Schema
class PasswordChangeRequest(BaseModel):
    new_password: str

# Balance Management Schemas
class BalanceUpdateRequest(BaseModel):
    amount: float
    wallet_type: str  # "millance_rewards_wallet" or "savings_wallet"

class BalanceUpdateResponse(BaseModel):
    message: str
    user_id: int
    wallet_type: str
    amount_changed: float
    new_balance: float


# Referral System Schemas
class InviteLinkValidation(BaseModel):
    franchise_name: str
    franchise_slug: str
    group_name: str
    group_id: str
    invite_code: str
    plan_name: str
    monthly_amount: float
    duration_months: int
    max_members: int
    current_members: int
    prizes: List[PrizeItem]

class RegisterWithInviteRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str
    franchise_slug: str
    invite_code: str

class ReferralUserResponse(BaseModel):
    user_id: int
    mld_id: str
    full_name: str
    email: str
    phone: str
    group_name: str
    monthly_amount: float
    duration_months: int
    payments_made: int
    total_payments: int
    total_paid: float
    commission_earned: float

class ReferralListResponse(BaseModel):
    users: List[ReferralUserResponse]
    total_users: int
    page: int
    total_pages: int

class ReferralUserDetailsResponse(BaseModel):
    user_id: int
    mld_id: str
    full_name: str
    email: str
    phone: str
    group_name: str
    monthly_amount: float
    duration_months: int
    payments_made: int
    total_payments: int
    total_paid: float
    commission_earned: float
    payments: List[dict]

class FranchiseEarningsResponse(BaseModel):
    total_earnings: float
    total_referred_users: int
    active_referred_users: int
    earnings_wallet_balance: float


# ============== CASHFREE PAYMENT SCHEMAS ==============

class PaymentOrderCreate(BaseModel):
    amount: float
    
    @validator('amount')
    def validate_amount(cls, v):
        if v < 1:
            raise ValueError('Amount must be at least ₹1')
        if v > 10000:
            raise ValueError('Amount cannot exceed ₹10,000')
        return round(v, 2)


class PaymentOrderResponse(BaseModel):
    success: bool
    order_id: str
    payment_session_id: str
    amount: float
    
    class Config:
        from_attributes = True


class PaymentVerifyRequest(BaseModel):
    order_id: str


class PaymentVerifyResponse(BaseModel):
    success: bool
    payment_status: str
    amount: float
    wallet_credited: bool = False
    new_balance: float = None
    transaction_id: int = None
    error: str = None
    
    class Config:
        from_attributes = True


class CashfreePaymentResponse(BaseModel):
    id: int
    order_id: str
    amount: float
    currency: str
    order_status: str
    payment_status: str
    payment_method: str = None
    is_credited: bool
    created_at: datetime
    payment_time: datetime = None
    
    class Config:
        from_attributes = True


class PaymentHistoryResponse(BaseModel):
    payments: List[CashfreePaymentResponse]
    total: int
    
    class Config:
        from_attributes = True
