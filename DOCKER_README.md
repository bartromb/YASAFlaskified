# YASAFlaskified Docker Setup - v6

Complete Docker deployment for YASAFlaskified with all production fixes integrated.

## ✅ All Fixes Included

This Docker setup includes:
- ✅ Werkzeug 2.0+ password hashing (scrypt/pbkdf2)
- ✅ CSRF configuration
- ✅ NUMBA cache directory (fixes MNE import errors)
- ✅ App.py job enqueue fix (string path)
- ✅ Proper permissions (no permission errors)
- ✅ Health checks
- ✅ Auto-recovery

## 🚀 Quick Start

### Prerequisites

```bash
# Install Docker (if not installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Log out and back in for group changes
```

### Installation

```bash
# 1. Extract or clone repository
cd YASAFlaskified

# 2. Run Docker setup
chmod +x docker-init.sh
./docker-init.sh

# 3. Access application
# http://localhost:8000
```

That's it! The script handles everything automatically.

## 📦 What Gets Created

### Containers
- **yasaflaskified-web** - Flask app + Gunicorn (port 8000)
- **yasaflaskified-worker** - RQ worker for background processing
- **yasaflaskified-redis** - Redis message queue

### Volumes
- `./uploads` - Uploaded EDF files (persistent)
- `./processed` - Generated results (persistent)
- `./instance` - SQLite database (persistent)
- `./config.json` - Application config (persistent)
- `app_cache` - Matplotlib cache
- `numba_cache` - Numba JIT cache
- `redis_data` - Redis persistence

## 🔧 Management Commands

### Basic Operations

```bash
# View status
docker compose ps

# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f web
docker compose logs -f worker
docker compose logs -f redis

# Restart all services
docker compose restart

# Restart specific service
docker compose restart web
docker compose restart worker

# Stop all services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v
```

### Troubleshooting

```bash
# Check container health
docker compose ps

# Enter web container shell
docker compose exec web /bin/bash

# Enter worker container shell
docker compose exec worker /bin/bash

# Check Redis
docker compose exec redis redis-cli ping

# View recent logs (last 50 lines)
docker compose logs --tail=50 web
docker compose logs --tail=50 worker

# Follow logs in real-time
docker compose logs -f
```

### Database Management

```bash
# Backup database
docker compose exec web tar -czf /tmp/backup.tar.gz instance/
docker cp yasaflaskified-web:/tmp/backup.tar.gz ./backup.tar.gz

# Reset database (stop services first)
docker compose down
rm -f instance/users.db
./docker-init.sh
```

### Updates

```bash
# Update code and rebuild
docker compose down
git pull  # or update your files
docker compose build --no-cache
docker compose up -d
```

## 🔍 Diagnostics

### Check Service Health

```bash
# All services should show "Up" and "healthy"
docker compose ps

# Expected output:
# NAME                    STATUS
# yasaflaskified-redis    Up (healthy)
# yasaflaskified-web      Up (healthy)
# yasaflaskified-worker   Up
```

### Test Web Service

```bash
# Test from within container
docker compose exec web curl -f http://localhost:8000/login

# Test from host
curl http://localhost:8000/login

# Should return HTML login page
```

### Test Worker

```bash
# Check worker logs
docker compose logs worker | grep "Listening on default"

# Should show: "*** Listening on default..."
```

### Test Redis

```bash
# Check Redis connection
docker compose exec redis redis-cli ping
# Should return: PONG

# Check queue
docker compose exec redis redis-cli LLEN rq:queue:default
# Should return: (integer) 0 (or number of jobs)
```

## 🐛 Common Issues

### Issue: Containers won't start

```bash
# Check logs
docker compose logs

# Check for port conflicts
sudo lsof -i :8000

# Kill conflicting processes
sudo pkill -9 -f "gunicorn"

# Restart
docker compose up -d
```

### Issue: Worker not processing jobs

```bash
# Check worker status
docker compose logs worker --tail=50

# Common fix: Restart worker
docker compose restart worker

# If still failing: Rebuild
docker compose down
docker compose build worker
docker compose up -d
```

### Issue: Database errors

```bash
# Check permissions
ls -la instance/

# Fix permissions
chmod 777 instance/
rm -f instance/users.db

# Reinitialize
./docker-init.sh
```

### Issue: "No space left on device"

```bash
# Clean Docker system
docker system prune -a --volumes

# Remove unused images
docker image prune -a

# Check space
df -h
docker system df
```

### Issue: Permission denied errors

```bash
# Fix directory permissions
chmod 777 uploads processed instance

# Or rebuild with proper permissions
docker compose down -v
./docker-init.sh
```

## 🔐 Security

### Default Security Features

- CSRF protection enabled
- Secure session cookies (HTTPOnly, SameSite)
- Rate limiting disabled in Docker (enable in config.json if needed)
- Password hashing with scrypt/pbkdf2

### Enable Rate Limiting

Edit `config.json`:
```json
{
  "ENABLE_RATE_LIMITING": true
}
```

Then restart:
```bash
docker compose restart web
```

### Change Admin Password

1. Login with current password
2. Navigate to user settings
3. Change password in UI

Or via database:
```bash
docker compose exec web python3 -c "
from werkzeug.security import generate_password_hash
from app import app, db, User
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    admin.password = generate_password_hash('NEW_PASSWORD', method='scrypt')
    db.session.commit()
"
```

## 📊 Monitoring

### Resource Usage

```bash
# Real-time stats
docker stats

# Specific container
docker stats yasaflaskified-web
```

### Disk Usage

```bash
# Docker disk usage
docker system df

# Detailed breakdown
docker system df -v
```

### Logs Rotation

Docker automatically rotates logs. Configure in daemon.json:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## 🌐 Production Deployment

### With Nginx Reverse Proxy

```yaml
# Add to docker-compose.yml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
    - ./ssl:/etc/nginx/ssl:ro
  depends_on:
    - web
```

### SSL/HTTPS Setup

```bash
# Get certificates (on host)
sudo certbot certonly --standalone -d yourdomain.com

# Copy to project
mkdir ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/*.pem ssl/

# Update nginx.conf with SSL config
# Restart nginx container
docker compose restart nginx
```

## 📝 Configuration

### Environment Variables

Set in docker-compose.yml:

```yaml
web:
  environment:
    - REDIS_HOST=redis
    - REDIS_PORT=6379
    - PYTHONUNBUFFERED=1
    - CUSTOM_VAR=value
```

### config.json

Main configuration file (auto-generated):
- Located at `./config.json`
- Mounted into both web and worker containers
- Restart containers after changes

### Resource Limits

Add to docker-compose.yml:

```yaml
web:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 2G
```

## 🔄 Backup & Restore

### Backup

```bash
# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p backups

# Backup database
docker compose exec web tar -czf /tmp/db_${DATE}.tar.gz instance/
docker cp yasaflaskified-web:/tmp/db_${DATE}.tar.gz backups/

# Backup uploads and processed
tar -czf backups/data_${DATE}.tar.gz uploads/ processed/

# Backup config
cp config.json backups/config_${DATE}.json

echo "Backup complete: backups/"
```

### Restore

```bash
# Restore from backup
docker compose down

# Restore data
tar -xzf backups/data_YYYYMMDD_HHMMSS.tar.gz

# Restore database
tar -xzf backups/db_YYYYMMDD_HHMMSS.tar.gz

# Restore config
cp backups/config_YYYYMMDD_HHMMSS.json config.json

# Restart
docker compose up -d
```

## 📚 Additional Resources

- Docker Documentation: https://docs.docker.com/
- Docker Compose: https://docs.docker.com/compose/
- Troubleshooting: See main README.md

## ✅ Verification Checklist

After deployment, verify:

- [ ] All 3 containers running (`docker compose ps`)
- [ ] Web service healthy (`curl http://localhost:8000/login`)
- [ ] Worker listening (`docker compose logs worker | grep Listening`)
- [ ] Redis responding (`docker compose exec redis redis-cli ping`)
- [ ] Can login with admin credentials
- [ ] Can upload EDF file
- [ ] Worker processes job
- [ ] Can download results

## 🎯 Quick Reference

**Start:** `./docker-init.sh`  
**Stop:** `docker compose down`  
**Restart:** `docker compose restart`  
**Logs:** `docker compose logs -f`  
**Status:** `docker compose ps`  
**Clean:** `docker compose down -v`  

---

**Version:** 6.0  
**Status:** Production Ready ✅
