"""
Cashfree Payment Gateway Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Cashfree Configuration
CASHFREE_CLIENT_ID = os.getenv("CASHFREE_CLIENT_ID", "")
CASHFREE_CLIENT_SECRET = os.getenv("CASHFREE_CLIENT_SECRET", "")

# Environment: 'sandbox' or 'production'
CASHFREE_ENV = os.getenv("CASHFREE_ENV", "sandbox")

# Base URLs
CASHFREE_BASE_URL = {
    "sandbox": "https://sandbox.cashfree.com/pg",
    "production": "https://api.cashfree.com/pg"
}

# API Version
CASHFREE_API_VERSION = "2023-08-01"

# Get base URL based on environment
def get_base_url():
    return CASHFREE_BASE_URL.get(CASHFREE_ENV, CASHFREE_BASE_URL["sandbox"])

# Return URL for payment completion
PAYMENT_RETURN_URL = os.getenv("PAYMENT_RETURN_URL", "https://millancefurniture.com/payment/callback")

# Webhook URL for payment notifications
PAYMENT_WEBHOOK_URL = os.getenv("PAYMENT_WEBHOOK_URL", "https://millancefurniture.com/api/payments/webhook")
