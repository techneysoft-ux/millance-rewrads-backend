from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import os
import uuid
import shutil
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

from database import get_db, engine
from models import Base, User, Franchise, Admin, PrizePool, Plan, Group, Enrollment, Payment, Transaction, Draw, DrawSchedule, DrawResult, CouponCounter, MonthlyPrize
from models import UserRole, PlanStatus, PaymentStatus, DrawStatus
from schemas import *
from auth import authenticate_user, create_access_token, get_current_user, require_role, require_any_role

load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "/var/www/rewards/uploads/profile_photos"
UPLOAD_BASE = "/var/www/rewards/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Millance Rewards API", version="1.0.0")

# Mount static files for profile photos (only if directory exists)
if os.path.exists(UPLOAD_BASE):
    app.mount("/uploads", StaticFiles(directory=UPLOAD_BASE), name="uploads")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== HELPER FUNCTIONS ==============

def calculate_group_enrollment_status(group):
    """
    Calculate group enrollment status with progress information
    Returns: dict with current_members, max_members, percentage, etc.
    """
    if not group:
        return None
    
    current = group.current_members or 0
    max_members = group.max_members or 0
    
    if max_members == 0:
        return {
            "current_members": current,
            "max_members": 0,
            "percentage": 0,
            "spots_remaining": 0,
            "status": "unlimited",
            "status_color": "blue",
            "status_message": "Unlimited enrollment"
        }
    
    percentage = (current / max_members * 100) if max_members > 0 else 0
    spots_remaining = max(0, max_members - current)
    
    # Determine status
    if current >= max_members:
        status = "full"
        status_color = "purple"
        status_message = "Group is full"
    elif percentage >= 80:
        status = "almost_full"
        status_color = "orange"
        status_message = f"Only {spots_remaining} spot{'s' if spots_remaining != 1 else ''} left!"
    elif percentage >= 50:
        status = "filling"
        status_color = "yellow"
        status_message = f"{spots_remaining} spots available"
    else:
        status = "open"
        status_color = "green"
        status_message = f"{spots_remaining} spots available"
    
    return {
        "current_members": current,
        "max_members": max_members,
        "percentage": round(percentage, 1),
        "spots_remaining": spots_remaining,
        "status": status,
        "status_color": status_color,
        "status_message": status_message
    }

# ============== AUTH ROUTES ==============

@app.get("/api/test/group-enrollment")
def test_group_enrollment(db: Session = Depends(get_db)):
    """Test endpoint to verify group enrollment calculation"""
    group = db.query(Group).first()
    if not group:
        return {"error": "No groups found"}
    
    status = calculate_group_enrollment_status(group)
    return {
        "group_id": group.id,
        "group_name": group.group_name,
        "enrollment_status": status
    }

@app.post("/api/auth/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data.identifier, login_data.password, login_data.role)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/MLD ID or password"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": login_data.identifier, "role": login_data.role.value}
    )
    
    # Prepare user data
    if login_data.role == UserRole.ADMIN:
        user_data = {"id": user.id, "email": user.email, "full_name": user.full_name}
    elif login_data.role == UserRole.FRANCHISE:
        user_data = {
            "id": user.id, 
            "email": user.email, 
            "franchise_name": user.franchise_name,
            "franchise_slug": user.franchise_slug
        }
    else:
        user_data = {
            "id": user.id,
            "mld_id": user.mld_id,
            "email": user.email,
            "full_name": user.full_name,
            "millance_rewards_wallet": user.millance_rewards_wallet,
            "savings_wallet": user.savings_wallet
        }
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": login_data.role,
        "user_data": user_data
    }

@app.post("/api/auth/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if email exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user (plain text password)
    new_user = User(
        email=user_data.email,
        password=user_data.password,  # Store plain text
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=UserRole.USER,
        millance_rewards_wallet=0.0,
        savings_wallet=0.0
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

# ============== USER ROUTES ==============

@app.get("/api/users/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@app.put("/api/users/me", response_model=UserResponse)
def update_user_profile(
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    # Update only provided fields
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name
    if update_data.email is not None:
        # Check if email already exists for another user
        existing = db.query(User).filter(
            User.email == update_data.email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = update_data.email
    if update_data.phone is not None:
        current_user.phone = update_data.phone
    if update_data.address is not None:
        current_user.address = update_data.address
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user

@app.post("/api/users/profile-photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and compress profile photo"""
    
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file
        contents = await file.read()
        
        # Validate file size (max 20MB)
        if len(contents) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size must be less than 20MB")
        
        # Open image with PIL
        image = Image.open(BytesIO(contents))
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        
        # Resize if too large (max 800x800)
        max_size = 800
        if image.width > max_size or image.height > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Generate unique filename
        file_ext = 'jpg'
        filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        print(f"📸 Saving image to: {file_path}")
        
        # Save compressed image
        image.save(file_path, 'JPEG', quality=85, optimize=True)
        
        print(f"✅ Image saved successfully")
        
        # Delete old photo if exists
        if current_user.profile_photo:
            old_path = current_user.profile_photo.replace('/uploads/', '/var/www/rewards/uploads/')
            if os.path.exists(old_path):
                os.remove(old_path)
                print(f"🗑️ Deleted old photo: {old_path}")
        
        # Update database
        current_user.profile_photo = f"/uploads/profile_photos/{filename}"
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        print(f"✅ Database updated with photo path: {current_user.profile_photo}")
        
        return {
            "success": True,
            "profile_photo": current_user.profile_photo,
            "message": "Profile photo uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error uploading photo: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")

@app.get("/api/users/wallet")
def get_wallet_balance(current_user: User = Depends(get_current_user)):
    return {
        "millance_rewards_wallet": current_user.millance_rewards_wallet,
        "savings_wallet": current_user.savings_wallet
    }

@app.post("/api/users/wallet/deposit")
def deposit_to_wallet(
    deposit_data: WalletDepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if deposit_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Get balance before
    if deposit_data.wallet_type == "millance_rewards_wallet":
        balance_before = current_user.millance_rewards_wallet
        current_user.millance_rewards_wallet += deposit_data.amount
        balance_after = current_user.millance_rewards_wallet
    elif deposit_data.wallet_type == "savings_wallet":
        balance_before = current_user.savings_wallet
        current_user.savings_wallet += deposit_data.amount
        balance_after = current_user.savings_wallet
    else:
        raise HTTPException(status_code=400, detail="Invalid wallet type")
    
    # Create transaction record
    transaction = Transaction(
        user_id=current_user.id,
        transaction_type="deposit",
        amount=deposit_data.amount,
        wallet=deposit_data.wallet_type,
        description=f"Deposit to {deposit_data.wallet_type}",
        balance_before=balance_before,
        balance_after=balance_after
    )
    db.add(transaction)
    db.commit()
    
    return {
        "message": "Deposit successful",
        "wallet": deposit_data.wallet_type,
        "amount": deposit_data.amount,
        "new_balance": balance_after
    }

@app.get("/api/users/transactions", response_model=List[TransactionResponse])
def get_user_transactions(
    transaction_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user transactions with optional filter"""
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    
    # Filter by transaction type if provided
    if transaction_type:
        if transaction_type == "plans":
            query = query.filter(Transaction.transaction_type.in_(["payment", "savings_credit"]))
        elif transaction_type == "store":
            query = query.filter(Transaction.transaction_type == "store_purchase")
        elif transaction_type == "redemptions":
            query = query.filter(Transaction.transaction_type == "redemption")
        # "all" or any other value returns everything
    
    transactions = query.order_by(Transaction.created_at.desc()).limit(100).all()
    return transactions

@app.get("/api/users/dashboard")
def get_user_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard data for user
    Returns: user info, groups/enrollments, wallet, next draw, prizes
    """
    # Get user's enrollments with group and plan info
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.status.in_([PlanStatus.ACTIVE, PlanStatus.COMPLETED])
    ).all()
    
    groups_data = []
    for enrollment in enrollments:
        group = db.query(Group).filter(Group.id == enrollment.group_id).first()
        plan = db.query(Plan).filter(Plan.id == enrollment.plan_id).first()
        
        if group and plan:
            groups_data.append({
                "enrollment_id": enrollment.id,
                "group_id": group.id,
                "group_name": group.group_name,
                "group_code": group.group_id,  # 4-digit code like "ABCD"
                "months_paid": enrollment.months_paid,
                "total_months": plan.duration_months,
                "current_month": enrollment.months_paid + 1,  # Next month to pay
                "monthly_amount": plan.monthly_amount,
                "total_paid": enrollment.total_paid,
                "status": enrollment.status.value
            })
    
    # Get next upcoming draw
    next_draw = db.query(Draw).filter(
        Draw.draw_date >= datetime.now().date(),
        Draw.status == DrawStatus.SCHEDULED
    ).order_by(Draw.draw_date).first()
    
    next_draw_data = None
    if next_draw:
        # Get draw time (default to 19:00 if not set)
        draw_time = getattr(next_draw, 'draw_time', '19:00')
        
        # Calculate countdown
        try:
            draw_datetime = datetime.combine(
                next_draw.draw_date,
                datetime.strptime(draw_time, "%H:%M").time()
            )
            diff = draw_datetime - datetime.now()
            
            next_draw_data = {
                "draw_id": next_draw.id,
                "draw_date": next_draw.draw_date.isoformat(),
                "draw_time": draw_time,
                "countdown": {
                    "days": max(0, diff.days),
                    "hours": max(0, diff.seconds // 3600),
                    "minutes": max(0, (diff.seconds % 3600) // 60),
                    "seconds": max(0, diff.seconds % 60)
                }
            }
        except Exception as e:
            print(f"Error calculating countdown: {e}")
            next_draw_data = {
                "draw_id": next_draw.id,
                "draw_date": next_draw.draw_date.isoformat(),
                "draw_time": draw_time,
                "countdown": {"days": 0, "hours": 0, "minutes": 0, "seconds": 0}
            }
    
    # Get prizes from first enrollment's plan (current month prizes)
    current_month_prizes = []
    if enrollments:
        first_enrollment = enrollments[0]
        plan = db.query(Plan).filter(Plan.id == first_enrollment.plan_id).first()
        
        if plan:
            prize_pool = db.query(PrizePool).filter(PrizePool.id == plan.prize_pool_id).first()
            
            if prize_pool:
                for i in range(1, 16):
                    prize_name = getattr(prize_pool, f"prize_{i}_name", None)
                    prize_amount = getattr(prize_pool, f"prize_{i}_amount", None)
                    
                    # Try to get image URL (may not exist in old data)
                    prize_image = None
                    if hasattr(prize_pool, f"prize_{i}_image_url"):
                        prize_image = getattr(prize_pool, f"prize_{i}_image_url", None)
                    
                    # Try to get winner count (may not exist in old data)
                    winner_count = 1
                    if hasattr(prize_pool, f"prize_{i}_winner_count"):
                        winner_count = getattr(prize_pool, f"prize_{i}_winner_count", 1) or 1
                    
                    if prize_name:
                        current_month_prizes.append({
                            "id": f"PRIZE-{i}",
                            "name": prize_name,
                            "image": prize_image or "https://via.placeholder.com/300x300.png?text=Prize",
                            "quantity": winner_count,
                            "winners": winner_count
                        })
    
    return {
        "user": {
            "name": current_user.full_name,
            "memberId": current_user.mld_id,
            "avatar_url": None
        },
        "groups": groups_data,
        "wallet": {
            "millance_rewards_wallet": current_user.millance_rewards_wallet,
            "savings_wallet": current_user.savings_wallet
        },
        "next_draw": next_draw_data,
        "current_month_prizes": current_month_prizes
    }

# ============== FRANCHISE ROUTES ==============

@app.get("/api/franchise/me")
def get_current_franchise_info(
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
):
    """Get current franchise info"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "franchise_name": current_user.franchise_name,
        "franchise_code": current_user.franchise_code,
        "franchise_slug": current_user.franchise_slug,
        "earnings_wallet": current_user.earnings_wallet,
        "phone": current_user.phone,
        "address": current_user.address
    }

@app.post("/api/franchise/prize-pools", response_model=PrizePoolResponse)
def create_prize_pool(
    prize_pool_data: PrizePoolCreate,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    if len(prize_pool_data.prizes) > 15:
        raise HTTPException(status_code=400, detail="Maximum 15 prizes allowed")
    
    # Create prize pool
    new_pool = PrizePool(
        franchise_id=current_user.id,
        name=prize_pool_data.name,
        description=prize_pool_data.description
    )
    
    # Add prizes
    for i, prize in enumerate(prize_pool_data.prizes, 1):
        if prize.name and prize.amount:
            setattr(new_pool, f"prize_{i}_name", prize.name)
            setattr(new_pool, f"prize_{i}_amount", prize.amount)
    
    db.add(new_pool)
    db.commit()
    db.refresh(new_pool)
    
    return new_pool

@app.get("/api/franchise/prize-pools", response_model=List[PrizePoolResponse])
def get_franchise_prize_pools(
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    pools = db.query(PrizePool).filter(
        PrizePool.franchise_id == current_user.id
    ).all()
    return pools

@app.post("/api/franchise/plans", response_model=PlanResponse)
def create_plan(
    plan_data: PlanCreate,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    # Verify prize pool exists and belongs to franchise
    prize_pool = db.query(PrizePool).filter(
        PrizePool.id == plan_data.prize_pool_id,
        PrizePool.franchise_id == current_user.id
    ).first()
    
    if not prize_pool:
        raise HTTPException(status_code=404, detail="Prize pool not found")
    
    # Create plan
    new_plan = Plan(
        franchise_id=current_user.id,
        prize_pool_id=plan_data.prize_pool_id,
        name=plan_data.name,
        monthly_amount=plan_data.monthly_amount,
        duration_months=plan_data.duration_months,
        max_members=plan_data.max_members,
        description=plan_data.description
    )
    
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    
    return new_plan

@app.post("/api/franchise/groups", response_model=GroupResponse)
def create_group(
    group_data: GroupCreate,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    # Verify plan exists and belongs to franchise
    plan = db.query(Plan).filter(
        Plan.id == group_data.plan_id,
        Plan.franchise_id == current_user.id
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Auto-generate unique invite code
    from models import generate_invite_code
    invite_code = generate_invite_code()
    
    # Ensure uniqueness
    while db.query(Group).filter(Group.invite_code == invite_code).first():
        invite_code = generate_invite_code()
    
    # Create group with random group_id and invite_code
    new_group = Group(
        franchise_id=current_user.id,
        plan_id=group_data.plan_id,
        group_name=group_data.group_name,
        max_members=group_data.max_members,
        invite_code=invite_code
    )
    
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    
    return new_group

@app.get("/api/franchise/groups", response_model=List[GroupResponse])
def get_franchise_groups(
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    groups = db.query(Group).filter(
        Group.franchise_id == current_user.id
    ).all()
    return groups

@app.get("/api/franchise/groups/{group_id}/details")
def get_franchise_group_details(
    group_id: int,
    current_user = Depends(require_any_role([UserRole.FRANCHISE, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific group including all members and winners - accessible by franchise and admin"""
    from models import DrawSchedule, DrawResult, Admin
    
    # Get group based on user role
    if isinstance(current_user, Admin):
        # Admin can view any group
        group = db.query(Group).filter(Group.id == group_id).first()
    else:
        # Franchise can only view their own groups
        group = db.query(Group).filter(
            Group.id == group_id,
            Group.franchise_id == current_user.id
        ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Get franchise details for referral link
    franchise = db.query(Franchise).filter(Franchise.id == group.franchise_id).first()
    
    # Get plan details
    plan = db.query(Plan).filter(Plan.id == group.plan_id).first()
    
    # Get prize pool
    prize_pool = None
    if plan:
        prize_pool = db.query(PrizePool).filter(PrizePool.id == plan.prize_pool_id).first()
    
    # Get all enrollments for this group
    enrollments = db.query(Enrollment).filter(
        Enrollment.group_id == group.id
    ).all()
    
    # Get all draw results for this group
    draw_schedules = db.query(DrawSchedule).filter(
        DrawSchedule.group_id == group.id,
        DrawSchedule.status == "completed"
    ).order_by(DrawSchedule.month_number).all()
    
    # Build winners by month
    winners_by_month = {}
    for draw in draw_schedules:
        draw_result = db.query(DrawResult).filter(
            DrawResult.draw_schedule_id == draw.id
        ).first()
        
        if draw_result:
            winner = db.query(User).filter(User.id == draw_result.user_id).first()
            winners_by_month[draw.month_number] = {
                "month_number": draw.month_number,
                "winner": {
                    "id": winner.id,
                    "mld_id": winner.mld_id,
                    "full_name": winner.full_name,
                    "email": winner.email,
                    "phone": winner.phone,
                    "profile_photo": winner.profile_photo
                } if winner else None,
                "prize_name": draw_result.prize_name,
                "prize_amount": draw_result.prize_amount,
                "draw_date": draw.draw_date,
                "conducted_at": draw.conducted_at
            }
    
    # Build member list with details
    members = []
    total_paid = 0
    active_members = 0
    pending_members = 0
    completed_members = 0
    
    for enrollment in enrollments:
        user = db.query(User).filter(User.id == enrollment.user_id).first()
        if not user:
            continue
            
        # Check if user is a winner
        won_month = None
        prize_won = None
        for month, winner_data in winners_by_month.items():
            if winner_data["winner"] and winner_data["winner"]["id"] == user.id:
                won_month = month
                prize_won = {
                    "name": winner_data["prize_name"],
                    "amount": winner_data["prize_amount"]
                }
                break
        
        # Count statuses
        if enrollment.status.value == "active":
            active_members += 1
        elif enrollment.status.value == "pending":
            pending_members += 1
        elif enrollment.status.value == "completed":
            completed_members += 1
        
        total_paid += enrollment.total_paid
        
        members.append({
            "user_id": user.id,
            "mld_id": user.mld_id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "profile_photo": user.profile_photo,
            "enrollment_status": enrollment.status.value,
            "months_paid": enrollment.months_paid,
            "total_paid": enrollment.total_paid,
            "is_eligible_for_draw": enrollment.is_eligible_for_draw,
            "has_won": enrollment.has_won_prize,
            "won_month": won_month,
            "prize_won": prize_won,
            "enrolled_date": enrollment.created_at
        })
    
    # Calculate statistics
    total_expected = group.current_members * (plan.monthly_amount * plan.duration_months if plan else 0)
    collection_percentage = (total_paid / total_expected * 100) if total_expected > 0 else 0
    
    return {
        "group": {
            "id": group.id,
            "group_id": group.group_id,
            "group_name": group.group_name,
            "max_members": group.max_members,
            "current_members": group.current_members,
            "status": group.status,
            "invite_code": group.invite_code,
            "franchise_slug": franchise.franchise_slug if franchise else None,
            "franchise_password": franchise.password if franchise else None
        },
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "monthly_amount": plan.monthly_amount,
            "duration_months": plan.duration_months,
            "description": plan.description
        } if plan else None,
        "prize_pool": {
            "id": prize_pool.id,
            "name": prize_pool.name,
            "prizes": prize_pool.prizes
        } if prize_pool else None,
        "statistics": {
            "total_members": group.current_members,
            "active_members": active_members,
            "pending_members": pending_members,
            "completed_members": completed_members,
            "total_collected": total_paid,
            "expected_total": total_expected,
            "collection_percentage": round(collection_percentage, 2),
            "winners_count": len(winners_by_month),
            "pending_draws": (plan.duration_months if plan else 11) - len(winners_by_month)
        },
        "winners_by_month": winners_by_month,
        "members": members
    }

# ============== PLAN & GROUP ROUTES (PUBLIC) ==============

@app.get("/api/plans", response_model=List[PlanResponse])
def get_all_plans(db: Session = Depends(get_db)):
    plans = db.query(Plan).filter(Plan.status == PlanStatus.ACTIVE).all()
    return plans

@app.get("/api/plans/{plan_id}", response_model=PlanResponse)
def get_plan_details(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@app.get("/api/groups/{group_id}", response_model=GroupResponse)
def get_group_details(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group

@app.get("/api/plans/{plan_id}/groups", response_model=List[GroupResponse])
def get_groups_by_plan(plan_id: int, db: Session = Depends(get_db)):
    """Get all available groups for a specific plan"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Get groups that belong to this plan and are not full
    groups = db.query(Group).filter(
        Group.plan_id == plan_id,
        Group.status == PlanStatus.ACTIVE,
        Group.current_members < Group.max_members
    ).all()
    
    return groups

# ============== PIN & WALLET PAYMENT ROUTES ==============

@app.post("/api/users/pin/set")
def set_pin(
    pin_data: PINSetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set PIN for first time (4-digit) - Authenticated"""
    # Validate PIN is 4 digits
    if len(pin_data.pin) != 4 or not pin_data.pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits")
    
    # Check if PIN already set
    if current_user.pin:
        raise HTTPException(status_code=400, detail="PIN already set. Use change PIN instead")
    
    # Set PIN (plain text, no hashing)
    current_user.pin = pin_data.pin
    db.commit()
    
    return {"message": "PIN set successfully"}

@app.post("/api/users/pin/set-public")
def set_pin_public(
    pin_data: PINVerifyRequest,
    db: Session = Depends(get_db)
):
    """Set PIN for first time using MLD ID (public endpoint for payment page)"""
    user = db.query(User).filter(User.mld_id == pin_data.mld_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate PIN is 4 digits
    if len(pin_data.pin) != 4 or not pin_data.pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits")
    
    # Check if PIN already set
    if user.pin:
        raise HTTPException(status_code=400, detail="PIN already set")
    
    # Set PIN (plain text, no hashing)
    user.pin = pin_data.pin
    db.commit()
    
    return {"message": "PIN set successfully", "user_id": user.id}

@app.post("/api/users/pin/change")
def change_pin(
    pin_data: PINChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change PIN (no old PIN required)"""
    # Validate PIN is 4 digits
    if len(pin_data.new_pin) != 4 or not pin_data.new_pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits")
    
    # Update PIN
    current_user.pin = pin_data.new_pin
    db.commit()
    
    return {"message": "PIN changed successfully"}

@app.post("/api/users/pin/verify")
def verify_pin(
    verify_data: PINVerifyRequest,
    db: Session = Depends(get_db)
):
    """Verify PIN for a user (public endpoint for payment page)"""
    user = db.query(User).filter(User.mld_id == verify_data.mld_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.pin:
        raise HTTPException(status_code=400, detail="PIN not set for this user")
    
    if user.pin != verify_data.pin:
        raise HTTPException(status_code=401, detail="Incorrect PIN")
    
    return {"message": "PIN verified", "user_id": user.id}

@app.post("/api/users/pin/verify-auth")
def verify_pin_authenticated(
    pin_data: PINSetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify PIN for authenticated user"""
    if not current_user.pin:
        raise HTTPException(status_code=400, detail="PIN not set")
    
    if current_user.pin != pin_data.pin:
        raise HTTPException(status_code=401, detail="Incorrect PIN")
    
    return {"message": "PIN verified", "user_id": current_user.id}

@app.post("/api/users/wallet/pay", response_model=WalletPaymentResponse)
def wallet_payment(
    payment_data: WalletPaymentRequest,
    db: Session = Depends(get_db)
):
    """Make payment from wallet (for store purchases)"""
    # Get user by MLD ID
    user = db.query(User).filter(User.mld_id == payment_data.mld_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify PIN
    if not user.pin:
        raise HTTPException(status_code=400, detail="PIN not set. Please set PIN first")
    
    if user.pin != payment_data.pin:
        raise HTTPException(status_code=401, detail="Incorrect PIN")
    
    # Validate wallet type
    if payment_data.wallet_type not in ["millance_rewards_wallet", "savings_wallet"]:
        raise HTTPException(status_code=400, detail="Invalid wallet type")
    
    # Check balance
    current_balance = getattr(user, payment_data.wallet_type)
    if current_balance < payment_data.amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient balance. Available: ₹{current_balance:.2f}"
        )
    
    # Deduct amount
    balance_before = current_balance
    new_balance = current_balance - payment_data.amount
    setattr(user, payment_data.wallet_type, new_balance)
    
    # Create transaction record
    wallet_name = "Millance Rewards Wallet" if payment_data.wallet_type == "millance_rewards_wallet" else "Savings Wallet"
    transaction = Transaction(
        user_id=user.id,
        transaction_type="store_purchase",
        amount=payment_data.amount,
        wallet=payment_data.wallet_type,
        description=f"Store purchase via Scan & Pay from {wallet_name}",
        balance_before=balance_before,
        balance_after=new_balance
    )
    db.add(transaction)
    
    db.commit()
    db.refresh(transaction)
    
    return {
        "success": True,
        "message": "Payment successful",
        "transaction_id": transaction.id,
        "new_balance": new_balance,
        "amount_paid": payment_data.amount
    }

@app.post("/api/users/password/change")
def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password (no old password required)"""
    # Update password (plain text, no hashing as per requirement)
    current_user.password = password_data.new_password
    db.commit()
    
    return {"message": "Password changed successfully"}

@app.get("/api/users/pin/status")
def check_pin_status(current_user: User = Depends(get_current_user)):
    """Check if user has PIN set"""
    return {
        "has_pin": current_user.pin is not None,
        "pin_set": bool(current_user.pin)
    }

@app.post("/api/users/wallet/pay-auth", response_model=WalletPaymentResponse)
def wallet_payment_authenticated(
    payment_data: WalletPaymentAuthRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Make payment from wallet (authenticated user for store purchases)"""
    # Verify PIN
    if not current_user.pin:
        raise HTTPException(status_code=400, detail="PIN not set. Please set PIN first")
    
    if current_user.pin != payment_data.pin:
        raise HTTPException(status_code=401, detail="Incorrect PIN")
    
    # Validate wallet type
    if payment_data.wallet_type not in ['millance_rewards_wallet', 'savings_wallet']:
        raise HTTPException(status_code=400, detail="Invalid wallet type")
    
    # Get current balance
    if payment_data.wallet_type == 'millance_rewards_wallet':
        current_balance = current_user.millance_rewards_wallet
    else:
        current_balance = current_user.savings_wallet
    
    # Check sufficient balance
    if current_balance < payment_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    balance_before = current_balance
    
    # Deduct from wallet
    if payment_data.wallet_type == 'millance_rewards_wallet':
        current_user.millance_rewards_wallet -= payment_data.amount
        new_balance = current_user.millance_rewards_wallet
    else:
        current_user.savings_wallet -= payment_data.amount
        new_balance = current_user.savings_wallet
    
    # Create transaction record
    wallet_name = "Millance Rewards Wallet" if payment_data.wallet_type == "millance_rewards_wallet" else "Savings Wallet"
    transaction = Transaction(
        user_id=current_user.id,
        amount=payment_data.amount,
        transaction_type='store_purchase',
        wallet=payment_data.wallet_type,
        description=f"Store purchase via Scan & Pay from {wallet_name}",
        balance_before=balance_before,
        balance_after=new_balance
    )
    db.add(transaction)
    db.commit()
    
    return {
        "success": True,
        "message": "Payment successful",
        "amount_paid": payment_data.amount,
        "new_balance": new_balance,
        "transaction_id": transaction.id
    }

# ============== ENROLLMENT ROUTES ==============

@app.post("/api/enrollments", response_model=EnrollmentResponse)
def enroll_in_plan(
    enrollment_data: EnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if plan and group exist
    plan = db.query(Plan).filter(Plan.id == enrollment_data.plan_id).first()
    group = db.query(Group).filter(Group.id == enrollment_data.group_id).first()
    
    if not plan or not group:
        raise HTTPException(status_code=404, detail="Plan or Group not found")
    
    # Check if group is full
    if group.current_members >= group.max_members:
        raise HTTPException(status_code=400, detail="Group is full")
    
    # Check if user already enrolled in this specific group
    existing = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.group_id == enrollment_data.group_id,
        Enrollment.status.in_([PlanStatus.ACTIVE, PlanStatus.COMPLETED])
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this group")
    
    # Check wallet balance for first payment
    wallet_balance = (
        current_user.millance_rewards_wallet if enrollment_data.wallet_type == "millance_rewards_wallet"
        else current_user.savings_wallet
    )
    
    if wallet_balance < plan.monthly_amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance for first payment")
    
    # Deduct first month payment from wallet
    payment_wallet_before = wallet_balance
    if enrollment_data.wallet_type == "millance_rewards_wallet":
        current_user.millance_rewards_wallet -= plan.monthly_amount
        payment_wallet_after = current_user.millance_rewards_wallet
    else:
        current_user.savings_wallet -= plan.monthly_amount
        payment_wallet_after = current_user.savings_wallet
    
    # Credit 100% to savings wallet
    savings_credit = plan.monthly_amount
    savings_before = current_user.savings_wallet
    current_user.savings_wallet += savings_credit
    savings_after = current_user.savings_wallet
    
    # Create enrollment with first payment done
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=plan.duration_months * 30)
    
    enrollment = Enrollment(
        user_id=current_user.id,
        plan_id=enrollment_data.plan_id,
        group_id=enrollment_data.group_id,
        start_date=start_date,
        end_date=end_date,
        status=PlanStatus.ACTIVE,
        months_paid=1,  # First payment done
        total_paid=plan.monthly_amount,
        savings_accumulated=savings_credit,
        is_eligible_for_draw=True  # Eligible after first payment
    )
    
    db.add(enrollment)
    db.flush()  # Get enrollment ID
    
    # Create payment transaction for first month
    payment_transaction = Transaction(
        user_id=current_user.id,
        transaction_type="payment",
        amount=plan.monthly_amount,
        wallet=enrollment_data.wallet_type,
        description=f"Month 1 payment for {plan.name}",
        balance_before=payment_wallet_before,
        balance_after=payment_wallet_after
    )
    db.add(payment_transaction)
    
    # Create savings credit transaction
    savings_transaction = Transaction(
        user_id=current_user.id,
        transaction_type="savings_credit",
        amount=savings_credit,
        wallet="savings_wallet",
        description=f"Savings credit from Month 1 payment - {plan.name}",
        balance_before=savings_before,
        balance_after=savings_after
    )
    db.add(savings_transaction)
    
    # Create payment record
    payment_record = Payment(
        user_id=current_user.id,
        enrollment_id=enrollment.id,
        amount=plan.monthly_amount,
        month="Month 1",
        payment_date=datetime.utcnow(),
        status=PaymentStatus.PAID,
        wallet_used=enrollment_data.wallet_type,
        savings_credited=savings_credit,
        transaction_id=str(payment_transaction.id) if hasattr(payment_transaction, 'id') else None
    )
    db.add(payment_record)
    
    # Update group member count
    group.current_members += 1
    plan.current_members += 1
    
    db.commit()
    db.refresh(enrollment)
    
    return enrollment

@app.get("/api/enrollments/my", response_model=List[EnrollmentResponse])
def get_my_enrollments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id
    ).all()
    
    # Add latest payment coupon and group enrollment status to each enrollment
    result = []
    for enrollment in enrollments:
        # Get group details
        group = db.query(Group).filter(Group.id == enrollment.group_id).first()
        
        # Calculate group enrollment status
        group_enrollment_status = calculate_group_enrollment_status(group)
        
        enrollment_dict = {
            "id": enrollment.id,
            "user_id": enrollment.user_id,
            "plan_id": enrollment.plan_id,
            "group_id": enrollment.group_id,
            "status": enrollment.status,
            "months_paid": enrollment.months_paid,
            "total_paid": enrollment.total_paid,
            "savings_accumulated": enrollment.savings_accumulated,
            "has_won_prize": enrollment.has_won_prize,
            "prize_name": enrollment.prize_name,
            "prize_amount": enrollment.prize_amount,
            "prize_won_month": enrollment.prize_won_month,
            "coupon_code": enrollment.coupon_code,
            "coupon_status": enrollment.coupon_status,
            "created_at": enrollment.created_at,
            "latest_payment_coupon": None,
            "group_enrollment": group_enrollment_status  # NEW: Group enrollment status
        }
        
        # Get latest payment coupon
        if enrollment.months_paid > 0:
            latest_payment = db.query(Payment).filter(
                Payment.enrollment_id == enrollment.id,
                Payment.status == PaymentStatus.PAID
            ).order_by(Payment.created_at.desc()).first()
            
            if latest_payment and latest_payment.coupon_number:
                enrollment_dict["latest_payment_coupon"] = latest_payment.coupon_number
        
        result.append(enrollment_dict)
    
    return result


@app.get("/api/enrollments/{enrollment_id}/payment-status")
def get_enrollment_payment_status(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed payment status with deadline information for group payment page
    Includes: payment deadlines, overdue status, consecutive misses, amount due
    """
    from payment_policy import (
        get_unpaid_months, calculate_total_amount_due,
        check_and_update_consecutive_misses, is_eligible_for_draw,
        get_payment_deadline, get_days_until_deadline
    )
    
    # Get enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.id == enrollment_id,
        Enrollment.user_id == current_user.id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Get plan and group details
    plan = db.query(Plan).filter(Plan.id == enrollment.plan_id).first()
    group = db.query(Group).filter(Group.id == enrollment.group_id).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Check if legacy policy (old enrollments - no deadline enforcement)
    if enrollment.is_legacy_policy:
        # Calculate group enrollment status
        group_enrollment_status = calculate_group_enrollment_status(group)
        
        return {
            "enrollment_id": enrollment.id,
            "group_id": group.group_id if group else None,
            "group_name": group.group_name if group else None,
            "plan_name": plan.name,
            "monthly_amount": plan.monthly_amount,
            "total_months": plan.duration_months,
            "months_paid": enrollment.months_paid,
            "total_paid": enrollment.total_paid,
            "is_legacy_policy": True,
            "policy_message": "No payment deadlines - Legacy enrollment",
            "next_month": enrollment.months_paid + 1,
            "next_month_amount": plan.monthly_amount,
            "payment_deadline": None,
            "is_overdue": False,
            "consecutive_misses": 0,
            "at_risk_of_removal": False,
            "is_eligible_for_draw": enrollment.months_paid > 0,
            "group_enrollment": group_enrollment_status  # NEW: Group enrollment status
        }
    
    # NEW POLICY - Calculate deadline information
    current_month = enrollment.months_paid + 1
    unpaid_months = get_unpaid_months(enrollment, db)
    amount_due = calculate_total_amount_due(enrollment, plan.monthly_amount, db)
    miss_status = check_and_update_consecutive_misses(enrollment, db)
    eligibility = is_eligible_for_draw(enrollment, db)
    
    # Get current month deadline
    current_deadline = get_payment_deadline(current_month, enrollment.enrollment_date)
    days_until = get_days_until_deadline(current_deadline)
    
    # Get all payments history
    payments = db.query(Payment).filter(
        Payment.enrollment_id == enrollment_id
    ).order_by(Payment.month_number.asc()).all()
    
    payment_history = []
    for payment in payments:
        payment_history.append({
            "month_number": payment.month_number,
            "month": payment.month,
            "amount": payment.amount,
            "status": payment.status.value,
            "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
            "coupon_number": payment.coupon_number,
            "deadline": payment.payment_deadline.isoformat() if payment.payment_deadline else None,
            "is_overdue": payment.is_overdue,
            "days_overdue": payment.days_overdue
        })
    
    db.commit()  # Save consecutive_missed_payments update
    
    # Calculate group enrollment status
    group_enrollment_status = calculate_group_enrollment_status(group)
    
    return {
        "enrollment_id": enrollment.id,
        "group_id": group.group_id if group else None,
        "group_name": group.group_name if group else None,
        "plan_name": plan.name,
        "monthly_amount": plan.monthly_amount,
        "total_months": plan.duration_months,
        "months_paid": enrollment.months_paid,
        "total_paid": enrollment.total_paid,
        
        # Policy info
        "is_legacy_policy": False,
        "policy_message": f"Payment deadline: 5th of each month. {2 - miss_status['consecutive_misses']} misses until removal.",
        
        # Current month info
        "current_month": current_month,
        "payment_deadline": current_deadline.isoformat(),
        "days_until_deadline": days_until,
        "is_overdue": days_until < 0,
        "days_overdue": abs(days_until) if days_until < 0 else 0,
        
        # Payment status
        "unpaid_months": unpaid_months,
        "total_amount_due": amount_due['total_amount'],
        "months_to_pay": amount_due['months_to_pay'],
        "payment_breakdown": amount_due['breakdown'],
        
        # Risk status
        "consecutive_misses": miss_status['consecutive_misses'],
        "at_risk_of_removal": miss_status['consecutive_misses'] >= 1,
        "should_remove": miss_status['should_remove'],
        "auto_removed": enrollment.auto_removed,
        
        # Draw eligibility
        "is_eligible_for_draw": eligibility['is_eligible'],
        "eligibility_reason": eligibility['reason'],
        
        # Group enrollment status (NEW)
        "group_enrollment": group_enrollment_status,
        
        # Payment history
        "payment_history": payment_history
    }


@app.get("/api/enrollments/{enrollment_id}")
def get_enrollment_details(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed enrollment information with payment history"""
    
    # Get enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.id == enrollment_id,
        Enrollment.user_id == current_user.id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Get plan details
    plan = db.query(Plan).filter(Plan.id == enrollment.plan_id).first()
    
    # Get group details
    group = db.query(Group).filter(Group.id == enrollment.group_id).first()
    
    # Get all payments for this enrollment
    payments = db.query(Payment).filter(
        Payment.enrollment_id == enrollment_id
    ).order_by(Payment.created_at.asc()).all()
    
    # Build payment history with coupon numbers
    payment_history = []
    for payment in payments:
        payment_history.append({
            "id": payment.id,
            "month": payment.month,
            "amount": payment.amount,
            "status": payment.status.value,
            "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
            "coupon_number": payment.coupon_number,
            "wallet_used": payment.wallet_used,
            "savings_credited": payment.savings_credited
        })
    
    # Get next draw info for this group
    next_draw = db.query(DrawSchedule).filter(
        DrawSchedule.group_id == enrollment.group_id,
        DrawSchedule.status == "scheduled",
        DrawSchedule.month_number > enrollment.months_paid
    ).order_by(DrawSchedule.month_number.asc()).first()
    
    return {
        "enrollment": {
            "id": enrollment.id,
            "user_id": enrollment.user_id,
            "plan_id": enrollment.plan_id,
            "group_id": enrollment.group_id,
            "status": enrollment.status.value,
            "months_paid": enrollment.months_paid,
            "total_paid": enrollment.total_paid,
            "savings_accumulated": enrollment.savings_accumulated,
            "has_won_prize": enrollment.has_won_prize,
            "prize_won_month": enrollment.prize_won_month,
            "prize_name": enrollment.prize_name,
            "prize_amount": enrollment.prize_amount,
            "created_at": enrollment.created_at.isoformat()
        },
        "plan": {
            "id": plan.id,
            "name": plan.name,
            "monthly_amount": plan.monthly_amount,
            "duration_months": plan.duration_months,
            "description": plan.description
        },
        "group": {
            "id": group.id,
            "group_id": group.group_id,
            "group_name": group.group_name,
            "current_members": group.current_members,
            "max_members": group.max_members,
            "status": group.status.value
        },
        "payment_history": payment_history,
        "next_draw": {
            "month_number": next_draw.month_number if next_draw else None,
            "draw_date": next_draw.draw_date.isoformat() if next_draw and next_draw.draw_date else None,
            "draw_time": next_draw.draw_time if next_draw else None
        } if next_draw else None,
        "total_amount": plan.monthly_amount * plan.duration_months,
        "remaining_amount": plan.monthly_amount * (plan.duration_months - enrollment.months_paid),
        "is_completed": enrollment.months_paid >= plan.duration_months or enrollment.has_won_prize
    }

# ============== PAYMENT ROUTES ==============

@app.post("/api/payments", response_model=PaymentResponse)
def make_payment(
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.id == payment_data.enrollment_id,
        Enrollment.user_id == current_user.id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Check if user already won (plan completed)
    if enrollment.has_won_prize:
        raise HTTPException(status_code=400, detail="Plan already completed - You won a prize!")
    
    # Check if already completed 11 months
    if enrollment.months_paid >= 11:
        raise HTTPException(status_code=400, detail="Plan already completed - All payments made")
    
    # Get plan
    plan = db.query(Plan).filter(Plan.id == enrollment.plan_id).first()
    
    # Check wallet balance (for deduction)
    wallet_balance = (
        current_user.millance_rewards_wallet if payment_data.wallet_type == "millance_rewards_wallet"
        else current_user.savings_wallet
    )
    
    if wallet_balance < plan.monthly_amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    # Deduct from selected wallet
    payment_wallet_before = wallet_balance
    if payment_data.wallet_type == "millance_rewards_wallet":
        current_user.millance_rewards_wallet -= plan.monthly_amount
        payment_wallet_after = current_user.millance_rewards_wallet
        
        # Credit to savings wallet ONLY if paid from rewards wallet
        savings_before = current_user.savings_wallet
        current_user.savings_wallet += plan.monthly_amount
        savings_after = current_user.savings_wallet
        savings_credited = plan.monthly_amount
    else:
        # If paying from savings wallet, only deduct (don't credit back)
        current_user.savings_wallet -= plan.monthly_amount
        payment_wallet_after = current_user.savings_wallet
        savings_before = payment_wallet_before
        savings_after = payment_wallet_after
        savings_credited = 0  # No savings credit when paying from savings
    
    # Generate unique coupon number
    from models import generate_coupon_number
    coupon_number = generate_coupon_number(db)
    
    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        enrollment_id=enrollment.id,
        amount=plan.monthly_amount,
        month=payment_data.month,
        payment_date=datetime.utcnow(),
        status=PaymentStatus.PAID,
        wallet_used=payment_data.wallet_type,
        savings_credited=savings_credited,  # Use calculated savings credit
        transaction_id=f"TXN{int(datetime.utcnow().timestamp())}",
        coupon_number=coupon_number  # NEW: Assign coupon number
    )
    db.add(payment)
    
    # Update enrollment
    enrollment.months_paid += 1
    enrollment.total_paid += plan.monthly_amount
    enrollment.savings_accumulated += savings_credited  # Only add if credited
    enrollment.is_eligible_for_draw = True
    
    # Check if already completed all 11 months
    if enrollment.months_paid >= 11:
        enrollment.status = PlanStatus.COMPLETED_FULL
        enrollment.ended_at = datetime.utcnow()
    
    # Create transaction record for payment deduction
    transaction_payment = Transaction(
        user_id=current_user.id,
        transaction_type="payment",
        amount=plan.monthly_amount,
        wallet=payment_data.wallet_type,
        description=f"Monthly payment for {payment_data.month}",
        balance_before=payment_wallet_before,
        balance_after=payment_wallet_after
    )
    db.add(transaction_payment)
    
    # Create transaction record for savings credit
    transaction_savings = Transaction(
        user_id=current_user.id,
        transaction_type="savings_credit",
        amount=plan.monthly_amount,
        wallet="savings_wallet",
        description=f"Savings credit for {payment_data.month}",
        balance_before=savings_before,
        balance_after=savings_after
    )
    db.add(transaction_savings)
    
    # Commission calculation for referred users
    if current_user.referred_by_franchise_id:
        from models import FranchiseEarning
        
        commission_amount = plan.monthly_amount * enrollment.commission_rate
        
        # Credit commission to franchise earnings wallet
        franchise = db.query(Franchise).filter(Franchise.id == current_user.referred_by_franchise_id).first()
        if franchise:
            franchise.earnings_wallet += commission_amount
            
            # Create franchise earning record
            earning = FranchiseEarning(
                franchise_id=franchise.id,
                user_id=current_user.id,
                payment_id=payment.id,
                amount=commission_amount,
                commission_rate=enrollment.commission_rate,
                payment_amount=plan.monthly_amount,
                description=f"Commission from {current_user.full_name} ({current_user.mld_id}) - {payment_data.month}"
            )
            db.add(earning)
    
    db.commit()
    db.refresh(payment)
    
    return payment

@app.get("/api/payments/my", response_model=List[PaymentResponse])
def get_my_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.id
    ).order_by(Payment.created_at.desc()).all()
    return payments

# ============== USER DRAW & REDEMPTION ROUTES ==============

@app.get("/api/users/draws/status")
def get_user_draw_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's draw status and history"""
    from models import DrawSchedule, DrawResult
    
    # Get ALL user's enrollments (active and completed)
    all_enrollments = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.status.in_([
            PlanStatus.ACTIVE, 
            PlanStatus.COMPLETED,
            PlanStatus.COMPLETED_WON,
            PlanStatus.COMPLETED_FULL
        ])
    ).all()
    
    if not all_enrollments:
        return {
            "next_draw": None, 
            "my_results": [], 
            "all_scheduled_draws": [],
            "enrollment_status": None,
            "live_draw": None
        }
    
    # Get primary enrollment (first active one)
    enrollment = all_enrollments[0]
    
    # Get next scheduled draw for primary enrollment
    next_draw = db.query(DrawSchedule).filter(
        DrawSchedule.group_id == enrollment.group_id,
        DrawSchedule.status == "scheduled",
        DrawSchedule.month_number > enrollment.months_paid
    ).order_by(DrawSchedule.draw_date).first()
    
    # Get ALL scheduled draws for ALL user's groups
    all_group_ids = [e.group_id for e in all_enrollments]
    all_scheduled_draws = db.query(DrawSchedule).filter(
        DrawSchedule.group_id.in_(all_group_ids),
        DrawSchedule.status == "scheduled"
    ).order_by(DrawSchedule.draw_date).all()
    
    # CHECK FOR LIVE DRAWS - Check if any of user's groups has a live draw
    live_draw = db.query(DrawSchedule).filter(
        DrawSchedule.group_id.in_(all_group_ids),
        DrawSchedule.status == "live"
    ).first()
    
    live_draw_data = None
    if live_draw:
        # Get ALL eligible users for this live draw
        eligible_users = db.query(User).join(Enrollment).filter(
            Enrollment.group_id == live_draw.group_id,
            Enrollment.status == PlanStatus.ACTIVE,
            Enrollment.has_won_prize == False,
            Enrollment.months_paid >= live_draw.month_number
        ).all()
        
        # Get prize pool for this group
        group = db.query(Group).filter(Group.id == live_draw.group_id).first()
        plan = db.query(Plan).filter(Plan.id == group.plan_id).first() if group else None
        prize_pool = db.query(PrizePool).filter(PrizePool.id == plan.prize_pool_id).first() if plan else None
        
        # Format prizes
        prizes_list = []
        if prize_pool:
            for i in range(1, 16):
                prize_name = getattr(prize_pool, f"prize_{i}_name", None)
                prize_amount = getattr(prize_pool, f"prize_{i}_amount", None)
                if prize_name and prize_amount:
                    prizes_list.append({
                        "name": prize_name,
                        "amount": float(prize_amount),
                        "month": i
                    })
        
        live_draw_data = {
            "draw_id": live_draw.id,
            "group_id": live_draw.group_id,
            "month_number": live_draw.month_number,
            "draw_date": live_draw.draw_date.isoformat() if live_draw.draw_date else None,
            "draw_time": live_draw.draw_time if hasattr(live_draw, 'draw_time') else '19:00',
            "eligible_users": [
                {
                    "mld_id": u.mld_id,
                    "full_name": u.full_name
                } for u in eligible_users
            ],
            "eligible_users_count": len(eligible_users),
            "prizes": prizes_list
        }
    
    # Format all scheduled draws
    scheduled_draws_data = []
    for draw in all_scheduled_draws:
        scheduled_draws_data.append({
            "group_id": draw.group_id,
            "month_number": draw.month_number,
            "draw_date": draw.draw_date.isoformat() if draw.draw_date else None,
            "draw_time": draw.draw_time if hasattr(draw, 'draw_time') else '19:00'
        })
    
    # Get all draw results for primary group
    all_results = db.query(DrawResult).filter(
        DrawResult.group_id == enrollment.group_id
    ).order_by(DrawResult.month_number).all()
    
    my_results = []
    for result in all_results:
        is_winner = result.user_id == current_user.id
        winner_user = db.query(User).filter(User.id == result.user_id).first()
        
        # Get payment details for this month to include coupon number
        payment = db.query(Payment).filter(
            Payment.enrollment_id == enrollment.id,
            Payment.month == str(result.month_number)
        ).first()
        
        my_results.append({
            "month": result.month_number,
            "status": "won" if is_winner else "lost",
            "winner_mld_id": winner_user.mld_id if winner_user else None,
            "winner_name": winner_user.full_name if winner_user else None,
            "winner_profile_photo": winner_user.profile_photo if winner_user else None,
            "coupon_number": payment.coupon_number if payment else None,  # NEW: Include coupon
            "prize_name": result.prize_name,
            "prize_amount": result.prize_amount,
            "draw_date": result.draw_date.isoformat() if hasattr(result, 'draw_date') and result.draw_date else None,
            "is_me": is_winner
        })
    
    return {
        "next_draw": {
            "group_id": enrollment.group_id,
            "month_number": next_draw.month_number if next_draw else None,
            "draw_date": next_draw.draw_date.isoformat() if next_draw and next_draw.draw_date else None,
            "draw_time": next_draw.draw_time if next_draw and hasattr(next_draw, 'draw_time') else '19:00',
            # User is eligible if: active enrollment, hasn't won, and has paid for the draw month
            "eligible": (enrollment.status == PlanStatus.ACTIVE and 
                        not enrollment.has_won_prize and 
                        enrollment.months_paid >= (next_draw.month_number if next_draw else 0))
        } if next_draw else None,
        "my_results": my_results,
        "all_scheduled_draws": scheduled_draws_data,
        "live_draw": live_draw_data,
        "enrollment_status": {
            "has_won": enrollment.has_won_prize,
            "prize_name": enrollment.prize_name,
            "prize_amount": enrollment.prize_amount,
            "prize_won_month": enrollment.prize_won_month if hasattr(enrollment, 'prize_won_month') else None,
            "months_paid": enrollment.months_paid,
            "savings_accumulated": enrollment.savings_accumulated
        }
    }

@app.post("/api/users/redeem-savings", response_model=RedemptionResponse)
def redeem_savings(
    redemption_data: RedemptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Redeem savings wallet amount for in-store use"""
    from models import Redemption
    import random
    import string
    from datetime import timedelta
    
    # Get enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.id == redemption_data.enrollment_id,
        Enrollment.user_id == current_user.id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Check enrollment is completed
    if enrollment.status not in [PlanStatus.COMPLETED_WON, PlanStatus.COMPLETED_FULL]:
        if not enrollment.has_won_prize and enrollment.months_paid < 11:
            raise HTTPException(status_code=400, detail="Plan not completed yet. Complete all payments or win a prize.")
    
    # Check savings wallet balance
    if current_user.savings_wallet < redemption_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient savings wallet balance")
    
    # Generate redemption code
    redemption_code = f"MLDR-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    
    # Deduct from savings wallet
    savings_before = current_user.savings_wallet
    current_user.savings_wallet -= redemption_data.amount
    savings_after = current_user.savings_wallet
    
    # Create redemption record
    redemption = Redemption(
        user_id=current_user.id,
        enrollment_id=enrollment.id,
        amount=redemption_data.amount,
        redemption_code=redemption_code,
        status="pending",
        valid_until=datetime.utcnow() + timedelta(days=365)  # Valid for 1 year
    )
    db.add(redemption)
    
    # Create transaction
    transaction = Transaction(
        user_id=current_user.id,
        transaction_type="redemption",
        amount=redemption_data.amount,
        wallet="savings_wallet",
        description=f"Savings redeemed - Code: {redemption_code}",
        balance_before=savings_before,
        balance_after=savings_after
    )
    db.add(transaction)
    
    db.commit()
    db.refresh(redemption)
    
    return redemption

@app.get("/api/users/redemptions")
def get_user_redemptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all redemption codes for the current user"""
    from models import Redemption
    
    redemptions = db.query(Redemption).filter(
        Redemption.user_id == current_user.id
    ).order_by(Redemption.created_at.desc()).all()
    
    return [{
        "id": r.id,
        "redemption_code": r.redemption_code,
        "amount": r.amount,
        "status": r.status,
        "valid_until": r.valid_until,
        "created_at": r.created_at,
        "is_expired": r.valid_until < datetime.utcnow() if r.valid_until else False
    } for r in redemptions]

# ============== ADMIN ROUTES ==============

@app.get("/api/admin/stats")
def get_admin_stats(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get overall system statistics"""
    total_users = db.query(User).count()
    total_franchises = db.query(Franchise).filter(Franchise.is_active == True).count()
    total_groups = db.query(Group).count()
    total_enrollments = db.query(Enrollment).count()
    
    # Calculate total revenue from payments
    from sqlalchemy import func
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatus.PAID
    ).scalar() or 0
    
    return {
        "total_users": total_users,
        "total_franchises": total_franchises,
        "total_groups": total_groups,
        "total_enrollments": total_enrollments,
        "total_revenue": float(total_revenue)
    }

@app.get("/api/admin/users", response_model=List[UserResponse])
def get_all_users(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get all users (paginated)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@app.get("/api/admin/franchises", response_model=List[FranchiseResponse])
def get_all_franchises(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get all franchises"""
    franchises = db.query(Franchise).all()
    return franchises

@app.post("/api/admin/franchises", response_model=FranchiseResponse)
def create_franchise(
    franchise_data: FranchiseCreate,
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Create a new franchise"""
    # Check if email or franchise_code already exists
    existing = db.query(Franchise).filter(
        (Franchise.email == franchise_data.email) | 
        (Franchise.franchise_code == franchise_data.franchise_code)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Franchise with this email or code already exists")
    
    # Auto-generate franchise_slug from franchise_name
    from models import slugify
    franchise_slug = slugify(franchise_data.franchise_name)
    
    # Check if slug exists, add number if needed
    slug_exists = db.query(Franchise).filter(Franchise.franchise_slug == franchise_slug).first()
    if slug_exists:
        import random
        franchise_slug = f"{franchise_slug}-{random.randint(100, 999)}"
    
    new_franchise = Franchise(
        email=franchise_data.email,
        password=franchise_data.password,  # Plain text as requested
        franchise_name=franchise_data.franchise_name,
        franchise_code=franchise_data.franchise_code,
        franchise_slug=franchise_slug,
        phone=franchise_data.phone if franchise_data.phone else None,
        address=franchise_data.address if franchise_data.address else None
    )
    
    db.add(new_franchise)
    db.commit()
    db.refresh(new_franchise)
    
    return new_franchise

@app.patch("/api/admin/users/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool,
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Update user active status"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = is_active
    db.commit()
    
    return {"message": "User status updated", "user_id": user_id, "is_active": is_active}

@app.post("/api/admin/users/{user_id}/add-balance", response_model=BalanceUpdateResponse)
def add_user_balance(
    user_id: int,
    request: BalanceUpdateRequest,
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Add balance to user's wallet (millance_rewards_wallet or savings_wallet)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    if request.wallet_type not in ["millance_rewards_wallet", "savings_wallet"]:
        raise HTTPException(status_code=400, detail="Invalid wallet type")
    
    # Get current balance
    current_balance = getattr(user, request.wallet_type)
    
    # Update wallet
    setattr(user, request.wallet_type, current_balance + request.amount)
    new_balance = getattr(user, request.wallet_type)
    
    # Create transaction record
    transaction = Transaction(
        user_id=user_id,
        transaction_type="admin_credit",
        amount=request.amount,
        wallet=request.wallet_type,
        description=f"Balance added by admin to {request.wallet_type.replace('_', ' ')}",
        balance_before=current_balance,
        balance_after=new_balance
    )
    db.add(transaction)
    db.commit()
    
    return {
        "message": "Balance added successfully",
        "user_id": user_id,
        "wallet_type": request.wallet_type,
        "amount_changed": request.amount,
        "new_balance": new_balance
    }

@app.post("/api/admin/users/{user_id}/reduce-balance", response_model=BalanceUpdateResponse)
def reduce_user_balance(
    user_id: int,
    request: BalanceUpdateRequest,
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Reduce balance from user's wallet (millance_rewards_wallet or savings_wallet)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    if request.wallet_type not in ["millance_rewards_wallet", "savings_wallet"]:
        raise HTTPException(status_code=400, detail="Invalid wallet type")
    
    # Get current balance
    current_balance = getattr(user, request.wallet_type)
    
    if request.amount > current_balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Update wallet
    setattr(user, request.wallet_type, current_balance - request.amount)
    new_balance = getattr(user, request.wallet_type)
    
    # Create transaction record
    transaction = Transaction(
        user_id=user_id,
        transaction_type="admin_debit",
        amount=request.amount,
        wallet=request.wallet_type,
        description=f"Balance deducted by admin from {request.wallet_type.replace('_', ' ')}",
        balance_before=current_balance,
        balance_after=new_balance
    )
    db.add(transaction)
    db.commit()
    
    return {
        "message": "Balance reduced successfully",
        "user_id": user_id,
        "wallet_type": request.wallet_type,
        "amount_changed": request.amount,
        "new_balance": new_balance
    }

@app.patch("/api/admin/franchises/{franchise_id}/status")
def update_franchise_status(
    franchise_id: int,
    is_active: bool,
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Update franchise active status"""
    franchise = db.query(Franchise).filter(Franchise.id == franchise_id).first()
    if not franchise:
        raise HTTPException(status_code=404, detail="Franchise not found")
    
    franchise.is_active = is_active
    db.commit()
    
    return {"message": "Franchise status updated", "franchise_id": franchise_id, "is_active": is_active}

@app.get("/api/admin/enrollments")
def get_all_enrollments(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get all enrollments"""
    enrollments = db.query(Enrollment).offset(skip).limit(limit).all()
    return enrollments

@app.get("/api/admin/payments")
def get_all_payments(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 1000
):
    """Get all payments"""
    payments = db.query(Payment).offset(skip).limit(limit).all()
    return payments

@app.get("/api/admin/transactions")
def get_all_transactions(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 1000
):
    """Get all wallet transactions"""
    transactions = db.query(Transaction).offset(skip).limit(limit).all()
    return transactions

@app.get("/api/admin/draws/scheduled")
def get_scheduled_draws(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get all scheduled (upcoming) draws"""
    from models import DrawSchedule
    
    # Get scheduled draws that haven't been completed yet
    scheduled_draws = db.query(DrawSchedule).filter(
        DrawSchedule.status == "scheduled"
    ).order_by(DrawSchedule.draw_date).all()
    
    # Enrich with group and franchise info
    result = []
    for draw in scheduled_draws:
        group = db.query(Group).filter(Group.id == draw.group_id).first()
        franchise = db.query(Franchise).filter(Franchise.id == draw.franchise_id).first()
        
        result.append({
            "id": draw.id,
            "group_id": draw.group_id,
            "group_name": group.group_name if group else "Unknown Group",
            "group_code": group.group_id if group else None,
            "franchise_id": draw.franchise_id,
            "franchise_name": franchise.franchise_name if franchise else "Unknown Franchise",
            "month_number": draw.month_number,
            "draw_date": draw.draw_date,
            "draw_time": draw.draw_time,
            "status": draw.status,
            "created_at": draw.created_at
        })
    
    return result

@app.get("/api/admin/draws/history")
def get_draw_history(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get all completed draws with results"""
    from models import DrawSchedule, DrawResult
    
    # Get completed draws
    completed_draws = db.query(DrawSchedule).filter(
        DrawSchedule.status == "completed"
    ).order_by(DrawSchedule.conducted_at.desc()).all()
    
    # Enrich with group, franchise, and winner info
    result = []
    for draw in completed_draws:
        group = db.query(Group).filter(Group.id == draw.group_id).first()
        franchise = db.query(Franchise).filter(Franchise.id == draw.franchise_id).first()
        
        # Get draw result (winner)
        draw_result = db.query(DrawResult).filter(
            DrawResult.draw_schedule_id == draw.id
        ).first()
        
        winner_info = None
        coupon_code = None
        if draw_result:
            winner = db.query(User).filter(User.id == draw_result.user_id).first()
            if winner:
                winner_info = {
                    "id": winner.id,
                    "full_name": winner.full_name,
                    "mld_id": winner.mld_id,
                    "email": winner.email,
                    "phone": winner.phone
                }
            
            # Get coupon code from enrollment
            enrollment = db.query(Enrollment).filter(
                Enrollment.id == draw_result.enrollment_id
            ).first()
            if enrollment and enrollment.coupon_code:
                coupon_code = enrollment.coupon_code
        
        result.append({
            "id": draw.id,
            "group_id": draw.group_id,
            "group_name": group.group_name if group else "Unknown Group",
            "group_code": group.group_id if group else None,
            "franchise_id": draw.franchise_id,
            "franchise_name": franchise.franchise_name if franchise else "Unknown Franchise",
            "month_number": draw.month_number,
            "draw_date": draw.draw_date,
            "conducted_at": draw.conducted_at,
            "status": draw.status,
            "winner": winner_info,
            "coupon_code": coupon_code,
            "prize_name": draw_result.prize_name if draw_result else None,
            "prize_amount": draw_result.prize_amount if draw_result else None,
            "created_at": draw.created_at
        })
    
    return result

@app.get("/api/admin/revenue-report")
def get_revenue_report(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get monthly revenue report"""
    from sqlalchemy import func, extract
    
    # Get revenue grouped by month
    revenue_by_month = db.query(
        extract('year', Payment.payment_date).label('year'),
        extract('month', Payment.payment_date).label('month'),
        func.sum(Payment.amount).label('total')
    ).filter(
        Payment.status == PaymentStatus.PAID,
        Payment.payment_date.isnot(None)
    ).group_by('year', 'month').all()
    
    return [
        {
            "year": int(r.year) if r.year else 0,
            "month": int(r.month) if r.month else 0,
            "total": float(r.total) if r.total else 0
        }
        for r in revenue_by_month
    ]

# ============== ADMIN FRANCHISE OPERATIONS ==============

@app.get("/api/admin/prize-pools", response_model=List[PrizePoolResponse])
def get_all_prize_pools(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get all prize pools across all franchises"""
    pools = db.query(PrizePool).all()
    return pools

@app.post("/api/admin/prize-pools", response_model=PrizePoolResponse)
def create_prize_pool_as_admin(
    prize_pool_data: dict,
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Admin creates prize pool for a franchise"""
    franchise_id = prize_pool_data.get('franchise_id')
    if not franchise_id:
        raise HTTPException(status_code=400, detail="franchise_id is required")
    
    franchise = db.query(Franchise).filter(Franchise.id == franchise_id).first()
    if not franchise:
        raise HTTPException(status_code=404, detail="Franchise not found")
    
    if len(prize_pool_data.get('prizes', [])) > 15:
        raise HTTPException(status_code=400, detail="Maximum 15 prizes allowed")
    
    new_pool = PrizePool(
        franchise_id=franchise_id,
        name=prize_pool_data.get('name'),
        description=prize_pool_data.get('description')
    )
    
    for i, prize in enumerate(prize_pool_data.get('prizes', []), 1):
        if prize.get('name') and prize.get('amount'):
            setattr(new_pool, f"prize_{i}_name", prize['name'])
            setattr(new_pool, f"prize_{i}_amount", prize['amount'])
    
    db.add(new_pool)
    db.commit()
    db.refresh(new_pool)
    
    return new_pool

@app.get("/api/admin/plans", response_model=List[PlanResponse])
def get_all_plans_admin(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get all plans across all franchises"""
    plans = db.query(Plan).all()
    return plans

@app.post("/api/admin/plans", response_model=PlanResponse)
def create_plan_as_admin(
    plan_data: dict,
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Admin creates plan for a franchise"""
    franchise_id = plan_data.get('franchise_id')
    prize_pool_id = plan_data.get('prize_pool_id')
    
    if not franchise_id or not prize_pool_id:
        raise HTTPException(status_code=400, detail="franchise_id and prize_pool_id are required")
    
    # Verify prize pool exists and belongs to franchise
    prize_pool = db.query(PrizePool).filter(
        PrizePool.id == prize_pool_id,
        PrizePool.franchise_id == franchise_id
    ).first()
    
    if not prize_pool:
        raise HTTPException(status_code=404, detail="Prize pool not found for this franchise")
    
    new_plan = Plan(
        franchise_id=franchise_id,
        prize_pool_id=prize_pool_id,
        name=plan_data.get('name'),
        monthly_amount=plan_data.get('monthly_amount'),
        duration_months=plan_data.get('duration_months', 11),
        max_members=plan_data.get('max_members'),
        description=plan_data.get('description')
    )
    
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    
    return new_plan

@app.get("/api/admin/groups", response_model=List[GroupResponse])
def get_all_groups_admin(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get all groups across all franchises"""
    groups = db.query(Group).all()
    return groups

@app.post("/api/admin/groups", response_model=GroupResponse)
def create_group_as_admin(
    group_data: dict,
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Admin creates group for a franchise"""
    franchise_id = group_data.get('franchise_id')
    plan_id = group_data.get('plan_id')
    
    if not franchise_id or not plan_id:
        raise HTTPException(status_code=400, detail="franchise_id and plan_id are required")
    
    # Verify plan exists and belongs to franchise
    plan = db.query(Plan).filter(
        Plan.id == plan_id,
        Plan.franchise_id == franchise_id
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found for this franchise")
    
    new_group = Group(
        franchise_id=franchise_id,
        plan_id=plan_id,
        group_name=group_data.get('group_name'),
        max_members=group_data.get('max_members')
    )
    
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    
    return new_group

# ============== FRANCHISE ADDITIONAL ROUTES ==============

@app.get("/api/franchise/stats")
def get_franchise_stats(
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Get franchise-specific statistics"""
    total_groups = db.query(Group).filter(Group.franchise_id == current_user.id).count()
    total_plans = db.query(Plan).filter(Plan.franchise_id == current_user.id).count()
    
    # Get total members across all groups
    from sqlalchemy import func
    total_members = db.query(func.sum(Group.current_members)).filter(
        Group.franchise_id == current_user.id
    ).scalar() or 0
    
    # Get revenue from this franchise's plans
    revenue = db.query(func.sum(Payment.amount)).join(
        Enrollment, Payment.enrollment_id == Enrollment.id
    ).join(
        Plan, Enrollment.plan_id == Plan.id
    ).filter(
        Plan.franchise_id == current_user.id,
        Payment.status == PaymentStatus.PAID
    ).scalar() or 0
    
    return {
        "total_groups": total_groups,
        "total_plans": total_plans,
        "total_members": int(total_members),
        "total_revenue": float(revenue)
    }

@app.get("/api/franchise/plans", response_model=List[PlanResponse])
def get_franchise_plans(
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Get all plans created by this franchise"""
    plans = db.query(Plan).filter(Plan.franchise_id == current_user.id).all()
    return plans

@app.get("/api/franchise/enrollments")
def get_franchise_enrollments(
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Get all enrollments in this franchise's plans"""
    enrollments = db.query(Enrollment).join(
        Plan, Enrollment.plan_id == Plan.id
    ).filter(
        Plan.franchise_id == current_user.id
    ).all()
    return enrollments

# ============== DRAW MANAGEMENT ROUTES ==============

@app.get("/api/franchise/draws/check-prize/{group_id}/{month_number}")
def check_prize_configured(
    group_id: int,
    month_number: int,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Check if prize is configured for a specific month in the group's prize pool"""
    
    # Verify group belongs to franchise
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.franchise_id == current_user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Get plan and prize pool
    plan = db.query(Plan).filter(Plan.id == group.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    prize_pool = db.query(PrizePool).filter(PrizePool.id == plan.prize_pool_id).first()
    if not prize_pool:
        raise HTTPException(status_code=404, detail="Prize pool not found")
    
    # Check if prize exists for this month
    prize_name = getattr(prize_pool, f"prize_{month_number}_name", None)
    prize_amount = getattr(prize_pool, f"prize_{month_number}_amount", None)
    
    return {
        "prize_pool_id": prize_pool.id,
        "prize_pool_name": prize_pool.name,
        "month_number": month_number,
        "prize_configured": bool(prize_name and prize_amount),
        "prize_name": prize_name,
        "prize_amount": prize_amount
    }

@app.post("/api/franchise/prize-pools/{prize_pool_id}/add-prize")
def add_prize_to_pool(
    prize_pool_id: int,
    prize_data: dict,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Add or update a prize for a specific month in the prize pool"""
    
    # Verify prize pool belongs to franchise
    prize_pool = db.query(PrizePool).filter(
        PrizePool.id == prize_pool_id,
        PrizePool.franchise_id == current_user.id
    ).first()
    
    if not prize_pool:
        raise HTTPException(status_code=404, detail="Prize pool not found")
    
    month_number = prize_data.get("month_number")
    prize_name = prize_data.get("prize_name")
    prize_amount = prize_data.get("prize_amount")
    
    if not month_number or not prize_name or not prize_amount:
        raise HTTPException(status_code=400, detail="month_number, prize_name, and prize_amount are required")
    
    if month_number < 1 or month_number > 15:
        raise HTTPException(status_code=400, detail="month_number must be between 1 and 15")
    
    # Update the prize pool
    setattr(prize_pool, f"prize_{month_number}_name", prize_name)
    setattr(prize_pool, f"prize_{month_number}_amount", float(prize_amount))
    
    db.commit()
    db.refresh(prize_pool)
    
    print(f"✅ Added prize for Month {month_number}: {prize_name} (₹{prize_amount}) to Prize Pool '{prize_pool.name}'")
    
    return {
        "success": True,
        "message": f"Prize configured for Month {month_number}",
        "prize_pool_id": prize_pool.id,
        "month_number": month_number,
        "prize_name": prize_name,
        "prize_amount": prize_amount
    }


# ==================== MONTHLY PRIZES (MULTI-WINNER SYSTEM) ====================

@app.get("/api/franchise/monthly-prizes/{prize_pool_id}/{month_number}")
def get_monthly_prizes(
    prize_pool_id: int,
    month_number: int,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Get all prizes configured for a specific month"""
    # Verify prize pool belongs to franchise
    prize_pool = db.query(PrizePool).filter(
        PrizePool.id == prize_pool_id,
        PrizePool.franchise_id == current_user.id
    ).first()
    
    if not prize_pool:
        raise HTTPException(status_code=404, detail="Prize pool not found")
    
    # Get all prizes for this month ordered by rank
    prizes = db.query(MonthlyPrize).filter(
        MonthlyPrize.prize_pool_id == prize_pool_id,
        MonthlyPrize.month_number == month_number
    ).order_by(MonthlyPrize.prize_rank).all()
    
    return [{
        "id": prize.id,
        "prize_rank": prize.prize_rank,
        "prize_name": prize.prize_name,
        "prize_amount": prize.prize_amount,
        "quantity": prize.quantity
    } for prize in prizes]


@app.post("/api/franchise/monthly-prizes/bulk")
def add_monthly_prizes_bulk(
    data: dict,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Add or replace all prizes for a specific month"""
    prize_pool_id = data.get("prize_pool_id")
    month_number = data.get("month_number")
    prizes = data.get("prizes", [])
    
    if not prize_pool_id or not month_number:
        raise HTTPException(status_code=400, detail="prize_pool_id and month_number are required")
    
    # Verify prize pool belongs to franchise
    prize_pool = db.query(PrizePool).filter(
        PrizePool.id == prize_pool_id,
        PrizePool.franchise_id == current_user.id
    ).first()
    
    if not prize_pool:
        raise HTTPException(status_code=404, detail="Prize pool not found")
    
    # Delete existing prizes for this month
    db.query(MonthlyPrize).filter(
        MonthlyPrize.prize_pool_id == prize_pool_id,
        MonthlyPrize.month_number == month_number
    ).delete()
    
    # Add new prizes
    created_prizes = []
    for prize_data in prizes:
        new_prize = MonthlyPrize(
            prize_pool_id=prize_pool_id,
            month_number=month_number,
            prize_rank=prize_data["prize_rank"],
            prize_name=prize_data["prize_name"],
            prize_amount=prize_data["prize_amount"],
            quantity=prize_data.get("quantity", 1)
        )
        db.add(new_prize)
        created_prizes.append(new_prize)
    
    db.commit()
    
    for prize in created_prizes:
        db.refresh(prize)
    
    return {
        "message": f"Successfully configured {len(created_prizes)} prizes for month {month_number}",
        "prizes": [{
            "id": prize.id,
            "prize_rank": prize.prize_rank,
            "prize_name": prize.prize_name,
            "prize_amount": prize.prize_amount,
            "quantity": prize.quantity
        } for prize in created_prizes]
    }


@app.put("/api/franchise/monthly-prizes/{prize_id}")
def update_monthly_prize(
    prize_id: int,
    data: dict,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Update a specific prize"""
    prize = db.query(MonthlyPrize).filter(MonthlyPrize.id == prize_id).first()
    
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")
    
    # Verify ownership
    prize_pool = db.query(PrizePool).filter(
        PrizePool.id == prize.prize_pool_id,
        PrizePool.franchise_id == current_user.id
    ).first()
    
    if not prize_pool:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Update fields
    if "prize_name" in data:
        prize.prize_name = data["prize_name"]
    if "prize_amount" in data:
        prize.prize_amount = data["prize_amount"]
    if "quantity" in data:
        prize.quantity = data["quantity"]
    if "prize_rank" in data:
        prize.prize_rank = data["prize_rank"]
    
    db.commit()
    db.refresh(prize)
    
    return {
        "id": prize.id,
        "prize_rank": prize.prize_rank,
        "prize_name": prize.prize_name,
        "prize_amount": prize.prize_amount,
        "quantity": prize.quantity
    }


@app.delete("/api/franchise/monthly-prizes/{prize_id}")
def delete_monthly_prize(
    prize_id: int,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Delete a specific prize"""
    prize = db.query(MonthlyPrize).filter(MonthlyPrize.id == prize_id).first()
    
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")
    
    # Verify ownership
    prize_pool = db.query(PrizePool).filter(
        PrizePool.id == prize.prize_pool_id,
        PrizePool.franchise_id == current_user.id
    ).first()
    
    if not prize_pool:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db.delete(prize)
    db.commit()
    
    return {"message": "Prize deleted successfully"}


@app.get("/api/franchise/monthly-prizes/check/{prize_pool_id}/{month_number}")
def check_monthly_prizes_configured(
    prize_pool_id: int,
    month_number: int,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Check if prizes are configured for a specific month"""
    # Verify prize pool belongs to franchise
    prize_pool = db.query(PrizePool).filter(
        PrizePool.id == prize_pool_id,
        PrizePool.franchise_id == current_user.id
    ).first()
    
    if not prize_pool:
        raise HTTPException(status_code=404, detail="Prize pool not found")
    
    # Check if any prizes exist for this month
    prizes = db.query(MonthlyPrize).filter(
        MonthlyPrize.prize_pool_id == prize_pool_id,
        MonthlyPrize.month_number == month_number
    ).all()
    
    total_winners = sum(prize.quantity for prize in prizes)
    
    return {
        "configured": len(prizes) > 0,
        "count": len(prizes),
        "total_winners": total_winners,
        "prizes": [{
            "prize_rank": prize.prize_rank,
            "prize_name": prize.prize_name,
            "prize_amount": prize.prize_amount,
            "quantity": prize.quantity
        } for prize in prizes]
    }


# ==================== DRAW SCHEDULING ====================

@app.post("/api/franchise/draws/schedule", response_model=DrawScheduleResponse)
def schedule_draw(
    draw_data: DrawScheduleCreate,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Schedule a draw for a specific group and month"""
    from models import DrawSchedule
    from datetime import datetime as dt
    
    # Verify group belongs to franchise
    group = db.query(Group).filter(
        Group.id == draw_data.group_id,
        Group.franchise_id == current_user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Check if draw already scheduled for this month
    existing = db.query(DrawSchedule).filter(
        DrawSchedule.group_id == draw_data.group_id,
        DrawSchedule.month_number == draw_data.month_number
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Draw already scheduled for month {draw_data.month_number}")
    
    # VALIDATE: Check if prizes are configured for this month (NEW MULTI-WINNER SYSTEM)
    plan = db.query(Plan).filter(Plan.id == group.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    prize_pool = db.query(PrizePool).filter(PrizePool.id == plan.prize_pool_id).first()
    if not prize_pool:
        raise HTTPException(status_code=404, detail="Prize pool not found")
    
    # Check monthly_prizes table
    monthly_prizes = db.query(MonthlyPrize).filter(
        MonthlyPrize.prize_pool_id == prize_pool.id,
        MonthlyPrize.month_number == draw_data.month_number
    ).all()
    
    if not monthly_prizes or len(monthly_prizes) == 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No prizes configured for month {draw_data.month_number}. Please configure prizes before scheduling the draw."
        )
    
    total_winners = sum(prize.quantity for prize in monthly_prizes)
    
    # Create draw schedule
    draw_schedule = DrawSchedule(
        group_id=draw_data.group_id,
        franchise_id=current_user.id,
        month_number=draw_data.month_number,
        draw_date=dt.strptime(draw_data.draw_date, "%Y-%m-%d"),
        draw_time=draw_data.draw_time,
        status="scheduled"
    )
    
    db.add(draw_schedule)
    db.commit()
    db.refresh(draw_schedule)
    
    print(f"✅ Draw scheduled for Month {draw_data.month_number} - {len(monthly_prizes)} prizes, {total_winners} total winners")
    
    return draw_schedule

@app.get("/api/franchise/draws/scheduled")
def get_scheduled_draws(
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Get all scheduled draws for this franchise"""
    from models import DrawSchedule
    
    draws = db.query(DrawSchedule).filter(
        DrawSchedule.franchise_id == current_user.id,
        DrawSchedule.status == "scheduled"
    ).order_by(DrawSchedule.draw_date.asc()).all()
    
    # Enhance with group info and eligible users count
    result = []
    for draw in draws:
        group = db.query(Group).filter(Group.id == draw.group_id).first()
        
        # Count eligible users
        # User is eligible if:
        # 1. Has active enrollment in this group
        # 2. Has NOT won a prize yet
        # 3. Has paid for this month (months_paid >= month_number)
        eligible_count = db.query(Enrollment).filter(
            Enrollment.group_id == draw.group_id,
            Enrollment.status == PlanStatus.ACTIVE,
            Enrollment.has_won_prize == False,
            Enrollment.months_paid >= draw.month_number
        ).count()
        
        result.append({
            "id": draw.id,
            "group_id": draw.group_id,
            "group_name": group.group_name if group else "Unknown",
            "month_number": draw.month_number,
            "draw_date": draw.draw_date,
            "draw_time": draw.draw_time,
            "eligible_users_count": eligible_count,
            "status": draw.status
        })
    
    return result

@app.post("/api/franchise/draws/{draw_id}/conduct")
def conduct_draw(
    draw_id: int,
    background_tasks: BackgroundTasks,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Conduct the draw - Set to live immediately, select winner after delay"""
    from models import DrawSchedule
    
    # Get draw schedule
    draw = db.query(DrawSchedule).filter(
        DrawSchedule.id == draw_id,
        DrawSchedule.franchise_id == current_user.id
    ).first()
    
    if not draw:
        raise HTTPException(status_code=404, detail="Draw not found")
    
    if draw.status != "scheduled":
        raise HTTPException(status_code=400, detail="Draw already conducted or cancelled")
    
    # Update draw status to "live" immediately
    draw.status = "live"
    draw.conducted_by = current_user.id
    db.commit()
    
    print(f"🔴 Draw {draw_id} set to LIVE! Winner will be selected in 100 seconds...")
    
    # Schedule background task to select winner after 100 seconds
    background_tasks.add_task(select_draw_winner, draw_id)
    
    return {
        "success": True,
        "message": "Draw is now LIVE! Winner will be selected in 100 seconds.",
        "draw_id": draw_id,
        "status": "live",
        "live_duration": 100
    }


def select_draw_winner(draw_id: int):
    """Background task to select multiple winners after 100-second delay (MULTI-WINNER SYSTEM)"""
    import time
    from models import DrawSchedule, DrawResult, MonthlyPrize
    import random
    from database import SessionLocal
    
    # Wait for 100 seconds to let users watch animation
    print(f"⏳ Waiting 100 seconds for draw {draw_id} animation...")
    time.sleep(100)
    
    # Create new DB session for background task
    db = SessionLocal()
    
    try:
        print(f"🎯 Selecting winners for draw {draw_id}...")
        
        # Get draw schedule
        draw = db.query(DrawSchedule).filter(DrawSchedule.id == draw_id).first()
        
        if not draw or draw.status != "live":
            print(f"❌ Draw {draw_id} not found or not live anymore")
            return
        
        # Get group and plan
        group = db.query(Group).filter(Group.id == draw.group_id).first()
        plan = db.query(Plan).filter(Plan.id == group.plan_id).first()
        prize_pool = db.query(PrizePool).filter(PrizePool.id == plan.prize_pool_id).first()
        
        # Get monthly prizes for this month (ordered by rank)
        monthly_prizes = db.query(MonthlyPrize).filter(
            MonthlyPrize.prize_pool_id == prize_pool.id,
            MonthlyPrize.month_number == draw.month_number
        ).order_by(MonthlyPrize.prize_rank).all()
        
        if not monthly_prizes:
            print(f"❌ No prizes configured for month {draw.month_number}")
            draw.status = "completed"
            db.commit()
            return
        
        # Get eligible enrollments (users who haven't won yet and paid enough)
        eligible_enrollments = db.query(Enrollment).filter(
            Enrollment.group_id == draw.group_id,
            Enrollment.status == PlanStatus.ACTIVE,
            Enrollment.has_won_prize == False,
            Enrollment.months_paid >= draw.month_number
        ).all()
        
        if not eligible_enrollments:
            print(f"❌ No eligible users for draw {draw_id}")
            draw.status = "completed"
            db.commit()
            return
        
        # Generate unique coupon code
        def generate_coupon_code(db_session, group_id):
            """Generate unique coupon code in format WINNER-{0001}-GROUP{id}"""
            from models import CouponCounter
            
            counter = db_session.query(CouponCounter).first()
            if not counter:
                counter = CouponCounter(last_number=0)
                db_session.add(counter)
                db_session.flush()
            
            counter.last_number += 1
            coupon_number = str(counter.last_number).zfill(4)
            return f"WINNER-{coupon_number}-GROUP{group_id}"
        
        # Select winners for each prize
        all_winners = []
        remaining_eligible = list(eligible_enrollments)
        
        for prize in monthly_prizes:
            print(f"\n🎁 Selecting {prize.quantity} winner(s) for Prize #{prize.prize_rank}: {prize.prize_name} (₹{prize.prize_amount})")
            
            # Check if enough eligible users remain
            if len(remaining_eligible) < prize.quantity:
                print(f"⚠️ Only {len(remaining_eligible)} eligible users left, but need {prize.quantity} for this prize")
                # Select as many as possible
                selected_count = len(remaining_eligible)
            else:
                selected_count = prize.quantity
            
            # Randomly select winners for this prize
            winners_for_this_prize = random.sample(remaining_eligible, selected_count)
            
            for winner_enrollment in winners_for_this_prize:
                winner_user = db.query(User).filter(User.id == winner_enrollment.user_id).first()
                
                # Generate coupon code
                coupon_code = generate_coupon_code(db, draw.group_id)
                
                # Update winner's enrollment with coupon
                winner_enrollment.has_won_prize = True
                winner_enrollment.prize_won_month = draw.month_number
                winner_enrollment.prize_name = prize.prize_name
                winner_enrollment.prize_amount = prize.prize_amount
                winner_enrollment.coupon_code = coupon_code
                winner_enrollment.coupon_status = "pending"
                winner_enrollment.status = PlanStatus.COMPLETED_WON
                winner_enrollment.ended_at = datetime.utcnow()
                winner_enrollment.is_eligible_for_draw = False
                
                # Create draw result
                draw_result = DrawResult(
                    draw_schedule_id=draw.id,
                    group_id=draw.group_id,
                    enrollment_id=winner_enrollment.id,
                    user_id=winner_user.id,
                    prize_name=prize.prize_name,
                    prize_amount=prize.prize_amount,
                    month_number=draw.month_number
                )
                db.add(draw_result)
                
                all_winners.append({
                    "rank": prize.prize_rank,
                    "user": winner_user.full_name,
                    "mld_id": winner_user.mld_id,
                    "prize": prize.prize_name,
                    "amount": prize.prize_amount,
                    "coupon": coupon_code
                })
                
                print(f"   🏆 Winner: {winner_user.full_name} ({winner_user.mld_id}) - Coupon: {coupon_code}")
                
                # Remove from eligible pool
                remaining_eligible.remove(winner_enrollment)
            
            # Break if no more eligible users
            if len(remaining_eligible) == 0:
                print(f"⚠️ No more eligible users remaining")
                break
        
        # Update draw status to completed
        draw.status = "completed"
        draw.conducted_at = datetime.utcnow()
        
        db.commit()
        
        print(f"\n✅ Draw {draw_id} completed! Total winners: {len(all_winners)}")
        for winner in all_winners:
            print(f"   Rank {winner['rank']}: {winner['user']} - {winner['prize']} (₹{winner['amount']}) - {winner['coupon']}")
        
    except Exception as e:
        print(f"❌ Error selecting winner for draw {draw_id}: {e}")
        db.rollback()
    finally:
        db.close()

@app.get("/api/franchise/draws/history")
def get_draw_history(
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Get all completed draws for this franchise"""
    from models import DrawSchedule, DrawResult
    
    draws = db.query(DrawSchedule).filter(
        DrawSchedule.franchise_id == current_user.id,
        DrawSchedule.status == "completed"
    ).order_by(DrawSchedule.conducted_at.desc()).all()
    
    result = []
    for draw in draws:
        draw_result = db.query(DrawResult).filter(
            DrawResult.draw_schedule_id == draw.id
        ).first()
        
        group = db.query(Group).filter(Group.id == draw.group_id).first()
        winner = db.query(User).filter(User.id == draw_result.user_id).first() if draw_result else None
        
        result.append({
            "id": draw.id,
            "group_id": draw.group_id,
            "group_name": group.group_name if group else "Unknown",
            "month_number": draw.month_number,
            "draw_date": draw.draw_date,
            "conducted_at": draw.conducted_at,
            "winner": {
                "full_name": winner.full_name,
                "mld_id": winner.mld_id
            } if winner else None,
            "prize_name": draw_result.prize_name if draw_result else None,
            "prize_amount": draw_result.prize_amount if draw_result else None
        })
    
    return result

# ============== HEALTH CHECK ==============

@app.get("/")
def root():
    return {
        "message": "Millance Rewards API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ============== REFERRAL SYSTEM ROUTES ==============

@app.get("/api/invite/{franchise_slug}/{invite_code}", response_model=InviteLinkValidation)
def validate_invite_link(franchise_slug: str, invite_code: str, db: Session = Depends(get_db)):
    """Validate invite link and return group details"""
    # Get franchise by slug
    franchise = db.query(Franchise).filter(Franchise.franchise_slug == franchise_slug).first()
    if not franchise:
        raise HTTPException(status_code=404, detail="Invalid invite link - Franchise not found")
    
    # Get group by invite code
    group = db.query(Group).filter(
        Group.invite_code == invite_code,
        Group.franchise_id == franchise.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Invalid invite link - Group not found")
    
    # Get plan details
    plan = db.query(Plan).filter(Plan.id == group.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Get prize pool
    prize_pool = db.query(PrizePool).filter(PrizePool.id == plan.prize_pool_id).first()
    
    return {
        "franchise_name": franchise.franchise_name,
        "franchise_slug": franchise.franchise_slug,
        "group_name": group.group_name,
        "group_id": group.group_id,
        "invite_code": group.invite_code,
        "plan_name": plan.name,
        "monthly_amount": plan.monthly_amount,
        "duration_months": plan.duration_months,
        "max_members": group.max_members,
        "current_members": group.current_members,
        "prizes": prize_pool.prizes if prize_pool else []
    }

@app.post("/api/auth/register-with-invite", response_model=TokenResponse)
def register_with_invite(user_data: RegisterWithInviteRequest, db: Session = Depends(get_db)):
    """Register user with referral tracking and auto-enroll in group"""
    # Check if email exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Get franchise by slug
    franchise = db.query(Franchise).filter(Franchise.franchise_slug == user_data.franchise_slug).first()
    if not franchise:
        raise HTTPException(status_code=404, detail="Franchise not found")
    
    # Get group by invite code
    group = db.query(Group).filter(
        Group.invite_code == user_data.invite_code,
        Group.franchise_id == franchise.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Check if group is full
    if group.current_members >= group.max_members:
        raise HTTPException(status_code=400, detail="Group is full")
    
    # Create new user with referral tracking
    new_user = User(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=UserRole.USER,
        millance_rewards_wallet=0.0,
        savings_wallet=0.0,
        referred_by_franchise_id=franchise.id,
        referred_by_group_id=group.id
    )
    db.add(new_user)
    db.flush()  # Get user ID
    
    # Auto-enroll user in the group
    plan = db.query(Plan).filter(Plan.id == group.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=plan.duration_months * 30)
    
    enrollment = Enrollment(
        user_id=new_user.id,
        plan_id=plan.id,
        group_id=group.id,
        start_date=start_date,
        end_date=end_date,
        status=PlanStatus.ACTIVE,
        commission_rate=0.15  # 15% commission
    )
    db.add(enrollment)
    
    # Update group member count
    group.current_members += 1
    plan.current_members += 1
    
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": new_user.email, "role": UserRole.USER.value}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": UserRole.USER,
        "user_data": {
            "id": new_user.id,
            "mld_id": new_user.mld_id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "millance_rewards_wallet": new_user.millance_rewards_wallet,
            "savings_wallet": new_user.savings_wallet
        }
    }


@app.post("/api/enrollments/join-with-invite")
def join_group_with_invite(
    invite_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allow existing logged-in users to join a group via invite link
    """
    franchise_slug = invite_data.get("franchise_slug")
    invite_code = invite_data.get("invite_code")
    
    if not franchise_slug or not invite_code:
        raise HTTPException(status_code=400, detail="Missing franchise_slug or invite_code")
    
    # Get franchise by slug
    franchise = db.query(Franchise).filter(Franchise.franchise_slug == franchise_slug).first()
    if not franchise:
        raise HTTPException(status_code=404, detail="Franchise not found")
    
    # Get group by invite code
    group = db.query(Group).filter(
        Group.invite_code == invite_code,
        Group.franchise_id == franchise.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Check if group is full
    if group.current_members >= group.max_members:
        raise HTTPException(status_code=400, detail="Group is full - Maximum members reached")
    
    # Check if user is already enrolled in this group
    existing_enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.group_id == group.id
    ).first()
    
    if existing_enrollment:
        raise HTTPException(status_code=400, detail="You are already enrolled in this group")
    
    # Get plan details
    plan = db.query(Plan).filter(Plan.id == group.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Create enrollment for existing user
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=plan.duration_months * 30)
    
    enrollment = Enrollment(
        user_id=current_user.id,
        plan_id=plan.id,
        group_id=group.id,
        start_date=start_date,
        end_date=end_date,
        status=PlanStatus.ACTIVE,
        commission_rate=0.15  # 15% commission for existing users too
    )
    db.add(enrollment)
    
    # Update group member count
    group.current_members += 1
    plan.current_members += 1
    
    # If user doesn't have referral tracking yet, add it
    if not current_user.referred_by_franchise_id:
        current_user.referred_by_franchise_id = franchise.id
        current_user.referred_by_group_id = group.id
    
    db.commit()
    db.refresh(enrollment)
    
    return {
        "success": True,
        "message": "Successfully joined the group!",
        "enrollment_id": enrollment.id,
        "group_id": group.group_id,
        "group_name": group.group_name,
        "plan_name": plan.name,
        "monthly_amount": plan.monthly_amount,
        "duration_months": plan.duration_months
    }


@app.get("/api/franchise/referrals", response_model=ReferralListResponse)
def get_franchise_referrals(
    page: int = 1,
    limit: int = 20,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Get all referred users for this franchise with pagination"""
    from sqlalchemy import func
    from models import FranchiseEarning
    
    # Get all users referred by this franchise
    query = db.query(User).filter(User.referred_by_franchise_id == current_user.id)
    
    total_users = query.count()
    total_pages = (total_users + limit - 1) // limit
    
    users = query.offset((page - 1) * limit).limit(limit).all()
    
    referral_list = []
    for user in users:
        # Get user's enrollment
        enrollment = db.query(Enrollment).filter(
            Enrollment.user_id == user.id,
            Enrollment.group_id == user.referred_by_group_id
        ).first()
        
        if enrollment:
            # Get plan details
            plan = db.query(Plan).filter(Plan.id == enrollment.plan_id).first()
            group = db.query(Group).filter(Group.id == enrollment.group_id).first()
            
            # Calculate commission earned
            commission_earned = db.query(func.sum(FranchiseEarning.amount)).filter(
                FranchiseEarning.franchise_id == current_user.id,
                FranchiseEarning.user_id == user.id
            ).scalar() or 0.0
            
            referral_list.append({
                "user_id": user.id,
                "mld_id": user.mld_id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "group_name": group.group_name if group else "N/A",
                "monthly_amount": plan.monthly_amount if plan else 0,
                "duration_months": plan.duration_months if plan else 0,
                "payments_made": enrollment.months_paid,
                "total_payments": plan.duration_months if plan else 0,
                "total_paid": enrollment.total_paid,
                "commission_earned": commission_earned
            })
    
    return {
        "users": referral_list,
        "total_users": total_users,
        "page": page,
        "total_pages": total_pages
    }

@app.get("/api/franchise/referrals/{user_id}", response_model=ReferralUserDetailsResponse)
def get_referral_user_details(
    user_id: int,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Get detailed information for a specific referred user"""
    from sqlalchemy import func
    from models import FranchiseEarning
    
    # Verify user was referred by this franchise
    user = db.query(User).filter(
        User.id == user_id,
        User.referred_by_franchise_id == current_user.id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found or not referred by you")
    
    # Get enrollment
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == user.id,
        Enrollment.group_id == user.referred_by_group_id
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Get plan and group
    plan = db.query(Plan).filter(Plan.id == enrollment.plan_id).first()
    group = db.query(Group).filter(Group.id == enrollment.group_id).first()
    
    # Get payment history with commissions
    payments = db.query(Payment).filter(
        Payment.user_id == user.id,
        Payment.enrollment_id == enrollment.id
    ).order_by(Payment.payment_date.desc()).all()
    
    payment_list = []
    for payment in payments:
        # Get commission for this payment
        earning = db.query(FranchiseEarning).filter(
            FranchiseEarning.payment_id == payment.id,
            FranchiseEarning.franchise_id == current_user.id
        ).first()
        
        payment_list.append({
            "id": payment.id,
            "month": payment.month,
            "amount": payment.amount,
            "payment_date": payment.payment_date.isoformat(),
            "commission_earned": earning.amount if earning else 0.0
        })
    
    # Calculate total commission
    total_commission = db.query(func.sum(FranchiseEarning.amount)).filter(
        FranchiseEarning.franchise_id == current_user.id,
        FranchiseEarning.user_id == user.id
    ).scalar() or 0.0
    
    return {
        "user_id": user.id,
        "mld_id": user.mld_id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "group_name": group.group_name if group else "N/A",
        "monthly_amount": plan.monthly_amount if plan else 0,
        "duration_months": plan.duration_months if plan else 0,
        "payments_made": enrollment.months_paid,
        "total_payments": plan.duration_months if plan else 0,
        "total_paid": enrollment.total_paid,
        "commission_earned": total_commission,
        "payments": payment_list
    }

@app.get("/api/franchise/earnings", response_model=FranchiseEarningsResponse)
def get_franchise_earnings(
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Get earnings summary for franchise"""
    from sqlalchemy import func
    from models import FranchiseEarning
    
    # Total earnings from commissions
    total_earnings = db.query(func.sum(FranchiseEarning.amount)).filter(
        FranchiseEarning.franchise_id == current_user.id
    ).scalar() or 0.0
    
    # Total referred users
    total_referred = db.query(func.count(User.id)).filter(
        User.referred_by_franchise_id == current_user.id
    ).scalar() or 0
    
    # Active referred users (have active enrollments)
    active_referred = db.query(func.count(User.id)).join(Enrollment).filter(
        User.referred_by_franchise_id == current_user.id,
        Enrollment.status == PlanStatus.ACTIVE
    ).scalar() or 0
    
    return {
        "total_earnings": total_earnings,
        "total_referred_users": total_referred,
        "active_referred_users": active_referred,
        "earnings_wallet_balance": current_user.earnings_wallet
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)


# ============== CASHFREE PAYMENT ROUTES ==============

from cashfree_service import cashfree
from models import CashfreePayment, PaymentReconciliation
from schemas import (
    PaymentOrderCreate, PaymentOrderResponse, 
    PaymentVerifyRequest, PaymentVerifyResponse,
    CashfreePaymentResponse, PaymentHistoryResponse
)

@app.post("/api/payments/create-order", response_model=PaymentOrderResponse)
def create_payment_order(
    order_data: PaymentOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new payment order with Cashfree
    User wants to add money to wallet
    """
    
    # Validate amount
    if order_data.amount < 1 or order_data.amount > 10000:
        raise HTTPException(
            status_code=400,
            detail="Amount must be between ₹1 and ₹10,000"
        )
    
    # Generate unique order ID
    timestamp = int(datetime.utcnow().timestamp())
    order_id = f"order_MLR_{timestamp}_{current_user.id}"
    
    # Clean phone number - Cashfree requires 10 digits without country code
    phone = current_user.phone or "9999999999"
    if phone.startswith("+91"):
        phone = phone[3:].strip()
    elif phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]
    
    # Create order with Cashfree
    cf_result = cashfree.create_order(
        order_id=order_id,
        amount=order_data.amount,
        customer_id=current_user.mld_id,
        customer_name=current_user.full_name,
        customer_phone=phone,
        customer_email=current_user.email
    )
    
    if not cf_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=cf_result.get("error", "Failed to create payment order")
        )
    
    # Save payment record to database
    payment = CashfreePayment(
        user_id=current_user.id,
        order_id=order_id,
        cf_order_id=cf_result.get("cf_order_id"),
        payment_session_id=cf_result.get("payment_session_id"),
        amount=order_data.amount,
        currency="INR",
        order_status="CREATED",
        payment_status="PENDING"
    )
    
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    print(f"💾 Payment record created: {payment.id}")
    
    return {
        "success": True,
        "order_id": order_id,
        "payment_session_id": cf_result.get("payment_session_id"),
        "amount": order_data.amount
    }


@app.post("/api/payments/verify", response_model=PaymentVerifyResponse)
def verify_payment(
    verify_data: PaymentVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify payment status and credit wallet if successful
    Called after user completes payment
    """
    
    # Get payment record
    payment = db.query(CashfreePayment).filter(
        CashfreePayment.order_id == verify_data.order_id,
        CashfreePayment.user_id == current_user.id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Check if already credited
    if payment.is_credited:
        return {
            "success": True,
            "payment_status": "SUCCESS",
            "amount": payment.amount,
            "wallet_credited": True,
            "new_balance": current_user.millance_rewards_wallet
        }
    
    # Verify with Cashfree
    verification = cashfree.verify_payment(verify_data.order_id)
    
    if not verification.get("success"):
        return {
            "success": False,
            "payment_status": "FAILED",
            "amount": payment.amount,
            "error": verification.get("error", "Verification failed")
        }
    
    # Update payment record with verification data
    payment.order_status = verification.get("order_status")
    payment.payment_status = verification.get("payment_status")
    payment.cf_payment_id = verification.get("cf_payment_id")
    payment.payment_method = verification.get("payment_method")
    payment.bank_reference = verification.get("bank_reference")
    payment.is_verified = True
    payment.verified_at = datetime.utcnow()
    
    if verification.get("payment_time"):
        try:
            payment.payment_time = datetime.fromisoformat(verification["payment_time"].replace("Z", "+00:00"))
        except:
            payment.payment_time = datetime.utcnow()
    
    # If payment successful, credit wallet
    if verification.get("is_paid"):
        try:
            # Credit wallet
            wallet_before = current_user.millance_rewards_wallet
            current_user.millance_rewards_wallet += payment.amount
            wallet_after = current_user.millance_rewards_wallet
            
            # Update payment record
            payment.is_credited = True
            payment.credited_at = datetime.utcnow()
            payment.wallet_before = wallet_before
            payment.wallet_after = wallet_after
            
            # Create transaction record
            transaction = Transaction(
                user_id=current_user.id,
                transaction_type="deposit",
                amount=payment.amount,
                wallet="millance_rewards_wallet",
                description=f"Wallet recharge via Cashfree - Order {payment.order_id}",
                balance_before=wallet_before,
                balance_after=wallet_after
            )
            db.add(transaction)
            
            db.commit()
            db.refresh(payment)
            
            print(f"💰 Wallet credited: ₹{payment.amount} → User {current_user.mld_id}")
            
            return {
                "success": True,
                "payment_status": "SUCCESS",
                "amount": payment.amount,
                "wallet_credited": True,
                "new_balance": wallet_after,
                "transaction_id": transaction.id
            }
            
        except Exception as e:
            # Wallet credit failed - create reconciliation record
            print(f"❌ Failed to credit wallet: {str(e)}")
            
            reconciliation = PaymentReconciliation(
                payment_id=payment.id,
                issue_type="CREDIT_FAILED",
                cf_status="SUCCESS",
                our_status="FAILED"
            )
            db.add(reconciliation)
            db.commit()
            
            payment.error_code = "CREDIT_FAILED"
            payment.error_message = str(e)
            db.commit()
            
            return {
                "success": False,
                "payment_status": "SUCCESS",
                "amount": payment.amount,
                "wallet_credited": False,
                "error": "Payment successful but wallet credit failed. Contact support."
            }
    
    else:
        # Payment not successful
        db.commit()
        
        return {
            "success": False,
            "payment_status": verification.get("payment_status", "FAILED"),
            "amount": payment.amount,
            "wallet_credited": False,
            "error": "Payment was not successful"
        }


@app.get("/api/payments/history")
def get_payment_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's payment history"""
    
    payments = db.query(CashfreePayment).filter(
        CashfreePayment.user_id == current_user.id
    ).order_by(
        CashfreePayment.created_at.desc()
    ).limit(limit).all()
    
    return {
        "payments": payments,
        "total": len(payments)
    }


@app.get("/api/payments/{payment_id}")
def get_payment_details(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific payment"""
    
    payment = db.query(CashfreePayment).filter(
        CashfreePayment.id == payment_id,
        CashfreePayment.user_id == current_user.id
    ).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return payment


# ============== ADMIN PAYMENT ROUTES ==============

@app.get("/api/admin/payments/issues")
def get_payment_issues(
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get all unresolved payment issues"""
    
    issues = db.query(PaymentReconciliation).filter(
        PaymentReconciliation.is_resolved == False
    ).order_by(
        PaymentReconciliation.created_at.desc()
    ).all()
    
    result = []
    for issue in issues:
        payment = issue.payment
        user = db.query(User).filter(User.id == payment.user_id).first()
        
        result.append({
            "id": issue.id,
            "payment_id": payment.id,
            "order_id": payment.order_id,
            "user": {
                "id": user.id,
                "name": user.full_name,
                "mld_id": user.mld_id,
                "email": user.email
            },
            "amount": payment.amount,
            "issue_type": issue.issue_type,
            "cf_status": issue.cf_status,
            "our_status": issue.our_status,
            "created_at": issue.created_at,
            "is_resolved": issue.is_resolved
        })
    
    return {"issues": result}


@app.post("/api/admin/payments/manual-credit")
def manual_credit_wallet(
    reconciliation_id: int,
    notes: str,
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Manually credit wallet for a failed payment"""
    
    # Get reconciliation record
    reconciliation = db.query(PaymentReconciliation).filter(
        PaymentReconciliation.id == reconciliation_id
    ).first()
    
    if not reconciliation:
        raise HTTPException(status_code=404, detail="Reconciliation record not found")
    
    if reconciliation.is_resolved:
        raise HTTPException(status_code=400, detail="Already resolved")
    
    # Get payment
    payment = reconciliation.payment
    
    if payment.is_credited:
        raise HTTPException(status_code=400, detail="Wallet already credited")
    
    # Verify with Cashfree one more time
    verification = cashfree.verify_payment(payment.order_id)
    
    if not verification.get("is_paid"):
        raise HTTPException(
            status_code=400,
            detail="Payment not successful in Cashfree. Cannot credit."
        )
    
    # Credit wallet
    user = db.query(User).filter(User.id == payment.user_id).first()
    
    wallet_before = user.millance_rewards_wallet
    user.millance_rewards_wallet += payment.amount
    wallet_after = user.millance_rewards_wallet
    
    # Update payment
    payment.is_credited = True
    payment.credited_at = datetime.utcnow()
    payment.wallet_before = wallet_before
    payment.wallet_after = wallet_after
    
    # Create transaction
    transaction = Transaction(
        user_id=user.id,
        transaction_type="deposit",
        amount=payment.amount,
        wallet="millance_rewards_wallet",
        description=f"Manual credit by admin - Order {payment.order_id}",
        balance_before=wallet_before,
        balance_after=wallet_after
    )
    db.add(transaction)
    
    # Mark reconciliation as resolved
    reconciliation.is_resolved = True
    reconciliation.resolved_by = current_user.id
    reconciliation.resolved_at = datetime.utcnow()
    reconciliation.resolution_notes = notes
    reconciliation.action_taken = "MANUAL_CREDIT"
    
    db.commit()
    
    print(f"✅ Admin manual credit: ₹{payment.amount} → User {user.mld_id}")
    
    return {
        "success": True,
        "wallet_credited": True,
        "new_balance": wallet_after,
        "amount": payment.amount
    }


# ============== COUPON MANAGEMENT ENDPOINTS ==============

@app.get("/api/users/my-winnings")
def get_my_winnings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all user winnings with coupon codes (NO AMOUNTS in response)"""
    
    # Find all enrollments where user has won
    winnings = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.has_won_prize == True
    ).order_by(Enrollment.prize_won_month).all()
    
    winnings_list = []
    for enrollment in winnings:
        # Get group and plan info
        group = db.query(Group).filter(Group.id == enrollment.group_id).first()
        plan = db.query(Plan).filter(Plan.id == enrollment.plan_id).first()
        
        winnings_list.append({
            "enrollment_id": enrollment.id,
            "prize_name": enrollment.prize_name,
            # NO prize_amount in response
            "coupon_code": enrollment.coupon_code,
            "coupon_status": enrollment.coupon_status,
            "won_month": enrollment.prize_won_month,
            "won_date": enrollment.ended_at.isoformat() if enrollment.ended_at else None,
            "group_id": enrollment.group_id,
            "group_name": group.group_name if group else None,
            "plan_name": plan.name if plan else None,
            "redeemed_at": enrollment.redeemed_at.isoformat() if enrollment.redeemed_at else None
        })
    
    return {"winnings": winnings_list}

@app.get("/api/users/recent-winners")
def get_recent_winners(
    db: Session = Depends(get_db)
):
    """Get last 5 recent winners across all users (public endpoint)"""
    
    # Find all enrollments where users have won, ordered by most recent
    recent_winnings = db.query(Enrollment).filter(
        Enrollment.has_won_prize == True,
        Enrollment.coupon_code != None
    ).order_by(Enrollment.ended_at.desc()).limit(5).all()
    
    winners_list = []
    for enrollment in recent_winnings:
        # Get user details
        user = db.query(User).filter(User.id == enrollment.user_id).first()
        
        # Get group and plan info
        group = db.query(Group).filter(Group.id == enrollment.group_id).first()
        plan = db.query(Plan).filter(Plan.id == enrollment.plan_id).first()
        
        if user:  # Only add if user exists
            winners_list.append({
                "enrollment_id": enrollment.id,
                "prize_name": enrollment.prize_name,
                "coupon_code": enrollment.coupon_code,
                "coupon_status": enrollment.coupon_status,
                "won_month": enrollment.prize_won_month,
                "won_date": enrollment.ended_at.isoformat() if enrollment.ended_at else None,
                "group_id": enrollment.group_id,
                "group_name": group.group_name if group else None,
                "plan_name": plan.name if plan else None,
                "winner_mld_id": user.mld_id,
                "winner_name": user.full_name,
                "winner_profile_photo": user.profile_photo
            })
    
    return {"recent_winners": winners_list}

@app.get("/api/admin/coupons/search")
def search_coupon(
    code: str,
    current_user = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Search for coupon by code (Admin only)"""
    
    enrollment = db.query(Enrollment).filter(
        Enrollment.coupon_code == code.upper()
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    # Get user details
    user = db.query(User).filter(User.id == enrollment.user_id).first()
    
    # Get group and plan details
    group = db.query(Group).filter(Group.id == enrollment.group_id).first()
    plan = db.query(Plan).filter(Plan.id == enrollment.plan_id).first()
    
    return {
        "coupon_code": enrollment.coupon_code,
        "coupon_status": enrollment.coupon_status,
        "prize_name": enrollment.prize_name,
        # NO prize_amount shown
        "won_date": enrollment.ended_at.isoformat() if enrollment.ended_at else None,
        "won_month": enrollment.prize_won_month,
        "user": {
            "id": user.id,
            "mld_id": user.mld_id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "profile_photo": user.profile_photo
        },
        "group": {
            "id": group.id,
            "group_id": group.group_id,
            "group_name": group.group_name
        } if group else None,
        "plan": {
            "id": plan.id,
            "name": plan.name
        } if plan else None,
        "redeemed_at": enrollment.redeemed_at.isoformat() if enrollment.redeemed_at else None,
        "redeemed_by_admin_id": enrollment.redeemed_by_admin_id,
        "redeemed_by_franchise_id": enrollment.redeemed_by_franchise_id
    }

@app.post("/api/admin/coupons/redeem")
def redeem_coupon(
    redeem_data: dict,
    current_user: Admin = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Mark coupon as redeemed (Admin only)"""
    
    coupon_code = redeem_data.get("coupon_code")
    if not coupon_code:
        raise HTTPException(status_code=400, detail="Coupon code required")
    
    enrollment = db.query(Enrollment).filter(
        Enrollment.coupon_code == coupon_code.upper()
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    if enrollment.coupon_status == "redeemed":
        raise HTTPException(status_code=400, detail="Coupon already redeemed")
    
    # Mark as redeemed
    enrollment.coupon_status = "redeemed"
    enrollment.redeemed_at = datetime.utcnow()
    enrollment.redeemed_by_admin_id = current_user.id
    
    db.commit()
    
    return {
        "message": "Coupon redeemed successfully",
        "coupon_code": coupon_code,
        "prize_name": enrollment.prize_name,
        "redeemed_at": enrollment.redeemed_at.isoformat()
    }

@app.get("/api/admin/coupons/pending")
def get_pending_coupons(
    current_user = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get all pending (unredeemed) coupons (Admin only)"""
    
    enrollments = db.query(Enrollment).filter(
        Enrollment.has_won_prize == True,
        Enrollment.coupon_status == "pending"
    ).order_by(Enrollment.ended_at.desc()).all()
    
    coupons_list = []
    for enrollment in enrollments:
        user = db.query(User).filter(User.id == enrollment.user_id).first()
        group = db.query(Group).filter(Group.id == enrollment.group_id).first()
        plan = db.query(Plan).filter(Plan.id == enrollment.plan_id).first()
        
        coupons_list.append({
            "coupon_code": enrollment.coupon_code,
            "prize_name": enrollment.prize_name,
            # NO prize_amount
            "won_date": enrollment.ended_at.isoformat() if enrollment.ended_at else None,
            "won_month": enrollment.prize_won_month,
            "user": {
                "mld_id": user.mld_id,
                "full_name": user.full_name,
                "phone": user.phone
            },
            "group": {
                "group_id": group.group_id,
                "group_name": group.group_name
            } if group else None,
            "plan_name": plan.name if plan else None
        })
    
    return {"pending_coupons": coupons_list}

@app.get("/api/admin/coupons/redeemed")
def get_redeemed_coupons(
    current_user = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get all redeemed coupons (Admin only)"""
    
    enrollments = db.query(Enrollment).filter(
        Enrollment.has_won_prize == True,
        Enrollment.coupon_status == "redeemed"
    ).order_by(Enrollment.redeemed_at.desc()).all()
    
    coupons_list = []
    for enrollment in enrollments:
        user = db.query(User).filter(User.id == enrollment.user_id).first()
        group = db.query(Group).filter(Group.id == enrollment.group_id).first()
        
        # Get admin who redeemed
        redeemed_by = None
        if enrollment.redeemed_by_admin_id:
            admin = db.query(Admin).filter(Admin.id == enrollment.redeemed_by_admin_id).first()
            if admin:
                redeemed_by = admin.full_name
        
        coupons_list.append({
            "coupon_code": enrollment.coupon_code,
            "prize_name": enrollment.prize_name,
            # NO prize_amount
            "won_date": enrollment.ended_at.isoformat() if enrollment.ended_at else None,
            "redeemed_at": enrollment.redeemed_at.isoformat() if enrollment.redeemed_at else None,
            "user": {
                "mld_id": user.mld_id,
                "full_name": user.full_name,
                "phone": user.phone
            },
            "group": {
                "group_id": group.group_id,
                "group_name": group.group_name
            } if group else None,
            "redeemed_by": redeemed_by
        })
    
    return {"redeemed_coupons": coupons_list}

@app.get("/api/franchise/coupons/my-groups")
def get_franchise_coupons(
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Get all coupons for franchise groups (Franchise only)"""
    
    # Get all groups belonging to this franchise
    groups = db.query(Group).filter(Group.franchise_id == current_user.id).all()
    group_ids = [g.id for g in groups]
    
    # Get all winning enrollments from these groups
    enrollments = db.query(Enrollment).filter(
        Enrollment.group_id.in_(group_ids),
        Enrollment.has_won_prize == True
    ).order_by(Enrollment.ended_at.desc()).all()
    
    coupons_list = []
    for enrollment in enrollments:
        user = db.query(User).filter(User.id == enrollment.user_id).first()
        group = db.query(Group).filter(Group.id == enrollment.group_id).first()
        plan = db.query(Plan).filter(Plan.id == enrollment.plan_id).first()
        
        coupons_list.append({
            "coupon_code": enrollment.coupon_code,
            "coupon_status": enrollment.coupon_status,
            "prize_name": enrollment.prize_name,
            # NO prize_amount
            "won_date": enrollment.ended_at.isoformat() if enrollment.ended_at else None,
            "won_month": enrollment.prize_won_month,
            "user": {
                "mld_id": user.mld_id,
                "full_name": user.full_name,
                "phone": user.phone
            },
            "group": {
                "group_id": group.group_id,
                "group_name": group.group_name
            } if group else None,
            "plan_name": plan.name if plan else None,
            "redeemed_at": enrollment.redeemed_at.isoformat() if enrollment.redeemed_at else None
        })
    
    return {"coupons": coupons_list}

@app.post("/api/franchise/coupons/redeem")
def franchise_redeem_coupon(
    redeem_data: dict,
    current_user: Franchise = Depends(require_role(UserRole.FRANCHISE)),
    db: Session = Depends(get_db)
):
    """Mark coupon as redeemed (Franchise only - for their own groups)"""
    
    coupon_code = redeem_data.get("coupon_code")
    if not coupon_code:
        raise HTTPException(status_code=400, detail="Coupon code required")
    
    enrollment = db.query(Enrollment).filter(
        Enrollment.coupon_code == coupon_code.upper()
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    # Verify this coupon belongs to franchise's group
    group = db.query(Group).filter(Group.id == enrollment.group_id).first()
    if not group or group.franchise_id != current_user.id:
        raise HTTPException(status_code=403, detail="This coupon does not belong to your franchise")
    
    if enrollment.coupon_status == "redeemed":
        raise HTTPException(status_code=400, detail="Coupon already redeemed")
    
    # Mark as redeemed
    enrollment.coupon_status = "redeemed"
    enrollment.redeemed_at = datetime.utcnow()
    enrollment.redeemed_by_franchise_id = current_user.id
    
    db.commit()
    
    return {
        "message": "Coupon redeemed successfully",
        "coupon_code": coupon_code,
        "prize_name": enrollment.prize_name,
        "redeemed_at": enrollment.redeemed_at.isoformat()
    }
