# VectorCraft Deployment Guide

## 🚀 Quick Deploy Anywhere

### One-Command Deployment
```bash
git clone https://github.com/Ankish8/VectorCraft.git && cd VectorCraft && docker build -t vectorcraft . && docker run -d -p 8080:8080 --name vectorcraft-app vectorcraft
```

### Check if Running
```bash
curl http://localhost:8080/health
```

## 📋 Prerequisites

### Required
- Docker installed
- Port 8080 available
- Git access to repository

### Optional (for development)
- Python 3.11+
- pip package manager

## 🔧 Environment Configuration

### Production Settings
Copy `.env` file and update for production:

```env
# Email (GoDaddy SMTP)
SMTP_USERNAME=your-email@domain.com
SMTP_PASSWORD=your-password
FROM_EMAIL=your-email@domain.com

# PayPal (Production)
PAYPAL_CLIENT_ID=your-live-client-id
PAYPAL_CLIENT_SECRET=your-live-secret
PAYPAL_ENVIRONMENT=live

# App Config
DOMAIN_URL=https://yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
```

## 🌐 Production Deployment (OVH Server)

### 1. Server Setup
```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Git
apt install git -y
```

### 2. Deploy Application
```bash
# Clone repository
git clone https://github.com/Ankish8/VectorCraft.git
cd VectorCraft

# Update environment for production
nano .env  # Edit with production values

# Build and run
docker build -t vectorcraft-prod .
docker run -d -p 80:8080 --name vectorcraft-prod --restart unless-stopped vectorcraft-prod
```

### 3. SSL & Domain Setup
```bash
# Install nginx
apt install nginx -y

# Configure nginx (create /etc/nginx/sites-available/vectorcraft)
server {
    listen 80;
    server_name yourdomain.com;
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Enable site
ln -s /etc/nginx/sites-available/vectorcraft /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# SSL with Let's Encrypt
apt install certbot python3-certbot-nginx -y
certbot --nginx -d yourdomain.com
```

## 🔄 Management Commands

### Container Operations
```bash
# Check status
docker ps
docker logs vectorcraft-app

# Stop/Start
docker stop vectorcraft-app
docker start vectorcraft-app

# Restart
docker restart vectorcraft-app

# Remove (for updates)
docker stop vectorcraft-app
docker rm vectorcraft-app
```

### Updates
```bash
# Pull latest code
git pull origin main

# Rebuild and redeploy
docker stop vectorcraft-app && docker rm vectorcraft-app
docker build -t vectorcraft . && docker run -d -p 8080:8080 --name vectorcraft-app vectorcraft
```

## 🐛 Troubleshooting

### Common Issues

**Port already in use**
```bash
sudo lsof -i :8080
sudo kill -9 <PID>
```

**Container won't start**
```bash
docker logs vectorcraft-app
# Check for environment variable issues
```

**PayPal not working**
- Verify sandbox vs live environment
- Check client ID/secret in .env
- Ensure .env file is copied to container

**Emails not sending**
- Test SMTP credentials
- Check spam folder
- Verify GoDaddy SMTP settings

### Debug Mode
```bash
# Run without daemon to see logs
docker run -p 8080:8080 vectorcraft

# Access container shell
docker exec -it vectorcraft-app bash
```

## 📊 Monitoring

### Health Checks
```bash
# Application health
curl http://localhost:8080/health

# PayPal integration
curl -X POST http://localhost:8080/api/create-paypal-order \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "amount": 49.00}'
```

### Log Monitoring
```bash
# Real-time logs
docker logs -f vectorcraft-app

# Error logs only
docker logs vectorcraft-app 2>&1 | grep -i error
```

## 🔐 Security Notes

### Production Checklist
- [ ] Update default admin password
- [ ] Use HTTPS only (SSL certificate)
- [ ] Firewall configuration (only 80/443 open)
- [ ] Regular backups of user database
- [ ] Monitor for failed login attempts
- [ ] Keep Docker images updated

### Environment Security
- Never commit real credentials to Git
- Use strong passwords for email accounts
- Regularly rotate PayPal API keys
- Enable 2FA on PayPal developer account

---
**Last Updated**: June 29, 2025  
**Status**: Production Ready ✅