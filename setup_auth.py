#!/usr/bin/env python3
"""
Setup script to enable authentication in VectorCraft
"""

import os
import shutil
import sys

def setup_authentication():
    """Enable authentication by replacing main app file"""
    
    print("🔐 Setting up VectorCraft with Authentication...")
    
    # Backup original app if it exists
    if os.path.exists('app.py'):
        print("📁 Backing up original app.py to app_original.py")
        shutil.copy2('app.py', 'app_original.py')
    
    # Copy authenticated app as main app
    if os.path.exists('app_with_auth.py'):
        print("🔄 Replacing app.py with authenticated version")
        shutil.copy2('app_with_auth.py', 'app.py')
    else:
        print("❌ app_with_auth.py not found!")
        return False
    
    # Initialize database
    print("🗄️ Initializing authentication database...")
    try:
        from database import db
        print("✅ Database initialized successfully")
        print("👤 Default users created:")
        print("   Admin: admin / admin123")
        print("   Demo:  demo / demo123")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    
    # Check if Flask-Login is installed
    try:
        import flask_login
        print("✅ Flask-Login is available")
    except ImportError:
        print("⚠️  Flask-Login not found. Installing...")
        os.system("pip install flask-login")
    
    print("\n🎉 Authentication setup complete!")
    print("\n🚀 To start VectorCraft with authentication:")
    print("   python app.py")
    print("\n🌐 Then visit: http://localhost:8080")
    print("🔑 Login with: admin/admin123 or demo/demo123")
    
    return True

def restore_original():
    """Restore original app without authentication"""
    
    print("🔄 Restoring original VectorCraft (no authentication)...")
    
    if os.path.exists('app_original.py'):
        print("📁 Restoring app.py from backup")
        shutil.copy2('app_original.py', 'app.py')
        print("✅ Original app restored")
        print("\n🚀 To start VectorCraft without authentication:")
        print("   python app.py")
    else:
        print("❌ No backup found (app_original.py)")
        return False
    
    return True

def show_status():
    """Show current authentication status"""
    
    print("📊 VectorCraft Authentication Status")
    print("=" * 40)
    
    # Check which version is active
    if os.path.exists('app.py'):
        with open('app.py', 'r') as f:
            content = f.read()
            if 'flask_login' in content and 'login_required' in content:
                print("🔐 Status: Authentication ENABLED")
                print("👤 Users: admin/admin123, demo/demo123")
            else:
                print("🔓 Status: Authentication DISABLED")
                print("🌐 Direct access to vectorization")
    else:
        print("❌ No app.py found")
    
    # Check database
    if os.path.exists('vectorcraft.db'):
        print("🗄️ Database: Available")
        try:
            from database import db
            admin_user = db.get_user_by_username('admin')
            demo_user = db.get_user_by_username('demo')
            
            if admin_user and demo_user:
                print("👥 Users: Default users exist")
            else:
                print("⚠️  Users: Default users missing")
        except:
            print("❌ Database: Error reading")
    else:
        print("📁 Database: Not initialized")
    
    # Check dependencies
    try:
        import flask_login
        print("📦 Flask-Login: Installed")
    except ImportError:
        print("❌ Flask-Login: Not installed")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'enable':
            setup_authentication()
        elif command == 'disable':
            restore_original()
        elif command == 'status':
            show_status()
        else:
            print("❌ Unknown command. Use: enable, disable, or status")
    else:
        print("🔐 VectorCraft Authentication Setup")
        print("=" * 40)
        print("Commands:")
        print("  python setup_auth.py enable   - Enable authentication")
        print("  python setup_auth.py disable  - Disable authentication")
        print("  python setup_auth.py status   - Show current status")
        print("")
        print("Choose an option:")
        print("1. Enable authentication")
        print("2. Disable authentication")
        print("3. Show status")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            setup_authentication()
        elif choice == '2':
            restore_original()
        elif choice == '3':
            show_status()
        else:
            print("❌ Invalid choice")