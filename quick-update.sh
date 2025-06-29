#!/bin/bash
# Quick update script - Copy files to running container without rebuilding

echo "🚀 Quick updating VectorCraft container..."

# Copy updated files to running container
echo "📁 Copying template files..."
docker cp templates/admin/system.html vectorcraft-container:/app/templates/admin/system.html
docker cp templates/admin/dashboard.html vectorcraft-container:/app/templates/admin/dashboard.html  
docker cp templates/admin/base.html vectorcraft-container:/app/templates/admin/base.html

echo "📱 Copying app.py if changed..."
docker cp app.py vectorcraft-container:/app/app.py 2>/dev/null || echo "app.py not copied (no changes)"

echo "✅ Files updated! Now:"
echo "   1. Hard refresh browser (Ctrl+F5 or Cmd+Shift+R)"
echo "   2. Or clear browser cache"
echo "   3. Changes should be visible immediately"

echo ""
echo "🌐 Access: http://localhost:8080/admin"
echo "🕒 IST Time should now display correctly"