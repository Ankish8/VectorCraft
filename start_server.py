#!/usr/bin/env python3
"""
VectorCraft 2.0 Server Startup Script
Simple way to start the web server
"""

import subprocess
import sys
import webbrowser
import time
import requests
from threading import Timer

def check_server_health():
    """Check if server is responding"""
    try:
        response = requests.get('http://localhost:8080/health', timeout=5)
        return response.status_code == 200
    except:
        return False

def open_browser():
    """Open browser after server starts"""
    print("⏳ Waiting for server to start...")
    
    # Wait up to 10 seconds for server to be ready
    for i in range(20):
        if check_server_health():
            print("✅ Server is ready!")
            print("🌐 Opening browser...")
            webbrowser.open('http://localhost:8080')
            return
        time.sleep(0.5)
    
    print("⚠️  Server may not be ready yet. Try opening http://localhost:8080 manually.")

def main():
    print("🚀 VectorCraft 2.0 - Starting Web Interface...")
    print("📍 Server will be available at: http://localhost:8080")
    print("🛑 Press Ctrl+C to stop the server")
    print()
    
    # Schedule browser opening
    Timer(2.0, open_browser).start()
    
    try:
        # Start Flask app
        from app import app
        app.run(debug=False, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()