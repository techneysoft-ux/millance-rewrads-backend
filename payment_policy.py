"""
Payment Deadline Policy Helper Functions
Handles all payment deadline calculations and enforcement
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from models import Enrollment, Payment, PaymentStatus

# Policy Constants
PAYMENT_DEADLINE_DAY = 5  # Payment due on 5th of each month
MAX_CONSECUTIVE_MISSES = 2  # Auto-remove after 2 consecutive missed months

def get_payment_deadline(month_number: int, enrollment_date: datetime) -> datetime:
    """
    Calculate payment deadline for a specific month
    Returns: 5th of the target month at 23:59:59
    
    Example:
    - Enrolled: Oct 1, 2026
    - Month 1 deadline: Nov 5, 2026 23:59:59
    - Month 2 deadline: Dec 5, 2026 23:59:59
    """
    # Calculate target month (enrollment month + month_number)
    target_date = enrollment_date + relativedelta(months=month_number)
    
    # Set to 5th of that month at 23:59:59
    deadline = datetime(
        year=target_date.year,
        month=target_date.month,
        day=PAYMENT_DEADLINE_DAY,
        hour=23,
        minute=59,
        second=59
    )
    
    return deadline


def get_days_overdue(deadline: datetime) -> int:
    """Calculate how many days overdue a payment is"""
    if not deadline:
        return 0
    
    now = datetime.now()
    if now <= deadline:
        return 0
    
    delta = now - deadline
    return delta.days


def get_days_until_deadline(deadline: datetime) -> int:
    """Calculate days remaining until deadline (positive = days left, negative = overdue)"""
    if not deadline:
        return 999  # No deadline set
    
    now = datetime.now()
    delta = deadline - now
    return delta.days


def is_payment_overdue(deadline: datetime) -> bool:
    """Check if payment is past deadline"""
    if not deadline:
        return False
    return datetime.now() > deadline


def get_unpaid_months(enrollment: Enrollment, db) -> list:
    """
    Get list of unpaid months for an enrollment
    Returns: List of dicts with month info and deadline status
    """
    unpaid_months = []
    
    # Get all paid payments for this enrollment
    paid_payments = db.query(Payment).filter(
        Payment.enrollment_id == enrollment.id,
        Payment.status == PaymentStatus.PAID
    ).all()
    
    paid_month_numbers = {p.month_number for p in paid_payments if p.month_number}
    
    # Check each month from 1 to months_paid + 1
    current_month = enrollment.months_paid + 1
    
    for month_num in range(1, current_month + 1):
        if month_num not in paid_month_numbers:
            deadline = get_payment_deadline(month_num, enrollment.enrollment_date)
            unpaid_months.append({
                'month_number': month_num,
                'deadline': deadline,
                'is_overdue': is_payment_overdue(deadline),
                'days_overdue': get_days_overdue(deadline) if is_payment_overdue(deadline) else 0,
                'days_until_deadline': get_days_until_deadline(deadline)
            })
    
    return unpaid_months


def calculate_total_amount_due(enrollment: Enrollment, plan_monthly_amount: float, db) -> dict:
    """
    Calculate total amount user must pay including all overdue months
    Returns: {
        'total_amount': float,
        'months_to_pay': list of month numbers,
        'breakdown': list of {month_number, amount, status}
    }
    """
    unpaid = get_unpaid_months(enrollment, db)
    
    breakdown = []
    total = 0.0
    months = []
    
    for month_info in unpaid:
        breakdown.append({
            'month_number': month_info['month_number'],
            'amount': plan_monthly_amount,
            'status': 'OVERDUE' if month_info['is_overdue'] else 'CURRENT',
            'deadline': month_info['deadline'],
            'days_overdue': month_info['days_overdue']
        })
        total += plan_monthly_amount
        months.append(month_info['month_number'])
    
    return {
        'total_amount': total,
        'months_to_pay': months,
        'breakdown': breakdown
    }


def check_and_update_consecutive_misses(enrollment: Enrollment, db) -> dict:
    """
    Check consecutive missed payments and update counter
    Returns: {
        'consecutive_misses': int,
        'should_remove': bool,
        'overdue_months': list
    }
    """
    if enrollment.is_legacy_policy:
        return {
            'consecutive_misses': 0,
            'should_remove': False,
            'overdue_months': []
        }
    
    unpaid = get_unpaid_months(enrollment, db)
    overdue_months = [m for m in unpaid if m['is_overdue']]
    
    # Count consecutive overdue months from current month backwards
    consecutive = 0
    current_expected_month = enrollment.months_paid + 1
    
    for month_num in range(current_expected_month, 0, -1):
        month_data = next((m for m in overdue_months if m['month_number'] == month_num), None)
        if month_data and month_data['is_overdue']:
            consecutive += 1
        else:
            break  # Stop at first non-overdue month
    
    # Update enrollment
    enrollment.consecutive_missed_payments = consecutive
    should_remove = consecutive >= MAX_CONSECUTIVE_MISSES
    
    return {
        'consecutive_misses': consecutive,
        'should_remove': should_remove,
        'overdue_months': overdue_months
    }


def is_eligible_for_draw(enrollment: Enrollment, db) -> dict:
    """
    Check if user is eligible for current month's draw
    Eligibility: Current month payment must be paid
    
    Returns: {
        'is_eligible': bool,
        'reason': str,
        'current_month': int,
        'current_month_paid': bool
    }
    """
    if enrollment.is_legacy_policy:
        # Old policy: Just check if any payment made
        return {
            'is_eligible': enrollment.months_paid > 0,
            'reason': 'Legacy policy - eligible if any payment made',
            'current_month': enrollment.months_paid + 1,
            'current_month_paid': True
        }
    
    if enrollment.auto_removed:
        return {
            'is_eligible': False,
            'reason': 'User removed for non-payment',
            'current_month': enrollment.months_paid + 1,
            'current_month_paid': False
        }
    
    current_month = enrollment.months_paid + 1
    
    # Check if current month is paid
    current_month_payment = db.query(Payment).filter(
        Payment.enrollment_id == enrollment.id,
        Payment.month_number == current_month,
        Payment.status == PaymentStatus.PAID
    ).first()
    
    is_paid = current_month_payment is not None
    
    return {
        'is_eligible': is_paid,
        'reason': 'Current month payment is paid' if is_paid else 'Current month payment not paid',
        'current_month': current_month,
        'current_month_paid': is_paid
    }


def auto_remove_non_payers(db):
    """
    Background job: Auto-remove users with 2+ consecutive missed payments
    Should be run daily
    """
    from models import PlanStatus
    
    # Get all active enrollments with new policy
    active_enrollments = db.query(Enrollment).filter(
        Enrollment.status == PlanStatus.ACTIVE,
        Enrollment.is_legacy_policy == False,
        Enrollment.auto_removed == False
    ).all()
    
    removed_count = 0
    
    for enrollment in active_enrollments:
        status = check_and_update_consecutive_misses(enrollment, db)
        
        if status['should_remove']:
            enrollment.auto_removed = True
            enrollment.removal_date = datetime.now()
            enrollment.status = PlanStatus.SUSPENDED
            removed_count += 1
            
            print(f"❌ Auto-removed user {enrollment.user_id} from enrollment {enrollment.id} - {status['consecutive_misses']} consecutive misses")
    
    if removed_count > 0:
        db.commit()
        print(f"\n✅ Auto-removed {removed_count} users for non-payment")
    
    return removed_count
