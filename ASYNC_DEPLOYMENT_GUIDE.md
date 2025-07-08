# VectorCraft Async System Deployment Guide

## Overview

This guide covers the deployment of VectorCraft's async processing system with Celery, Redis, and enhanced backend services. The system provides scalable background processing, real-time monitoring, and webhook notifications.

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   Flask API     │    │   Celery Worker │
│   (Users)       │──> │   (Async API)   │──> │   (Processing)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Redis Cache   │    │   File Storage  │
                       │   (Broker)      │    │   (Results)     │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   PostgreSQL    │
                       │   (Database)    │
                       └─────────────────┘
```

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended) or macOS
- **Python**: 3.8+ 
- **Memory**: 4GB+ RAM
- **Storage**: 20GB+ free space
- **Network**: Stable internet connection

### Software Dependencies

```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv redis-server postgresql postgresql-contrib

# Install Docker (optional but recommended)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Quick Start (Docker Compose)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-repo/vectorcraft.git
cd vectorcraft

# Copy environment file
cp .env.example .env

# Edit configuration
nano .env
```

### 2. Environment Configuration

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DOMAIN_URL=https://yourdomain.com

# Redis Configuration
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Database Configuration
DATABASE_URL=postgresql://vectorcraft:password@postgres:5432/vectorcraft

# Email Configuration (GoDaddy SMTP)
SMTP_SERVER=smtpout.secureserver.net
SMTP_PORT=587
SMTP_USERNAME=support@yourdomain.com
SMTP_PASSWORD=your-email-password
FROM_EMAIL=support@yourdomain.com

# PayPal Configuration
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-client-secret
PAYPAL_ENVIRONMENT=live

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
```

### 3. Deploy with Docker Compose

```bash
# Start the complete stack
docker-compose -f docker-compose.async.yml up -d

# Check services status
docker-compose -f docker-compose.async.yml ps

# View logs
docker-compose -f docker-compose.async.yml logs -f vectorcraft_app
```

## Manual Deployment

### 1. Environment Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p logs uploads results output
```

### 2. Database Setup

```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres createdb vectorcraft
sudo -u postgres createuser -P vectorcraft

# Initialize database
python setup_environment.py
```

### 3. Redis Setup

```bash
# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis connection
redis-cli ping
```

### 4. Application Services

```bash
# Terminal 1: Start Flask application
python app.py

# Terminal 2: Start Celery worker
celery -A vectorization_tasks worker --loglevel=info --concurrency=4 --queues=vectorization,batch_processing,image_analysis,maintenance

# Terminal 3: Start Celery beat scheduler
celery -A vectorization_tasks beat --loglevel=info

# Terminal 4: Start Flower monitoring
celery -A vectorization_tasks flower --address=0.0.0.0 --port=5555
```

### 5. Process Management (Production)

```bash
# Install supervisor
sudo apt install supervisor

# Create supervisor configuration
sudo nano /etc/supervisor/conf.d/vectorcraft.conf
```

**Supervisor Configuration:**

```ini
[program:vectorcraft_app]
command=/path/to/venv/bin/python app.py
directory=/path/to/vectorcraft
user=vectorcraft
autostart=true
autorestart=true
stderr_logfile=/var/log/vectorcraft/app.err.log
stdout_logfile=/var/log/vectorcraft/app.out.log

[program:celery_worker]
command=/path/to/venv/bin/celery -A vectorization_tasks worker --loglevel=info --concurrency=4
directory=/path/to/vectorcraft
user=vectorcraft
autostart=true
autorestart=true
stderr_logfile=/var/log/vectorcraft/worker.err.log
stdout_logfile=/var/log/vectorcraft/worker.out.log

[program:celery_beat]
command=/path/to/venv/bin/celery -A vectorization_tasks beat --loglevel=info
directory=/path/to/vectorcraft
user=vectorcraft
autostart=true
autorestart=true
stderr_logfile=/var/log/vectorcraft/beat.err.log
stdout_logfile=/var/log/vectorcraft/beat.out.log

[program:flower]
command=/path/to/venv/bin/celery -A vectorization_tasks flower --address=0.0.0.0 --port=5555
directory=/path/to/vectorcraft
user=vectorcraft
autostart=true
autorestart=true
stderr_logfile=/var/log/vectorcraft/flower.err.log
stdout_logfile=/var/log/vectorcraft/flower.out.log
```

```bash
# Start services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

## Nginx Configuration

```nginx
# /etc/nginx/sites-available/vectorcraft
server {
    listen 80;
    server_name yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Content-Type-Options "nosniff";
    
    # Main application
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for async operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Flower monitoring (restrict access)
    location /flower {
        proxy_pass http://localhost:5555;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Authentication
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
    
    # Static files
    location /static {
        alias /path/to/vectorcraft/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # File uploads
    client_max_body_size 16M;
    client_body_timeout 60s;
    client_header_timeout 60s;
}
```

## Monitoring Setup

### 1. Prometheus Configuration

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'vectorcraft'
    static_configs:
      - targets: ['localhost:8080']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
    
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
```

### 2. Grafana Dashboards

```bash
# Import pre-configured dashboards
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @grafana/dashboards/vectorcraft-dashboard.json
```

## Security Considerations

### 1. Firewall Configuration

```bash
# UFW firewall rules
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable

# Restrict Redis access
sudo ufw deny 6379/tcp
```

### 2. SSL/TLS Setup

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Generate SSL certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Application Security

```bash
# Create non-root user
sudo useradd -m -s /bin/bash vectorcraft
sudo usermod -aG sudo vectorcraft

# Set file permissions
sudo chown -R vectorcraft:vectorcraft /path/to/vectorcraft
sudo chmod -R 755 /path/to/vectorcraft
sudo chmod 600 /path/to/vectorcraft/.env
```

## Performance Optimization

### 1. Redis Optimization

```bash
# Edit Redis configuration
sudo nano /etc/redis/redis.conf

# Key optimizations:
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 2. PostgreSQL Optimization

```sql
-- postgresql.conf optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

### 3. Celery Worker Optimization

```bash
# Optimized worker configuration
celery -A vectorization_tasks worker \
    --loglevel=info \
    --concurrency=4 \
    --prefetch-multiplier=1 \
    --max-tasks-per-child=1000 \
    --time-limit=1800 \
    --soft-time-limit=1200
```

## Monitoring and Alerting

### 1. Health Checks

```bash
# Application health
curl -f http://localhost:8080/health

# Celery health
celery -A vectorization_tasks inspect ping

# Redis health
redis-cli ping

# Database health
psql -h localhost -U vectorcraft -d vectorcraft -c "SELECT 1"
```

### 2. Log Monitoring

```bash
# Centralized logging with rsyslog
sudo nano /etc/rsyslog.conf

# Add:
*.* @@localhost:514

# Application logs
tail -f /var/log/vectorcraft/app.out.log
tail -f /var/log/vectorcraft/worker.out.log
tail -f /var/log/vectorcraft/beat.out.log
```

### 3. Performance Metrics

```bash
# System metrics
htop
iostat -x 1
vmstat 1
netstat -tulpn

# Application metrics
curl http://localhost:8080/api/async/metrics
curl http://localhost:5555/api/workers
```

## Backup and Recovery

### 1. Database Backup

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backup/vectorcraft"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

pg_dump -h localhost -U vectorcraft vectorcraft > $BACKUP_DIR/vectorcraft_$DATE.sql
gzip $BACKUP_DIR/vectorcraft_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

### 2. Redis Backup

```bash
# Redis backup
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /backup/redis/dump_$(date +%Y%m%d_%H%M%S).rdb
```

### 3. Application Backup

```bash
# Application files backup
tar -czf /backup/vectorcraft_app_$(date +%Y%m%d_%H%M%S).tar.gz \
    /path/to/vectorcraft \
    --exclude=venv \
    --exclude=uploads \
    --exclude=results \
    --exclude=__pycache__
```

## Troubleshooting

### Common Issues

1. **Celery Worker Not Starting**
   ```bash
   # Check broker connection
   celery -A vectorization_tasks inspect ping
   
   # Check worker logs
   celery -A vectorization_tasks worker --loglevel=debug
   ```

2. **Redis Connection Issues**
   ```bash
   # Check Redis status
   sudo systemctl status redis-server
   
   # Test connection
   redis-cli ping
   
   # Check configuration
   redis-cli config get "*"
   ```

3. **Database Connection Issues**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Test connection
   psql -h localhost -U vectorcraft -d vectorcraft
   
   # Check connection pool
   curl http://localhost:8080/api/async/health
   ```

4. **High Memory Usage**
   ```bash
   # Monitor memory usage
   free -h
   ps aux --sort=-%mem | head
   
   # Optimize Redis
   redis-cli config set maxmemory 256mb
   redis-cli config set maxmemory-policy allkeys-lru
   ```

5. **Slow Performance**
   ```bash
   # Check system resources
   htop
   iostat -x 1
   
   # Check application metrics
   curl http://localhost:8080/api/async/metrics
   
   # Optimize worker concurrency
   celery -A vectorization_tasks worker --concurrency=8
   ```

## Maintenance

### Regular Tasks

```bash
# Weekly maintenance script
#!/bin/bash

# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean up old files
find /path/to/vectorcraft/uploads -type f -mtime +7 -delete
find /path/to/vectorcraft/results -type f -mtime +7 -delete

# Restart services
sudo supervisorctl restart all

# Check disk space
df -h

# Check service status
sudo supervisorctl status
```

### Updates and Upgrades

```bash
# Update application
git pull origin main
pip install -r requirements.txt

# Database migrations
python setup_environment.py --upgrade

# Restart services
sudo supervisorctl restart all
```

## Scaling Considerations

### Horizontal Scaling

1. **Multiple Workers**
   ```bash
   # Start multiple worker instances
   celery -A vectorization_tasks worker --hostname=worker1@%h
   celery -A vectorization_tasks worker --hostname=worker2@%h
   ```

2. **Load Balancing**
   ```nginx
   upstream vectorcraft_backend {
       server localhost:8080;
       server localhost:8081;
       server localhost:8082;
   }
   ```

3. **Database Clustering**
   - PostgreSQL streaming replication
   - Redis Cluster setup
   - Distributed file storage

### Vertical Scaling

1. **Increase Resources**
   - More CPU cores for workers
   - More RAM for Redis cache
   - Faster storage for database

2. **Optimize Configuration**
   - Tune worker concurrency
   - Adjust connection pools
   - Optimize cache settings

## Support and Documentation

- **API Documentation**: `/API_DOCUMENTATION.md`
- **Performance Guide**: `/PERFORMANCE_TUNING.md`
- **Security Guide**: `/SECURITY.md`
- **Monitoring Dashboard**: `http://localhost:3000`
- **Task Monitoring**: `http://localhost:5555`

## Conclusion

This deployment guide provides a comprehensive approach to deploying VectorCraft's async processing system. The system is designed for high availability, scalability, and performance.

Key benefits:
- ✅ Async processing for better scalability
- ✅ Real-time monitoring and alerting
- ✅ Webhook notifications for integrations
- ✅ Database connection pooling
- ✅ Comprehensive caching system
- ✅ Production-ready deployment

For additional support or questions, please refer to the project documentation or contact the development team.