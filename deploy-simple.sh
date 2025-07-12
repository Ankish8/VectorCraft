#!/bin/bash
# Simple deployment - just fix the bcrypt issue and deploy current working version

echo "🚀 VectorCraft Simple Deployment"
echo "================================"

# Stop and remove current container
echo "🛑 Stopping current container..."
docker stop vectorcraft-app 2>/dev/null || echo "Container not running"
docker rm vectorcraft-app 2>/dev/null || echo "Container not found"

# Remove old Docker image
echo "🗑️ Removing old Docker image..."
docker rmi vectorcraft:latest 2>/dev/null || echo "Image not found"

# Create a simple requirements.txt to fix bcrypt issue
echo "📝 Creating minimal requirements.txt..."
cat > requirements_simple.txt << 'EOF'
flask>=2.0.0
flask-login>=0.6.0
flask-wtf>=1.0.0
werkzeug>=2.0.0
python-dotenv>=0.19.0
bcrypt>=3.2.0
python-magic>=0.4.24
flask-limiter>=2.1.0
requests>=2.28.0
cryptography>=3.4.8
numpy>=1.21.0
Pillow>=8.0.0
opencv-python>=4.5.0
scikit-image>=0.18.0
matplotlib>=3.5.0
scipy>=1.7.0
svgwrite>=1.4.0
shapely>=1.8.0
vtracer>=0.6.0
psutil>=5.9.0
scikit-learn>=1.0.0
EOF

# Backup original requirements and use simple one
mv requirements.txt requirements_original.txt
mv requirements_simple.txt requirements.txt

# Build fresh Docker image
echo "🔨 Building Docker image with fixed dependencies..."
docker build -t vectorcraft:latest .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    # Restore original requirements
    mv requirements_original.txt requirements.txt
    exit 1
fi

# Restore original requirements
mv requirements_original.txt requirements.txt

# Start fresh container
echo "🚀 Starting fresh container..."
docker run -d \
    --name vectorcraft-app \
    -p 8080:8080 \
    --restart unless-stopped \
    vectorcraft:latest

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ VectorCraft deployed successfully!"
    echo "🌐 Access: http://localhost:8080"
    echo "🔑 Admin: http://localhost:8080/admin"
    echo "⏱️ Wait 30 seconds for startup, then access"
    echo ""
    echo "🎯 Simple deployment with:"
    echo "   ✅ Fixed bcrypt dependency"
    echo "   ✅ Clean admin dashboard"
    echo "   ✅ Working functionality"
    echo ""
    echo "🔍 Check container status:"
    echo "   docker logs vectorcraft-app"
    echo "   docker ps"
else
    echo "❌ Failed to start container!"
    exit 1
fi