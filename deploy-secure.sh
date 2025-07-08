#!/bin/bash

# VectorCraft Secure Deployment Script
# This script sets up a secure deployment environment

set -e

echo "🔒 Starting VectorCraft Security Deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please create one from .env.example"
    echo "Run: cp .env.example .env"
    echo "Then edit .env with your secure credentials"
    exit 1
fi

# Validate critical environment variables
echo "🔍 Validating environment variables..."

required_vars=(
    "SECRET_KEY"
    "ADMIN_PASSWORD"
    "SMTP_PASSWORD"
    "PAYPAL_CLIENT_ID"
    "PAYPAL_CLIENT_SECRET"
)

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "^${var}=.*your-.*" .env; then
        echo "❌ Error: ${var} not properly configured in .env"
        exit 1
    fi
done

# Generate secure secret key if not provided
if grep -q "^SECRET_KEY=your-secret-key-here" .env; then
    echo "🔑 Generating secure SECRET_KEY..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|" .env
    echo "✅ SECRET_KEY generated and updated"
fi

# Set secure file permissions
echo "🔐 Setting secure file permissions..."
chmod 600 .env
chmod 700 data/ || mkdir -p data && chmod 700 data/
chmod 755 uploads/ || mkdir -p uploads && chmod 755 uploads/
chmod 755 results/ || mkdir -p results && chmod 755 results/

# Build Docker image with security enhancements
echo "🐳 Building secure Docker image..."
docker build -t vectorcraft-secure:latest .

# Create docker-compose override for security
cat > docker-compose.override.yml << EOF
version: '3.8'

services:
  vectorcraft:
    image: vectorcraft-secure:latest
    env_file:
      - .env
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:size=100M,noexec,nosuid,nodev
      - /var/tmp:size=10M,noexec,nosuid,nodev
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
      - ./results:/app/results
      - ./vectorcraft.log:/app/vectorcraft.log
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
EOF

# Start secure deployment
echo "🚀 Starting secure VectorCraft deployment..."
docker-compose up -d

echo "✅ VectorCraft deployed securely!"
echo ""
echo "🔒 Security Features Enabled:"
echo "  ✓ Environment variable configuration"
echo "  ✓ File upload security scanning"
echo "  ✓ Session security and timeouts"
echo "  ✓ API rate limiting"
echo "  ✓ CSRF protection"
echo "  ✓ Security headers"
echo "  ✓ Read-only filesystem"
echo "  ✓ No new privileges"
echo "  ✓ Resource limits"
echo "  ✓ Health checks"
echo ""
echo "🌐 Access URLs:"
echo "  Main App: http://localhost:8080"
echo "  Admin Dashboard: http://localhost:8080/admin"
echo "  Health Check: http://localhost:8080/health"
echo ""
echo "⚠️  Important Security Notes:"
echo "  • Admin credentials: Set via ADMIN_USERNAME/ADMIN_PASSWORD in .env"
echo "  • SSL/TLS: Configure reverse proxy (nginx) for production"
echo "  • Firewall: Ensure only necessary ports are open"
echo "  • Backups: Implement regular database backups"
echo "  • Updates: Keep system and dependencies updated"
echo ""
echo "📋 Next Steps:"
echo "  1. Configure reverse proxy with SSL/TLS"
echo "  2. Set up firewall rules"
echo "  3. Configure monitoring and alerting"
echo "  4. Implement backup strategy"
echo "  5. Schedule security updates"