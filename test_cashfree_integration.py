"""
Complete Cashfree Integration Test Script
Tests: API endpoints, payment flow, wallet crediting
"""

import requests
import json
import time

BASE_URL = "http://localhost:8002"  # Change to VPS URL for production testing

class CashfreeIntegrationTest:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.user_data = None
        self.order_id = None
        
    def print_step(self, step_num, title):
        print(f"\n{'='*60}")
        print(f"STEP {step_num}: {title}")
        print('='*60)
    
    def print_success(self, message):
        print(f"✅ {message}")
    
    def print_error(self, message):
        print(f"❌ {message}")
    
    def print_info(self, message):
        print(f"ℹ️  {message}")
    
    def login(self):
        """Step 1: Login as test user"""
        self.print_step(1, "USER LOGIN")
        
        payload = {
            "identifier": "test@example.com",  # Replace with actual user
            "password": "test123",              # Replace with actual password
            "role": "user"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.user_data = data["user_data"]
                
                self.print_success("Login successful!")
                self.print_info(f"User: {self.user_data.get('full_name')}")
                self.print_info(f"MLD ID: {self.user_data.get('mld_id')}")
                self.print_info(f"Current Balance: ₹{self.user_data.get('millance_rewards_wallet', 0)}")
                return True
            else:
                self.print_error(f"Login failed: {response.text}")
                return False
                
        except Exception as e:
            self.print_error(f"Login error: {str(e)}")
            return False
    
    def get_wallet_balance(self):
        """Step 2: Get current wallet balance"""
        self.print_step(2, "GET WALLET BALANCE")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(
                f"{self.base_url}/api/users/wallet",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.print_success("Wallet balance retrieved!")
                self.print_info(f"Millance Rewards: ₹{data.get('millance_rewards_wallet', 0)}")
                self.print_info(f"Savings Wallet: ₹{data.get('savings_wallet', 0)}")
                return data.get('millance_rewards_wallet', 0)
            else:
                self.print_error(f"Failed to get balance: {response.text}")
                return None
                
        except Exception as e:
            self.print_error(f"Error: {str(e)}")
            return None
    
    def create_payment_order(self, amount=100):
        """Step 3: Create payment order"""
        self.print_step(3, f"CREATE PAYMENT ORDER (₹{amount})")
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {"amount": float(amount)}
        
        try:
            response = requests.post(
                f"{self.base_url}/api/payments/create-order",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    self.order_id = data['order_id']
                    
                    self.print_success("Payment order created!")
                    self.print_info(f"Order ID: {data['order_id']}")
                    self.print_info(f"CF Order ID: {data.get('cf_order_id')}")
                    self.print_info(f"Payment Session ID: {data.get('payment_session_id')}")
                    self.print_info(f"Amount: ₹{data['amount']}")
                    
                    return data
                else:
                    self.print_error(f"Order creation failed: {data.get('error')}")
                    return None
            else:
                self.print_error(f"API error: {response.text}")
                return None
                
        except Exception as e:
            self.print_error(f"Error: {str(e)}")
            return None
    
    def simulate_payment_completion(self):
        """Step 4: Simulate payment completion (for testing)"""
        self.print_step(4, "SIMULATE PAYMENT COMPLETION")
        
        self.print_info("In real scenario, user would:")
        self.print_info("1. Be redirected to Cashfree payment page")
        self.print_info("2. Select payment method (UPI/Card/Net Banking)")
        self.print_info("3. Complete payment")
        self.print_info("4. Be redirected back to our app")
        
        print("\n⚠️  Manual Step Required:")
        print("Since this is a test, you need to complete the payment manually.")
        print(f"Order ID: {self.order_id}")
        print("\nOptions:")
        print("1. Use Cashfree test credentials to complete payment")
        print("2. Mark payment as success in database manually")
        print("3. Skip to payment history check")
        
        choice = input("\nEnter 's' to skip to verification, or press Enter to continue: ")
        
        if choice.lower() == 's':
            self.print_info("Skipping payment completion simulation")
            return False
        
        return True
    
    def verify_payment(self):
        """Step 5: Verify payment"""
        self.print_step(5, "VERIFY PAYMENT")
        
        if not self.order_id:
            self.print_error("No order ID available. Create an order first.")
            return False
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {"order_id": self.order_id}
        
        try:
            response = requests.post(
                f"{self.base_url}/api/payments/verify",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and data.get('wallet_credited'):
                    self.print_success("Payment verified and wallet credited!")
                    self.print_info(f"Amount: ₹{data.get('amount')}")
                    self.print_info(f"New Balance: ₹{data.get('new_balance')}")
                    self.print_info(f"Transaction ID: {data.get('transaction_id')}")
                    return True
                else:
                    self.print_error(f"Verification failed: {data.get('error', 'Unknown error')}")
                    self.print_info(f"Payment Status: {data.get('payment_status')}")
                    return False
            else:
                self.print_error(f"API error: {response.text}")
                return False
                
        except Exception as e:
            self.print_error(f"Error: {str(e)}")
            return False
    
    def get_payment_history(self):
        """Step 6: Get payment history"""
        self.print_step(6, "GET PAYMENT HISTORY")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(
                f"{self.base_url}/api/payments/history",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                payments = data.get('payments', [])
                total = data.get('total', 0)
                
                self.print_success(f"Payment history retrieved! Total: {total}")
                
                if payments:
                    print("\nRecent Payments:")
                    for i, payment in enumerate(payments[:5], 1):
                        print(f"\n{i}. Order ID: {payment['order_id']}")
                        print(f"   Amount: ₹{payment['amount']}")
                        print(f"   Status: {payment['payment_status']}")
                        print(f"   Credited: {'Yes' if payment['is_credited'] else 'No'}")
                        print(f"   Date: {payment['created_at']}")
                else:
                    self.print_info("No payment history found")
                
                return payments
            else:
                self.print_error(f"Failed to get history: {response.text}")
                return None
                
        except Exception as e:
            self.print_error(f"Error: {str(e)}")
            return None
    
    def get_transaction_history(self):
        """Step 7: Get transaction history"""
        self.print_step(7, "GET TRANSACTION HISTORY")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(
                f"{self.base_url}/api/users/transactions",
                headers=headers
            )
            
            if response.status_code == 200:
                transactions = response.json()
                
                self.print_success(f"Transaction history retrieved! Total: {len(transactions)}")
                
                if transactions:
                    print("\nRecent Transactions:")
                    for i, txn in enumerate(transactions[:5], 1):
                        print(f"\n{i}. Type: {txn['transaction_type']}")
                        print(f"   Amount: ₹{txn['amount']}")
                        print(f"   Wallet: {txn['wallet']}")
                        print(f"   Description: {txn['description']}")
                        print(f"   Date: {txn['created_at']}")
                else:
                    self.print_info("No transactions found")
                
                return transactions
            else:
                self.print_error(f"Failed to get transactions: {response.text}")
                return None
                
        except Exception as e:
            self.print_error(f"Error: {str(e)}")
            return None
    
    def run_full_test(self):
        """Run complete integration test"""
        print("\n" + "="*60)
        print("CASHFREE INTEGRATION TEST - FULL FLOW")
        print("="*60)
        
        # Step 1: Login
        if not self.login():
            print("\n❌ TEST FAILED: Unable to login")
            return False
        
        # Step 2: Get initial balance
        initial_balance = self.get_wallet_balance()
        if initial_balance is None:
            print("\n❌ TEST FAILED: Unable to get wallet balance")
            return False
        
        # Step 3: Create payment order
        order_data = self.create_payment_order(amount=100)
        if not order_data:
            print("\n❌ TEST FAILED: Unable to create payment order")
            return False
        
        # Step 4: Simulate payment (manual step)
        if not self.simulate_payment_completion():
            print("\n⚠️  Skipping payment verification")
        else:
            # Step 5: Verify payment
            time.sleep(2)  # Wait a bit before verification
            self.verify_payment()
        
        # Step 6: Get payment history
        self.get_payment_history()
        
        # Step 7: Get transaction history
        self.get_transaction_history()
        
        # Step 8: Get final balance
        final_balance = self.get_wallet_balance()
        
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Initial Balance: ₹{initial_balance}")
        print(f"Final Balance: ₹{final_balance}")
        if final_balance and initial_balance:
            difference = final_balance - initial_balance
            print(f"Difference: ₹{difference}")
        
        print("\n✅ TEST COMPLETED!")
        print("\nNOTE: Payment verification may show as failed if payment")
        print("was not actually completed via Cashfree gateway.")
        
        return True


if __name__ == "__main__":
    tester = CashfreeIntegrationTest()
    tester.run_full_test()
