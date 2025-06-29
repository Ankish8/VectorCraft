# VectorCraft One-Time Payment System - Implementation Plan

## Project Overview
VectorCraft is a professional vector conversion tool transitioning from a SaaS model to a **one-time payment system**. Users purchase access via PayPal, receive credentials via email, and can then access the full application.

## Business Model
- **One-time payment** (not subscription)
- **No signup page** - users get credentials after payment
- **PayPal only** for payments initially
- **Email delivery** of login credentials
- **Make.com integration** for automation and notifications

## Current Status
✅ **Docker deployment working** with authentication system
✅ **Core VectorCraft application** fully functional
✅ **Database system** with user management
✅ **Templates** for login, dashboard, and main app

## Implementation Phases

### Phase 1: Landing & Purchase Pages 🎯 **PRIORITY**
**Goal**: Create simple, replaceable landing page with Buy Now flow

#### 1.1 Landing Page (`templates/landing.html`)
- **Simple HTML/CSS design** (easily replaceable later)
- Hero section with VectorCraft benefits
- **Prominent "Buy Now" button**
- Price display and feature list
- Clean, professional layout
- Mobile responsive

#### 1.2 Buy Now Page (`templates/buy.html`)
- Customer information form:
  - Email address (required)
  - Preferred username (optional - auto-generate if empty)
  - Order confirmation
- **PayPal button integration** (placeholder for now)
- Order summary and terms

#### 1.3 Routes & Logic (`app.py` updates)
```python
@app.route('/')
def landing_page():
    # Show landing page if not authenticated
    
@app.route('/buy')
def buy_now():
    # Show purchase form
    
@app.route('/api/create-order', methods=['POST'])
def create_order():
    # Handle order creation and email simulation
```

### Phase 2: Email System Implementation 📧
**Goal**: Implement GoDaddy SMTP email delivery

#### 2.1 Email Configuration
- **GoDaddy SMTP setup** in Docker environment
- Email templates for:
  - Welcome email with credentials
  - Purchase confirmation
  - Error notifications

#### 2.2 Email Service (`email_service.py`)
```python
class EmailService:
    def send_credentials_email(self, email, username, password, login_url)
    def send_purchase_confirmation(self, email, order_details)
    def send_error_notification(self, email, error_details)
```

#### 2.3 User Creation Logic
- Generate secure random passwords
- Create user accounts automatically after "payment"
- Store order information in database

### Phase 3: PayPal Integration 💳
**Goal**: Real PayPal payment processing

#### 3.1 PayPal Setup
- PayPal REST API integration
- Order creation and capture
- Webhook handling for payment confirmation

#### 3.2 Payment Flow
```
Buy Now → PayPal → Payment Success → User Creation → Email Sent → Redirect to Login
```

#### 3.3 Database Updates
- Add `orders` table for payment tracking
- Add `payment_status` field to users
- Store PayPal transaction IDs

### Phase 4: Make.com Automation 🤖
**Goal**: Webhook endpoints for external automation

#### 4.1 Webhook Endpoints
```python
@app.route('/webhooks/payment-success', methods=['POST'])
@app.route('/webhooks/payment-error', methods=['POST'])
@app.route('/webhooks/user-created', methods=['POST'])
```

#### 4.2 Automation Events
- **Payment Success**: Send notification to Telegram
- **Payment Error**: Alert about failed transactions
- **User Created**: Log new customer in tracking system
- **Daily Stats**: Send summary reports

### Phase 5: Production Deployment 🚀
**Goal**: Deploy to OVH server with domain configuration

#### 5.1 Server Setup
- OVH server configuration
- Docker deployment
- SSL certificate setup (Let's Encrypt)
- Domain configuration

#### 5.2 Production Configuration
- Environment variables for production
- Email credentials configuration
- PayPal production keys
- Database backups

## Technical Architecture

### Database Schema Updates
```sql
-- Orders table
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    username TEXT,
    amount DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    paypal_order_id VARCHAR(255),
    paypal_payment_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Update users table
ALTER TABLE users ADD COLUMN order_id INTEGER;
ALTER TABLE users ADD COLUMN payment_status VARCHAR(50) DEFAULT 'pending';
```

### File Structure
```
VectorCraft/
├── templates/
│   ├── landing.html          # NEW: Landing page
│   ├── buy.html             # NEW: Purchase page  
│   ├── success.html         # NEW: Payment success
│   ├── error.html           # NEW: Payment error
│   ├── login.html           # EXISTING
│   ├── dashboard.html       # EXISTING
│   └── index.html           # EXISTING
├── static/
│   ├── css/
│   └── js/
├── services/
│   ├── email_service.py     # NEW: Email handling
│   ├── payment_service.py   # NEW: PayPal integration
│   └── webhook_service.py   # NEW: Make.com webhooks
├── app.py                   # UPDATED: New routes
├── database.py             # UPDATED: Orders table
└── claude.md               # THIS PLAN
```

### Environment Variables
```env
# Email (GoDaddy SMTP)
SMTP_SERVER=smtpout.secureserver.net
SMTP_PORT=587
SMTP_USERNAME=your-email@domain.com
SMTP_PASSWORD=your-password

# PayPal
PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-secret
PAYPAL_ENVIRONMENT=sandbox|live

# Application
DOMAIN_URL=https://yourdomain.com
ADMIN_EMAIL=admin@domain.com
```

## Development Priorities

### Immediate (This Session)
1. ✅ **Create landing page template**
2. ✅ **Create buy now page template**  
3. ✅ **Add new routes to app.py**
4. ✅ **Implement email simulation**
5. ✅ **Test complete flow without PayPal**

### Next Session
1. **GoDaddy SMTP configuration**
2. **Real email delivery testing**
3. **PayPal sandbox integration**
4. **Make.com webhook endpoints**

### Future Sessions
1. **PayPal production setup**
2. **Server deployment**
3. **Domain & SSL configuration**
4. **Make.com automation setup**

## Success Metrics
- ✅ User can complete purchase simulation
- ✅ Email credentials are delivered automatically
- ✅ User can login with received credentials
- ✅ Complete VectorCraft functionality works
- ✅ Make.com receives webhook notifications
- ✅ Production deployment successful

## Notes
- Landing page design is **intentionally simple** for easy replacement
- All payment logic is **modular** for easy PayPal integration
- Email system uses **templates** for easy customization
- Webhook system is **flexible** for various automation needs
- Database schema supports **full order tracking**

---
*Last Updated: 2025-06-29*
*Status: Architecture Planning Complete - Ready for Implementation*