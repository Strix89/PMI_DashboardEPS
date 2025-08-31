# PMI Dashboard Installation Guide

This comprehensive guide covers installation, configuration, and deployment of the PMI Dashboard for various environments.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Start](#quick-start)
3. [Development Installation](#development-installation)
4. [Production Installation](#production-installation)
5. [Docker Deployment](#docker-deployment)
6. [Configuration](#configuration)
7. [Proxmox Setup](#proxmox-setup)
8. [Security Configuration](#security-configuration)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

## System Requirements

### Minimum Requirements

- **Operating System**: Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+), macOS 10.15+, Windows 10+
- **Python**: 3.8 or higher
- **Memory**: 512 MB RAM
- **Storage**: 1 GB free space
- **Network**: HTTP/HTTPS access to Proxmox VE servers

### Recommended Requirements

- **Operating System**: Linux (Ubuntu 22.04 LTS, Rocky Linux 9)
- **Python**: 3.11 or higher
- **Memory**: 2 GB RAM
- **Storage**: 5 GB free space (for logs and data)
- **CPU**: 2+ cores
- **Network**: Gigabit network connection

### Browser Compatibility

- **Chrome**: 90+
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+
- **Mobile**: iOS Safari 14+, Chrome Mobile 90+

## Quick Start

For a rapid development setup:

```bash
# Clone repository
git clone <repository-url>
cd pmi_dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy configuration template
cp .env .env.local

# Edit configuration (see Configuration section)
nano .env.local

# Run application
python app.py
```

Access the dashboard at: http://127.0.0.1:5000

## Development Installation

### Step 1: Environment Setup

#### Linux/macOS
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
# sudo yum update -y                    # CentOS/RHEL

# Install Python and development tools
sudo apt install python3 python3-pip python3-venv git -y

# Create project directory
mkdir -p ~/projects
cd ~/projects

# Clone repository
git clone <repository-url>
cd pmi_dashboard
```

#### Windows
```powershell
# Install Python from python.org or Microsoft Store
# Install Git from git-scm.com

# Clone repository
git clone <repository-url>
cd pmi_dashboard
```

### Step 2: Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Upgrade pip
pip install --upgrade pip
```

### Step 3: Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# For development, install additional tools
pip install pytest flake8 black isort mypy
```

### Step 4: Configuration

```bash
# Copy environment template
cp .env .env.local

# Edit configuration
nano .env.local  # Linux/macOS
# notepad .env.local  # Windows
```

Minimum configuration for development:
```bash
SECRET_KEY=dev-secret-key-change-in-production
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=True
LOG_LEVEL=DEBUG
```

### Step 5: Run Development Server

```bash
# Run with Flask development server
python app.py

# Or use Flask CLI
export FLASK_APP=app.py
flask run --host=127.0.0.1 --port=5000 --debug
```

## Production Installation

### Step 1: System Preparation

#### Ubuntu/Debian
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install python3 python3-pip python3-venv nginx supervisor git -y

# Create application user
sudo useradd -m -s /bin/bash pmidashboard
sudo usermod -aG www-data pmidashboard
```

#### CentOS/RHEL
```bash
# Update system
sudo yum update -y

# Install EPEL repository
sudo yum install epel-release -y

# Install required packages
sudo yum install python3 python3-pip nginx supervisor git -y

# Create application user
sudo useradd -m -s /bin/bash pmidashboard
```

### Step 2: Application Setup

```bash
# Switch to application user
sudo su - pmidashboard

# Create application directory
mkdir -p /home/pmidashboard/apps
cd /home/pmidashboard/apps

# Clone repository
git clone <repository-url> pmi-dashboard
cd pmi-dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### Step 3: Production Configuration

```bash
# Create production configuration
cp .env .env.production

# Edit production configuration
nano .env.production
```

Production configuration example:
```bash
# Security
SECRET_KEY=your-very-secure-random-key-here
FLASK_DEBUG=False
FORCE_HTTPS=True

# Server
FLASK_HOST=127.0.0.1
FLASK_PORT=8000

# Paths
DATA_DIR=/home/pmidashboard/data
LOG_FILE=/home/pmidashboard/logs/app.log

# Proxmox
PROXMOX_SSL_VERIFY=True
PROXMOX_TIMEOUT=30

# Performance
METRICS_REFRESH_INTERVAL=15
```

### Step 4: Directory Structure

```bash
# Create required directories
mkdir -p /home/pmidashboard/data
mkdir -p /home/pmidashboard/logs
mkdir -p /home/pmidashboard/backups

# Set permissions
chmod 750 /home/pmidashboard/data
chmod 750 /home/pmidashboard/logs
chmod 750 /home/pmidashboard/backups
```

### Step 5: Systemd Service

Create systemd service file:
```bash
sudo nano /etc/systemd/system/pmi-dashboard.service
```

Service configuration:
```ini
[Unit]
Description=PMI Dashboard
After=network.target

[Service]
Type=exec
User=pmidashboard
Group=pmidashboard
WorkingDirectory=/home/pmidashboard/apps/pmi-dashboard
Environment=PATH=/home/pmidashboard/apps/pmi-dashboard/venv/bin
EnvironmentFile=/home/pmidashboard/apps/pmi-dashboard/.env.production
ExecStart=/home/pmidashboard/apps/pmi-dashboard/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --keepalive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile /home/pmidashboard/logs/access.log \
    --error-logfile /home/pmidashboard/logs/error.log \
    --log-level info \
    app:create_app()
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pmi-dashboard
sudo systemctl start pmi-dashboard
sudo systemctl status pmi-dashboard
```

### Step 6: Nginx Configuration

Create Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/pmi-dashboard
```

Nginx configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Static Files
    location /static/ {
        alias /home/pmidashboard/apps/pmi-dashboard/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        proxy_buffering off;
    }

    # Health Check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/pmi-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Docker Deployment

### Step 1: Dockerfile

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy project
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Create required directories
RUN mkdir -p /app/data /app/logs

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:create_app()"]
```

### Step 2: Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  pmi-dashboard:
    build: .
    ports:
      - "5000:5000"
    environment:
      - SECRET_KEY=your-secret-key-here
      - FLASK_DEBUG=False
      - DATA_DIR=/app/data
      - LOG_FILE=/app/logs/app.log
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./.env.docker:/app/.env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - pmi-dashboard
    restart: unless-stopped
```

### Step 3: Build and Run

```bash
# Build image
docker-compose build

# Run services
docker-compose up -d

# View logs
docker-compose logs -f pmi-dashboard

# Stop services
docker-compose down
```

## Configuration

### Environment Variables

Copy and customize the configuration:
```bash
cp .env .env.local  # Development
cp .env .env.production  # Production
```

Key configuration sections:

#### Flask Application
```bash
SECRET_KEY=your-secret-key-here          # CRITICAL: Change in production!
FLASK_HOST=127.0.0.1                     # Server bind address
FLASK_PORT=5000                          # Server port
FLASK_DEBUG=False                        # Debug mode (False for production)
```

#### Security (Production)
```bash
FORCE_HTTPS=True                         # Force HTTPS redirect
SESSION_TIMEOUT=60                       # Session timeout in minutes
MAX_UPLOAD_SIZE=10                       # Max upload size in MB
```

#### Proxmox Defaults
```bash
PROXMOX_DEFAULT_PORT=8006                # Default Proxmox API port
PROXMOX_SSL_VERIFY=True                  # SSL certificate verification
PROXMOX_TIMEOUT=30                       # API connection timeout
```

#### Monitoring
```bash
METRICS_REFRESH_INTERVAL=10              # Metrics refresh interval (seconds)
```

#### Logging
```bash
LOG_LEVEL=INFO                           # Log level (DEBUG, INFO, WARNING, ERROR)
LOG_FILE=/path/to/logfile.log           # Log file path (optional)
```

### Configuration Validation

The application automatically validates configuration on startup:

```bash
# Check configuration
python -c "from config import Config; print(Config.validate_configuration())"
```

## Proxmox Setup

### Step 1: Create API Token

1. **Access Proxmox Web Interface**: https://your-proxmox-server:8006
2. **Navigate to Datacenter → Permissions → API Tokens**
3. **Click "Add"**
4. **Configure Token**:
   - User: `root@pam` (or dedicated user)
   - Token ID: `monitoring` (or your choice)
   - Privilege Separation: Unchecked (for full permissions)
5. **Save Token**: Copy the token secret (shown only once)

### Step 2: Set Permissions (if using privilege separation)

If using privilege separation, assign these permissions:

- **VM.Monitor**: View VM status and metrics
- **VM.PowerMgmt**: Start, stop, restart VMs
- **Datastore.Audit**: View storage information
- **Sys.Audit**: View system information

### Step 3: Test Connection

```bash
# Test API connection
curl -k -H "Authorization: PVEAPIToken=root@pam!monitoring=your-token-secret" \
  https://your-proxmox-server:8006/api2/json/version
```

### Step 4: Add Node in Dashboard

1. **Access PMI Dashboard**
2. **Click "Add Node"**
3. **Enter Configuration**:
   - Name: Display name
   - Host: IP address or hostname
   - Port: 8006 (default)
   - API Token ID: `root@pam!monitoring`
   - API Token Secret: Your token secret
   - SSL Verify: True (if using valid certificates)
4. **Test Connection**
5. **Save Configuration**

## Security Configuration

### SSL/TLS Setup

#### Self-Signed Certificate (Development)
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

#### Let's Encrypt (Production)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Firewall Configuration

#### UFW (Ubuntu)
```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow application port (if needed)
sudo ufw allow 5000/tcp
```

#### Firewalld (CentOS/RHEL)
```bash
# Enable firewall
sudo systemctl enable --now firewalld

# Allow HTTP/HTTPS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### File Permissions

```bash
# Set secure permissions
chmod 600 .env.production
chmod 750 data/
chmod 750 logs/
chown -R pmidashboard:pmidashboard /home/pmidashboard/
```

## Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check logs
journalctl -u pmi-dashboard -f

# Check configuration
python -c "from config import Config; Config.validate_configuration()"

# Check permissions
ls -la /home/pmidashboard/apps/pmi-dashboard/
```

#### Connection Issues
```bash
# Test Proxmox connectivity
curl -k https://your-proxmox-server:8006/api2/json/version

# Check network connectivity
ping your-proxmox-server
telnet your-proxmox-server 8006
```

#### Performance Issues
```bash
# Check system resources
htop
df -h
free -h

# Check application logs
tail -f /home/pmidashboard/logs/app.log
tail -f /home/pmidashboard/logs/performance.log
```

#### SSL/Certificate Issues
```bash
# Check certificate validity
openssl x509 -in /path/to/certificate.crt -text -noout

# Test SSL connection
openssl s_client -connect your-domain.com:443
```

### Debug Mode

Enable debug mode for troubleshooting:
```bash
# Temporary debug mode
export FLASK_DEBUG=True
export LOG_LEVEL=DEBUG
python app.py

# Or edit configuration
echo "FLASK_DEBUG=True" >> .env.local
echo "LOG_LEVEL=DEBUG" >> .env.local
```

### Log Analysis

```bash
# View application logs
tail -f logs/app.log

# View error logs
tail -f logs/errors.log

# View API logs
tail -f logs/api.log

# Search for specific errors
grep -i "error" logs/app.log
grep -i "failed" logs/errors.log
```

## Maintenance

### Regular Tasks

#### Daily
- Monitor application logs
- Check system resources
- Verify service status

#### Weekly
- Review security logs
- Update system packages
- Check backup integrity

#### Monthly
- Rotate API tokens
- Update application dependencies
- Review and clean old logs

### Backup Strategy

#### Configuration Backup
```bash
#!/bin/bash
# backup-config.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/pmidashboard/backups"

# Create backup
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" \
    /home/pmidashboard/apps/pmi-dashboard/.env.production \
    /home/pmidashboard/data/

# Keep only last 30 days
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +30 -delete
```

#### Database Backup (Future)
```bash
#!/bin/bash
# backup-database.sh
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump pmi_dashboard > "/home/pmidashboard/backups/db_$DATE.sql"
```

### Updates

#### Application Updates
```bash
# Switch to application user
sudo su - pmidashboard

# Navigate to application directory
cd /home/pmidashboard/apps/pmi-dashboard

# Backup current version
cp -r . ../pmi-dashboard-backup-$(date +%Y%m%d)

# Pull updates
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart service
sudo systemctl restart pmi-dashboard
```

#### System Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
sudo yum update -y                      # CentOS/RHEL

# Restart if kernel updated
sudo reboot
```

### Monitoring

#### Health Checks
```bash
# Application health
curl -f http://localhost:5000/health

# Service status
systemctl status pmi-dashboard
systemctl status nginx
```

#### Log Monitoring
```bash
# Set up log monitoring with logrotate
sudo nano /etc/logrotate.d/pmi-dashboard
```

Logrotate configuration:
```
/home/pmidashboard/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 pmidashboard pmidashboard
    postrotate
        systemctl reload pmi-dashboard
    endscript
}
```

This installation guide provides comprehensive coverage for deploying PMI Dashboard in various environments with proper security and maintenance considerations.