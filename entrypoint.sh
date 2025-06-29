#!/bin/bash
# VectorCraft Container Entrypoint
# Ensures VTracer is available before starting the app

echo "🚀 Starting VectorCraft container..."

# Try to install VTracer if not available
if ! python -c "import vtracer" 2>/dev/null; then
    echo "📦 Installing VTracer..."
    pip install vtracer --quiet || echo "⚠️  VTracer installation failed - using fallback strategies"
else
    echo "✅ VTracer already available"
fi

# Verify email service
echo "📧 Email service: ${SMTP_USERNAME:-not configured}"

# Start the Flask application
echo "🌐 Starting VectorCraft application..."
exec python app.py