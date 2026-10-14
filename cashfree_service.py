"""
Cashfree Payment Gateway Service
Handles all Cashfree API interactions
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Cashfree Configuration
CASHFREE_APP_ID = os.getenv("CASHFREE_APP_ID")
CASHFREE_SECRET_KEY = os.getenv("CASHFREE_SECRET_KEY")
CASHFREE_ENV = os.getenv("CASHFREE_ENV", "production")
CASHFREE_API_VERSION = os.getenv("CASHFREE_API_VERSION", "2023-08-01")

# API Base URLs
if CASHFREE_ENV == "production":
    CASHFREE_BASE_URL = "https://api.cashfree.com/pg"
else:
    CASHFREE_BASE_URL = "https://sandbox.cashfree.com/pg"


class CashfreeService:
    """Service class for Cashfree payment operations"""
    
    def __init__(self):
        self.app_id = CASHFREE_APP_ID
        self.secret_key = CASHFREE_SECRET_KEY
        self.base_url = CASHFREE_BASE_URL
        self.api_version = CASHFREE_API_VERSION
        
        # Validate credentials
        if not self.app_id or not self.secret_key:
            raise ValueError("Cashfree credentials not configured in .env file")
    
    def _get_headers(self):
        """Get headers for Cashfree API requests"""
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-version": self.api_version,
            "x-client-id": self.app_id,
            "x-client-secret": self.secret_key
        }
    
    def create_order(self, order_id: str, amount: float, customer_id: str, customer_name: str, customer_phone: str, customer_email: str):
        """
        Create a new payment order with Cashfree
        
        Args:
            order_id: Unique order ID from our system
            amount: Payment amount in INR
            customer_id: User's MLD ID
            customer_name: User's full name
            customer_phone: User's phone number
            customer_email: User's email
            
        Returns:
            dict: Cashfree order response with payment_session_id
        """
        
        url = f"{self.base_url}/orders"
        
        payload = {
            "order_id": order_id,
            "order_amount": amount,
            "order_currency": "INR",
            "customer_details": {
                "customer_id": customer_id,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "customer_email": customer_email
            },
            "order_meta": {
                "return_url": f"{os.getenv('FRONTEND_URL')}/payment-callback?order_id={order_id}",
                "notify_url": None  # Webhook URL (we'll add later)
            },
            "order_note": "Wallet recharge for Millance Rewards"
        }
        
        try:
            print(f"🔄 Creating Cashfree order: {order_id}")
            print(f"   Customer Phone: {customer_phone}")
            print(f"   Payload: {payload}")
            response = requests.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Cashfree order created: {data.get('cf_order_id')}")
            
            return {
                "success": True,
                "cf_order_id": data.get("cf_order_id"),
                "payment_session_id": data.get("payment_session_id"),
                "order_status": data.get("order_status"),
                "order_token": data.get("order_token")  # For SDK integration
            }
            
        except requests.exceptions.HTTPError as e:
            error_data = e.response.json() if e.response else {}
            print(f"❌ Cashfree API error: {error_data.get('message', 'Unknown error')}")
            print(f"   Status: {e.response.status_code if e.response else 'N/A'}")
            print(f"   Response: {error_data}")
            
            return {
                "success": False,
                "error": error_data.get("message", "Failed to create order"),
                "error_code": error_data.get("code")
            }
        
        except Exception as e:
            print(f"❌ Error creating order: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_order_status(self, order_id: str):
        """
        Get order status from Cashfree
        
        Args:
            order_id: Order ID from our system
            
        Returns:
            dict: Order status and payment details
        """
        
        url = f"{self.base_url}/orders/{order_id}"
        
        try:
            print(f"🔍 Checking order status: {order_id}")
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            print(f"📊 Order status: {data.get('order_status')}")
            
            return {
                "success": True,
                "order_status": data.get("order_status"),
                "order_amount": data.get("order_amount"),
                "cf_order_id": data.get("cf_order_id"),
                "payment_status": None,  # Will be filled from payments API
                "raw_data": data
            }
            
        except requests.exceptions.HTTPError as e:
            error_data = e.response.json() if e.response else {}
            print(f"❌ Error fetching order: {error_data}")
            
            return {
                "success": False,
                "error": error_data.get("message", "Order not found"),
                "error_code": error_data.get("code")
            }
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_payments_for_order(self, order_id: str):
        """
        Get payment details for an order
        
        Args:
            order_id: Order ID from our system
            
        Returns:
            dict: Payment details including status, method, etc.
        """
        
        url = f"{self.base_url}/orders/{order_id}/payments"
        
        try:
            print(f"💳 Fetching payment details: {order_id}")
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            payments = data if isinstance(data, list) else []
            
            if not payments:
                print(f"⚠️ No payments found for order: {order_id}")
                return {
                    "success": True,
                    "payment_status": "NOT_ATTEMPTED",
                    "payments": []
                }
            
            # Get the latest payment
            latest_payment = payments[0]
            
            print(f"💳 Payment status: {latest_payment.get('payment_status')}")
            
            return {
                "success": True,
                "cf_payment_id": latest_payment.get("cf_payment_id"),
                "payment_status": latest_payment.get("payment_status"),
                "payment_amount": latest_payment.get("payment_amount"),
                "payment_time": latest_payment.get("payment_time"),
                "payment_method": latest_payment.get("payment_group"),
                "bank_reference": latest_payment.get("bank_reference"),
                "auth_id": latest_payment.get("auth_id"),
                "all_payments": payments
            }
            
        except requests.exceptions.HTTPError as e:
            error_data = e.response.json() if e.response else {}
            print(f"❌ Error fetching payments: {error_data}")
            
            return {
                "success": False,
                "error": error_data.get("message", "Failed to fetch payments"),
                "error_code": error_data.get("code")
            }
        
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_payment(self, order_id: str):
        """
        Verify payment by checking both order and payment status
        
        Args:
            order_id: Order ID from our system
            
        Returns:
            dict: Combined verification result
        """
        
        print(f"🔐 Verifying payment for order: {order_id}")
        
        # Step 1: Get order status
        order_result = self.get_order_status(order_id)
        
        if not order_result.get("success"):
            return order_result
        
        # Step 2: Get payment details
        payment_result = self.get_payments_for_order(order_id)
        
        # Combine results
        verification = {
            "success": True,
            "order_id": order_id,
            "order_status": order_result.get("order_status"),
            "payment_status": payment_result.get("payment_status", "NOT_ATTEMPTED"),
            "amount": order_result.get("order_amount"),
            "cf_payment_id": payment_result.get("cf_payment_id"),
            "payment_method": payment_result.get("payment_method"),
            "payment_time": payment_result.get("payment_time"),
            "bank_reference": payment_result.get("bank_reference")
        }
        
        # Determine if payment was successful
        verification["is_paid"] = (
            order_result.get("order_status") == "PAID" or
            payment_result.get("payment_status") == "SUCCESS"
        )
        
        print(f"{'✅' if verification['is_paid'] else '❌'} Payment verified: {verification['payment_status']}")
        
        return verification


# Create singleton instance
cashfree = CashfreeService()
