# Millance Rewards Backend

A comprehensive rewards management system backend built with FastAPI and PostgreSQL for managing users, franchises, prize pools, group enrollments, payments, and lucky draws.

## 🚀 Features

- **User Management**: Registration, authentication, profile management, and wallet system
- **Franchise Management**: Multi-franchise support with group management
- **Prize Pool System**: Configurable prize pools with monthly prizes
- **Payment Integration**: Cashfree payment gateway integration
- **Lucky Draw System**: Automated draw system with winner selection
- **Referral System**: Franchise-based referral links and invite codes
- **Coupon Management**: Winner coupon generation and redemption
- **Admin Dashboard**: Comprehensive admin controls for all entities
- **Wallet System**: Dual wallet system (Rewards Wallet + Savings Wallet)

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/techneysoft-ux/millance-rewrads-backend.git
cd millance-rewrads-backend
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Database Setup

#### Create PostgreSQL Database

```sql
CREATE DATABASE millancerewards;
```

#### Create .env File

Create a `.env` file in the root directory with the following configuration:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/millancerewards

# JWT Configuration
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# CORS Origins (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://yourdomain.com

# Application Settings
DEBUG=True
ENVIRONMENT=development

# Cashfree Payment Gateway (Production)
CASHFREE_APP_ID=your_cashfree_app_id
CASHFREE_SECRET_KEY=your_cashfree_secret_key
CASHFREE_API_VERSION=2023-08-01
CASHFREE_ENVIRONMENT=production
```

**Important**: Replace all placeholder values with your actual credentials.

### 5. Initialize Database

Run the database initialization script to create all tables:

```bash
python init_db.py
```

This will create all necessary tables:
- users
- admins
- franchises
- prize_pools
- monthly_prizes
- plans
- groups
- enrollments
- payments
- transactions
- draws
- winners
- coupons
- franchise_earnings

### 6. Create Admin User (Optional)

Run the check_admin.py script to create a default admin user:

```bash
python check_admin.py
```

Default admin credentials:
- Email: `admin@millancefurniture.com`
- Password: `admin123`

**Change these credentials immediately in production!**

### 7. Run the Server

#### Development Mode

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

#### Production Mode (Linux/VPS)

```bash
# Install systemd service
sudo nano /etc/systemd/system/rewards-backend.service
```

Add the following configuration:

```ini
[Unit]
Description=Millance Rewards Backend
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/backend
Environment="PATH=/path/to/backend/venv/bin"
ExecStart=/path/to/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8002
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable rewards-backend
sudo systemctl start rewards-backend
sudo systemctl status rewards-backend
```

## 📁 Project Structure

```
backend/
├── main.py                          # Main FastAPI application
├── models.py                        # Database models (SQLAlchemy)
├── schemas.py                       # Pydantic schemas for validation
├── database.py                      # Database connection
├── auth.py                          # Authentication logic
├── cashfree_config.py              # Payment gateway config
├── cashfree_service.py             # Payment service
├── payment_policy.py               # Payment deadline policies
├── init_db.py                      # Database initialization
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables (create this)
├── .gitignore                      # Git ignore rules
│
├── Migration Scripts/
│   ├── add_address_column.py
│   ├── add_coupon_column.py
│   ├── add_pin_column.py
│   ├── add_profile_photo_column.py
│   ├── add_referral_system.py
│   ├── create_earnings_table.py
│   ├── create_monthly_prizes_table.py
│   └── create_payment_tables.py
│
└── Test Scripts/
    ├── test_api_response.py
    ├── test_cashfree.py
    ├── test_coupon_system.py
    ├── test_draw_system.py
    ├── test_endpoints.py
    └── test_wallet_system.py
```

## 🔑 API Endpoints

### Authentication
- `POST /api/login` - User login
- `POST /api/franchise/login` - Franchise login
- `POST /api/admin/login` - Admin login
- `POST /api/register` - User registration

### User Routes
- `GET /api/users/me` - Get current user info
- `PUT /api/users/me` - Update user profile
- `GET /api/users/wallet` - Get wallet balance
- `GET /api/users/transactions` - Get transaction history
- `POST /api/users/change-password` - Change password
- `POST /api/users/set-pin` - Set security PIN

### Admin Routes
- `GET /api/admin/stats` - Get dashboard statistics
- `GET /api/admin/users` - Get all users
- `GET /api/admin/franchises` - Get all franchises
- `POST /api/admin/franchises` - Create franchise
- `GET /api/admin/prize-pools` - Get all prize pools
- `POST /api/admin/prize-pools` - Create prize pool
- `GET /api/admin/plans` - Get all plans
- `POST /api/admin/plans` - Create plan

### Franchise Routes
- `GET /api/franchise/dashboard` - Franchise dashboard
- `GET /api/franchise/groups` - Get franchise groups
- `POST /api/franchise/groups` - Create group
- `GET /api/franchise/groups/{id}` - Get group details
- `POST /api/franchise/groups/{id}/enroll` - Enroll user in group

### Payment Routes
- `POST /api/payments/create-order` - Create payment order
- `POST /api/payments/verify` - Verify payment
- `GET /api/payments/user` - Get user payments
- `POST /api/cashfree/webhook` - Payment webhook

### Draw Routes
- `POST /api/draws/conduct` - Conduct draw (Admin)
- `GET /api/draws/status` - Get draw status
- `GET /api/draws/winners` - Get winners list
- `GET /api/users/my-winnings` - Get user winnings

## 🔐 Security Features

- JWT-based authentication
- Role-based access control (User, Franchise, Admin)
- Password hashing with bcrypt
- PIN protection for sensitive operations
- CORS configuration
- SQL injection protection via SQLAlchemy ORM
- Input validation with Pydantic

## 💳 Payment Integration

The system uses Cashfree Payment Gateway for processing payments:

1. **Setup Cashfree Account**: Sign up at [Cashfree](https://www.cashfree.com/)
2. **Get Credentials**: Obtain App ID and Secret Key from dashboard
3. **Configure .env**: Add credentials to `.env` file
4. **Set Environment**: Use `sandbox` for testing, `production` for live
5. **Webhook URL**: Configure webhook at `https://yourdomain.com/api/cashfree/webhook`

## 📊 Database Schema

### Core Tables
- **users**: User accounts and profiles
- **franchises**: Franchise partners
- **prize_pools**: Prize configurations
- **plans**: Subscription plans
- **groups**: Group enrollments
- **enrollments**: User-group relationships
- **payments**: Payment records
- **transactions**: Wallet transactions
- **draws**: Draw events
- **winners**: Draw winners
- **coupons**: Winner coupons

## 🧪 Testing

Run test scripts to verify functionality:

```bash
# Test API endpoints
python test_endpoints.py

# Test payment system
python test_cashfree.py

# Test draw system
python test_draw_system.py

# Test wallet system
python test_wallet_system.py
```

## 🚀 Deployment

### VPS Deployment (Ubuntu/Debian)

1. **Update system**:
```bash
sudo apt update && sudo apt upgrade -y
```

2. **Install dependencies**:
```bash
sudo apt install python3-pip python3-venv postgresql nginx -y
```

3. **Clone and setup**:
```bash
cd /var/www
git clone https://github.com/techneysoft-ux/millance-rewrads-backend.git rewards-backend
cd rewards-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Configure .env** with production settings

5. **Setup systemd service** (see step 7 above)

6. **Configure Nginx** as reverse proxy:
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

7. **Enable SSL** with Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.yourdomain.com
```

## 🔄 Updating

```bash
cd /var/www/rewards-backend
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart rewards-backend
```

## 📝 Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql://user:pass@localhost/db |
| SECRET_KEY | JWT secret key | your-secret-key |
| ALGORITHM | JWT algorithm | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token expiry time | 10080 (7 days) |
| CORS_ORIGINS | Allowed origins | http://localhost:5173,https://domain.com |
| CASHFREE_APP_ID | Cashfree App ID | your_app_id |
| CASHFREE_SECRET_KEY | Cashfree Secret Key | your_secret_key |
| CASHFREE_ENVIRONMENT | Payment environment | sandbox or production |

## 🐛 Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection string in .env
# Verify database exists
psql -U username -d millancerewards
```

### Port Already in Use
```bash
# Kill process on port 8002
lsof -ti:8002 | xargs kill -9

# Or use different port
uvicorn main:app --port 8003
```

### Module Not Found Error
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📧 Support

For issues or questions, contact: techneysoft123@gmail.com

## 📄 License

Proprietary - All rights reserved by Millance Furniture

## 👥 Contributors

- Development Team: Techneysoft
- Project: Millance Rewards System
