#!/bin/bash
# VectorCraft Startup Script
# Ensures VTracer is always available

echo "🚀 Starting VectorCraft with VTracer support..."

# Stop any existing container
docker rm -f vectorcraft-app 2>/dev/null || true

# Run the container with VTracer pre-installed
if docker image inspect vectorcraft:with-vtracer >/dev/null 2>&1; then
    echo "📦 Using pre-built image with VTracer..."
    docker run -d -p 8080:8080 --env-file .env --name vectorcraft-app vectorcraft:with-vtracer
else
    echo "📦 Building fresh container..."
    docker build -t vectorcraft .
    docker run -d -p 8080:8080 --env-file .env --name vectorcraft-app vectorcraft
    
    echo "⚙️ Installing VTracer in container..."
    sleep 5
    docker exec -u root vectorcraft-app pip install vtracer || echo "VTracer installation failed"
    
    echo "💾 Saving container state..."
    docker commit vectorcraft-app vectorcraft:with-vtracer
fi

# Wait for startup
echo "⏳ Waiting for VectorCraft to start..."
sleep 5

# Verify everything is working
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✅ VectorCraft is running at http://localhost:8080"
    echo "✅ Landing page: http://localhost:8080"
    echo "✅ Clear session: http://localhost:8080/clear-session"
    
    # Test VTracer
    if docker exec vectorcraft-app python -c "import vtracer" 2>/dev/null; then
        echo "✅ VTracer is available for high-quality conversions"
    else
        echo "⚠️  VTracer not available - using fallback strategies"
    fi
else
    echo "❌ VectorCraft failed to start"
    docker logs vectorcraft-app
fi