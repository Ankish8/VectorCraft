#!/bin/bash

# VectorCraft Admin CSS Development Script
# This script watches for changes and rebuilds CSS automatically

echo "🎨 Starting VectorCraft Admin CSS development watcher..."
echo "👁️  Watching for changes in templates/ and static/admin/scss/"
echo "⏹️  Press Ctrl+C to stop"

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

# Start development watcher
npm run build-css