#!/usr/bin/env python3
"""
Local development server for VectorCraft
Runs on port 5000 to avoid conflicts with Docker
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main app
from app import app

if __name__ == '__main__':
    print("🚀 Starting VectorCraft LOCAL DEV - Port 4000")
    print("🔧 Debug mode: ON")
    print("✅ Ready!")
    print("\n🌐 Access VectorCraft at: http://localhost:4000")
    print("🔧 Admin panel: http://localhost:4000/admin")
    print("🔑 Login with: admin/admin123")
    print("\n💡 Local development - changes update automatically!")
    print(" Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=4000)