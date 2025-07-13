#!/bin/bash

# VectorCraft Admin CSS Build Script
# This script builds the Tailwind CSS for production use

echo "🎨 Building VectorCraft Admin CSS..."

# Check if Node.js is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install Node.js first."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build CSS for production
echo "🔨 Building CSS..."
npm run build-css-prod

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "✅ CSS build completed successfully!"
    echo "📁 Generated: static/admin/css/admin.css"
    
    # Get file size for verification
    SIZE=$(du -h static/admin/css/admin.css | cut -f1)
    echo "📊 File size: $SIZE"
    
    echo ""
    echo "🚀 Ready for production deployment!"
    echo "   The admin dashboard now uses local CSS instead of CDN."
else
    echo "❌ CSS build failed!"
    exit 1
fi