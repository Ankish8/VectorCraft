#!/bin/bash
# Quick setup and run script for VectorCraft direct development

echo "🚀 VectorCraft Direct Development Setup"
echo "======================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install flask flask-login werkzeug python-dotenv requests cryptography

# Install only essential packages for faster startup
echo "📦 Installing core VectorCraft dependencies..."
pip install numpy opencv-python Pillow

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Starting VectorCraft on http://localhost:5004"
echo "🔧 Admin panel: http://localhost:5004/admin"
echo "🔑 Login: admin / admin123"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the app
python3 app.py