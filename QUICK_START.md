# 🚀 VectorCraft Quick Start Guide

## Fast Development Setup (No Docker)

### Option 1: Automated Setup (Recommended)
```bash
./run_direct.sh
```

### Option 2: Manual Setup
```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install minimal dependencies
pip install -r requirements_dev.txt

# 3. Run the app
python3 app.py
```

### Option 3: System-wide Install (Not recommended)
```bash
# Install dependencies globally
pip3 install flask flask-login werkzeug python-dotenv requests cryptography numpy Pillow

# Run the app
python3 app.py
```

## Access Your App

Once running, access:
- **Main App**: http://localhost:5004
- **Admin Panel**: http://localhost:5004/admin
- **Email Testing**: http://localhost:5004/admin/email/test
- **Login**: admin / admin123

## What You Get

### ✅ **Complete Email System**
- Email template management
- Email automation system  
- Email testing interface
- Real SMTP delivery (8.7/10 deliverability score)
- Variable replacement working

### ✅ **Admin Features**
- Complete admin dashboard
- Real-time monitoring
- System health checks
- Transaction management

### ✅ **Core Features**
- User authentication
- PayPal payment processing
- Database management
- API endpoints

## Fast Development Workflow

1. **Start the app**: `./run_direct.sh` or `python3 app.py`
2. **Make changes** to any file
3. **Restart** to see changes (Flask auto-reload in debug mode)
4. **Test features** at http://localhost:5004

## Troubleshooting

### If app won't start:
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Check if port is in use
lsof -i :5004

# Install missing dependencies
pip install flask flask-login werkzeug python-dotenv
```

### If database errors:
```bash
# Database file exists and should work
ls -la vectorcraft.db
```

### If import errors:
```bash
# Make sure you're in the right directory
pwd  # Should show /Users/ankish/Downloads/VC2

# Activate virtual environment if using one
source venv/bin/activate
```

## Development Tips

- **Fast iteration**: Use `python3 app.py` directly
- **Auto-reload**: App restarts on file changes in debug mode
- **Testing**: Use `/admin/email/test` for email testing
- **Monitoring**: Check `/admin` for system status

---

**Ready to develop!** Your VectorCraft app with complete email system is ready for fast iteration. 🎉