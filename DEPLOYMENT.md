# VectorCraft Deployment Guide

## Quick Start with Docker

### Prerequisites
- Docker and Docker Compose installed
- At least 2GB of available RAM
- 5GB of free disk space

### Development Deployment

1. **Clone and build:**
   ```bash
   cd VectorCraft
   docker-compose up --build
   ```

2. **Access the application:**
   - Open http://localhost:8080
   - Login with demo credentials:
     - Admin: `admin` / `admin123`
     - Demo: `demo` / `demo123`

### Production Deployment

1. **Build and run in production mode:**
   ```bash
   docker-compose --profile production up -d
   ```

2. **Custom environment:**
   ```bash
   # Create custom environment file
   cp .env.example .env
   
   # Edit configuration
   nano .env
   
   # Deploy with custom settings
   docker-compose --env-file .env up -d
   ```

## Manual Installation

### System Requirements
- Python 3.8+
- 4GB RAM (recommended)
- 10GB disk space

### Setup Steps

1. **Install dependencies:**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install packages
   pip install -r requirements.txt
   pip install flask-login
   ```

2. **Initialize database:**
   ```bash
   python database.py
   ```

3. **Run application:**
   ```bash
   # Copy authenticated app
   cp app_with_auth.py app.py
   
   # Start server
   python app.py
   ```

## Configuration

### Environment Variables
- `FLASK_ENV`: Set to `production` for production deployment
- `SECRET_KEY`: Change from default for security
- `DATABASE_URL`: SQLite database path (default: `vectorcraft.db`)

### Authentication
- Default users are created automatically
- Add users via database or create admin interface
- Change default passwords in production

### File Storage
- `uploads/`: Temporary uploaded images
- `results/`: Generated SVG files
- `output/`: Timestamped output archive

## Security Considerations

### Production Checklist
- [ ] Change default secret key
- [ ] Change default user passwords
- [ ] Enable HTTPS with SSL certificates
- [ ] Set up firewall rules
- [ ] Regular database backups
- [ ] Monitor disk space usage

### Nginx Configuration (Optional)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # File upload size limit
    client_max_body_size 16M;
}
```

## Monitoring

### Health Check
- Endpoint: `GET /health`
- Returns application status and version info

### Logs
```bash
# Docker logs
docker-compose logs -f vectorcraft

# Application logs
tail -f app.log
```

### Metrics
- User upload statistics available in dashboard
- Processing time monitoring
- File size tracking

## Backup and Recovery

### Database Backup
```bash
# Backup SQLite database
cp vectorcraft.db vectorcraft_backup_$(date +%Y%m%d).db

# Docker volume backup
docker run --rm -v vectorcraft_data:/data -v $(pwd):/backup alpine tar czf /backup/database_backup.tar.gz /data
```

### File Backup
```bash
# Backup user files
tar czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/ results/
```

## Scaling

### Performance Optimization
- Use Redis for session storage in multi-instance setup
- Configure reverse proxy load balancing
- Implement CDN for static files
- Database optimization for large user bases

### Resource Monitoring
- Monitor CPU usage during vector processing
- Watch memory usage with large images
- Track disk space for uploads and results

## Troubleshooting

### Common Issues

1. **Permission Errors:**
   ```bash
   sudo chown -R $(whoami):$(whoami) uploads/ results/
   chmod 755 uploads/ results/
   ```

2. **Port Already in Use:**
   ```bash
   # Change port in docker-compose.yml
   ports:
     - "8081:8080"  # Use 8081 instead
   ```

3. **Database Lock Errors:**
   ```bash
   # Stop application and check database
   sqlite3 vectorcraft.db ".schema"
   ```

4. **VTracer Not Working:**
   ```bash
   # Install VTracer in virtual environment
   pip install vtracer
   ```

### Logs and Debugging
- Check Docker logs: `docker-compose logs`
- Python error logs in console output
- Browser console for frontend issues
- Network tab for API request failures

## Support

For issues and questions:
- Check logs first
- Verify system requirements
- Test with demo images
- Review configuration settings

## Updates

### Updating the Application
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up --build -d

# Verify health
curl http://localhost:8080/health
```