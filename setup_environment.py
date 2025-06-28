#!/usr/bin/env python3
"""
Setup script for VectorCraft environment
This ensures all dependencies are properly installed
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} error: {e}")
        return False

def check_vtracer():
    """Check if vtracer is available"""
    print("\n🔍 Checking VTracer availability...")
    
    # Check local binary
    binary_path = Path("./vtracer_binary")
    if binary_path.exists():
        try:
            result = subprocess.run([str(binary_path), "--version"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ Local VTracer binary found: {result.stdout.strip()}")
                return True
        except Exception as e:
            print(f"⚠️  Local binary test failed: {e}")
    
    # Check system vtracer
    try:
        result = subprocess.run(["vtracer", "--version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ System VTracer found: {result.stdout.strip()}")
            return True
    except Exception:
        pass
    
    # Check Python package
    try:
        import vtracer
        print("✅ Python VTracer package found")
        return True
    except ImportError:
        pass
    
    print("❌ VTracer not found")
    return False

def main():
    print("🚀 VectorCraft Environment Setup")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install requirements
    success = True
    
    # Try to install in virtual environment or with user flag
    install_methods = [
        "pip3 install -r requirements.txt",
        "pip3 install --user -r requirements.txt",
        "python3 -m pip install -r requirements.txt",
        "python3 -m pip install --user -r requirements.txt"
    ]
    
    for method in install_methods:
        if run_command(method, "Installing Python dependencies"):
            break
    else:
        print("⚠️  Could not install dependencies automatically")
        print("Please install manually: pip3 install -r requirements.txt")
        success = False
    
    # Check VTracer
    if not check_vtracer():
        print("\n⚠️  VTracer not available. To install:")
        print("   Option 1: cargo install vtracer")
        print("   Option 2: pip3 install vtracer")
        print("   Option 3: Use the bundled binary (./vtracer_binary)")
        success = False
    
    # Final status
    print("\n" + "=" * 40)
    if success:
        print("✅ Setup completed successfully!")
        print("You can now run: python3 app.py")
    else:
        print("⚠️  Setup completed with warnings")
        print("Some features may not work properly")
    
    return success

if __name__ == "__main__":
    main()