# Tibbiy Konsultatsiya - Production Deployment Guide

## 🚀 Production Deployment

### Prerequisites

- Ubuntu 20.04+ / CentOS 8+ server
- Minimum 2GB RAM, 2 CPU cores
- Domain name va SSL sertifikat
- PostgreSQL 13+
- Redis 6+
- Nginx
- Git

## 🖥️ Server Setup

### 1. Server Tayyorlash

```bash
# Tizimni yangilash
sudo apt update && sudo apt upgrade -y

# Kerakli packages
sudo apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib redis-server git curl software-properties-common

# Python 3.9+
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-dev
```

### 2. PostgreSQL Sozlash

```bash
# PostgreSQL ishga tushirish
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Database yaratish
sudo -u postgres psql

-- PostgreSQL console'da
CREATE DATABASE medical_consultation_db;
CREATE USER medical_user WITH PASSWORD 'your_strong_password';
GRANT ALL PRIVILEGES ON DATABASE medical_consultation_db TO medical_user;
ALTER USER medical_user CREATEDB;
\q
```

### 3. Redis Sozlash

```bash
# Redis konfiguratsiya
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Redis test
redis-cli ping
# PONG javob qaytishi kerak
```

### 4. User yaratish

```bash
# System user
sudo adduser medical
sudo usermod -aG sudo medical
sudo su - medical
```

## 📥 Application Deployment

### 1. Loyihani Clone Qilish

```bash
# Home directory'da
cd /home/medical
git clone <your-repository-url> medical_consultation
cd medical_consultation
```

### 2. Virtual Environment

```bash
# Python virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### 3. Production Environment

`.env` fayl yaratish:

```bash
nano .env
```

```env
# Production Settings
SECRET_KEY=your-super-secret-production-key-here-minimum-50-characters
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,your-server-ip

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=medical_consultation_db
DB_USER=medical_user
DB_PASSWORD=your_strong_password
DB_HOST=localhost
DB_PORT=5432

# AI Services
GOOGLE_API_KEY=your-production-gemini-api-key

# Redis
REDIS_URL=redis://localhost:6379/0

# Email (SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Media and Static
MEDIA_ROOT=/home/medical/medical_consultation/media/
STATIC_ROOT=/home/medical/medical_consultation/staticfiles/

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True

# Logging
LOG_LEVEL=INFO
```

### 4. Database Migration

```bash
# Migrations
python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate

# Superuser yaratish
python manage.py createsuperuser

# Test data (agar kerak bo'lsa)
python manage.py create_test_data
```

### 5. Static Files

```bash
# Static files yig'ish
python manage.py collectstatic --noinput

# Ruxsatlar
sudo chown -R medical:medical /home/medical/medical_consultation/
sudo chmod -R 755 /home/medical/medical_consultation/
```

## 🔧 Gunicorn Configuration

### 1. Gunicorn Socket

```bash
sudo nano /etc/systemd/system/medical_gunicorn.socket
```

```ini
[Unit]
Description=gunicorn socket for Medical Consultation

[Socket]
ListenStream=/run/medical_gunicorn.sock

[Install]
WantedBy=sockets.target
```

### 2. Gunicorn Service

```bash
sudo nano /etc/systemd/system/medical_gunicorn.service
```

```ini
[Unit]
Description=gunicorn daemon for Medical Consultation
Requires=medical_gunicorn.socket
After=network.target

[Service]
User=medical
Group=medical
WorkingDirectory=/home/medical/medical_consultation
Environment="PATH=/home/medical/medical_consultation/venv/bin"
ExecStart=/home/medical/medical_consultation/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/medical_gunicorn.sock \
          Medical_consultation.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### 3. Gunicorn Ishga Tushirish

```bash
# Service'larni yoqish
sudo systemctl start medical_gunicorn.socket
sudo systemctl enable medical_gunicorn.socket

# Status tekshirish
sudo systemctl status medical_gunicorn.socket
sudo systemctl status medical_gunicorn.service

# Test
curl --unix-socket /run/medical_gunicorn.sock localhost
```

## 🌐 Nginx Configuration

### 1. Nginx Site Configuration

```bash
sudo nano /etc/nginx/sites-available/medical_consultation
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL redirect
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Static files
    location /static/ {
        alias /home/medical/medical_consultation/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /home/medical/medical_consultation/media/;
        expires 1M;
        add_header Cache-Control "public";
    }
    
    # Django application
    location / {
        include proxy_params;
        proxy_pass http://unix:/run/medical_gunicorn.sock;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
    
    # Security
    location ~ /\.ht {
        deny all;
    }
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
}
```

### 2. Nginx Yoqish

```bash
# Site yoqish
sudo ln -s /etc/nginx/sites-available/medical_consultation /etc/nginx/sites-enabled/

# Default site o'chirish
sudo rm /etc/nginx/sites-enabled/default

# Nginx test
sudo nginx -t

# Nginx restart
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## 🔒 SSL Certificate (Let's Encrypt)

### 1. Certbot O'rnatish

```bash
# Certbot
sudo apt install snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot

# Certbot link
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

### 2. SSL Certificate Olish

```bash
# Domain uchun SSL
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal test
sudo certbot renew --dry-run
```

## 📊 Monitoring va Logging

### 1. Systemd Journal

```bash
# Gunicorn logs
sudo journalctl -u medical_gunicorn.service -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 2. Application Logs

```bash
# Django logs
tail -f /home/medical/medical_consultation/logs/django.log

# AI service logs
tail -f /home/medical/medical_consultation/logs/ai_assistant.log
```

### 3. Log Rotation

```bash
sudo nano /etc/logrotate.d/medical_consultation
```

```
/home/medical/medical_consultation/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 medical medical
    postrotate
        systemctl reload medical_gunicorn.service
    endscript
}
```

## 🔄 Backup Strategy

### 1. Database Backup Script

```bash
nano /home/medical/backup_db.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/medical/backups"
DB_NAME="medical_consultation_db"
DB_USER="medical_user"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Media files backup
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz /home/medical/medical_consultation/media/

# Old backups o'chirish (30 kundan eski)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x /home/medical/backup_db.sh
```

### 2. Cron Job

```bash
crontab -e
```

```bash
# Har kuni ertalab 2:00 da backup
0 2 * * * /home/medical/backup_db.sh >> /home/medical/backup.log 2>&1
```

## 🔧 Maintenance

### 1. Update Script

```bash
nano /home/medical/update_app.sh
```

```bash
#!/bin/bash
cd /home/medical/medical_consultation

# Git pull
git pull origin main

# Virtual environment
source venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Django tasks
python manage.py collectstatic --noinput
python manage.py migrate

# Restart services
sudo systemctl restart medical_gunicorn.service
sudo systemctl reload nginx

echo "Update completed: $(date)"
```

```bash
chmod +x /home/medical/update_app.sh
```

### 2. Health Check Script

```bash
nano /home/medical/health_check.sh
```

```bash
#!/bin/bash

# Gunicorn status
if ! systemctl is-active --quiet medical_gunicorn.service; then
    echo "Gunicorn is down, restarting..."
    sudo systemctl restart medical_gunicorn.service
fi

# Nginx status
if ! systemctl is-active --quiet nginx; then
    echo "Nginx is down, restarting..."
    sudo systemctl restart nginx
fi

# Database connection
if ! python /home/medical/medical_consultation/manage.py check --database default; then
    echo "Database connection failed!"
fi

# Disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "Disk usage is high: $DISK_USAGE%"
fi
```

## 🚨 Security Checklist

### 1. Firewall

```bash
# UFW firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
```

### 2. Fail2Ban

```bash
# Fail2ban o'rnatish
sudo apt install fail2ban

# Nginx protection
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true

[nginx-noscript]
enabled = true

[nginx-badbots]
enabled = true

[nginx-noproxy]
enabled = true
```

### 3. Regular Updates

```bash
# Cron job for security updates
echo "0 6 * * * apt update && apt upgrade -y" | sudo crontab -
```

## 📈 Performance Optimization

### 1. PostgreSQL Tuning

```bash
sudo nano /etc/postgresql/13/main/postgresql.conf
```

```ini
# Memory
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB

# Connections
max_connections = 100

# WAL
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

### 2. Redis Optimization

```bash
sudo nano /etc/redis/redis.conf
```

```ini
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## 🔍 Troubleshooting

### 1. Common Issues

```bash
# Permission errors
sudo chown -R medical:medical /home/medical/medical_consultation/
sudo chmod -R 755 /home/medical/medical_consultation/

# Service status
sudo systemctl status medical_gunicorn.service
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis-server

# Logs
sudo journalctl -u medical_gunicorn.service -n 50
sudo tail -f /var/log/nginx/error.log
```

### 2. Database Issues

```bash
# Connection test
python manage.py check --database default

# Database rebuild
python manage.py flush
python manage.py migrate
```

### 3. SSL Issues

```bash
# Certificate status
sudo certbot certificates

# Renew
sudo certbot renew --force-renewal
```

## 📊 Monitoring Setup

### 1. Simple Health Check

```bash
# API health check
curl -f https://yourdomain.com/api/health/ || echo "API down"

# Database check
python manage.py check --database default
```

### 2. Server Monitoring

```bash
# System resources
htop
df -h
free -h
systemctl status
```

## 🚀 Final Steps

1. **Test barcha funksiyalar**
2. **SSL sertifikat tekshirish**
3. **Backup script test qilish**
4. **Performance monitoring**
5. **Security scan o'tkazish**

Production deployment muvaffaqiyatli tugallandi! 🎉

### Support URLs

- **Website**: https://yourdomain.com
- **Admin**: https://yourdomain.com/admin/
- **API Docs**: https://yourdomain.com/docs/
- **Health Check**: https://yourdomain.com/api/health/