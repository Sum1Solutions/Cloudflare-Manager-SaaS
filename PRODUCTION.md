# Production Deployment Guide

This guide covers deploying the Cloudflare Manager to production with security considerations.

## Security Checklist

### ✅ Prerequisites Completed
- [x] All dependency vulnerabilities fixed
- [x] Configurable authentication (Auth0/Cloudflare Access) integrated
- [x] Debug mode configurable via environment
- [x] Secret keys externalized to environment variables
- [x] Sensitive files properly gitignored
- [x] Comprehensive test suite passing
- [x] Tested with multiple domains in real environments

## 🔧 Environment Configuration

### 1. Required Environment Variables

Copy `.env.example` to `.env.production` and configure:

```bash
# Cloudflare API Credentials
CLOUDFLARE_EMAIL=your-email@domain.com
CLOUDFLARE_API_KEY=your-global-api-key
CLOUDFLARE_ACCOUNT_ID=your-account-id

# Authentication Configuration (choose one method)
AUTH_METHOD=auth0  # or 'cloudflare_access'

# Auth0 Configuration (if AUTH_METHOD=auth0)
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret

# Cloudflare Access (if AUTH_METHOD=cloudflare_access)
# No additional config - uses Cloudflare headers

# Application Security - CRITICAL
SECRET_KEY=your-secure-random-key-32-chars-minimum

# Production Settings
FLASK_DEBUG=false
HOST=0.0.0.0
PORT=5001
```

### 2. Generate Secure Keys

```bash
# Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

## 🌐 Deployment Options

### Option A: Traditional VPS/Server

#### Install Dependencies
```bash
# Python 3.11+ required
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv nginx

# Create application directory
sudo mkdir -p /opt/cloudflare-manager
cd /opt/cloudflare-manager

# Clone repository
git clone https://github.com/Sum1Solutions/Cloudflare-Manager.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Production WSGI Server
```bash
# Install Gunicorn
pip install gunicorn

# Create Gunicorn configuration
cat > gunicorn.conf.py << EOF
bind = "0.0.0.0:5001"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 5
preload_app = True
EOF

# Start with Gunicorn
gunicorn --config gunicorn.conf.py app:app
```

#### Systemd Service
```bash
# Create systemd service
sudo cat > /etc/systemd/system/cloudflare-manager.service << EOF
[Unit]
Description=Cloudflare Manager
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/cloudflare-manager
Environment=PATH=/opt/cloudflare-manager/venv/bin
ExecStart=/opt/cloudflare-manager/venv/bin/gunicorn --config gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable cloudflare-manager
sudo systemctl start cloudflare-manager
```

#### Nginx Reverse Proxy
```bash
# Create Nginx configuration
sudo cat > /etc/nginx/sites-available/cloudflare-manager << EOF
server {
    listen 80;
    server_name sum1solutions.com cloudflaremanager.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name sum1solutions.com cloudflaremanager.com;
    
    # SSL Configuration (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/sum1solutions.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sum1solutions.com/privkey.pem;
    
    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/cloudflare-manager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Option B: Docker Deployment

#### Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -r -s /bin/false appuser
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5001/health || exit 1

EXPOSE 5001

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "app:app"]
```

#### Docker Compose
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5001:5001"
    environment:
      - FLASK_DEBUG=false
    env_file:
      - .env.production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Option C: Cloudflare Pages + Workers (Serverless)

The `pages-migration/` directory contains a serverless version using:
- **Cloudflare Pages** for hosting
- **Cloudflare D1** for database  
- **Cloudflare Workers** for API endpoints

```bash
cd pages-migration

# Deploy to Cloudflare Pages
wrangler pages deploy public/ --project-name=cloudflare-manager

# Configure environment variables in Cloudflare dashboard
wrangler secret put AUTH0_DOMAIN
wrangler secret put AUTH0_CLIENT_ID  
wrangler secret put AUTH0_CLIENT_SECRET
wrangler secret put CLOUDFLARE_EMAIL
wrangler secret put CLOUDFLARE_API_KEY
```

## 🔒 Security Configuration

### Auth0 Production Setup

1. **Create Production Auth0 Application**
   - Type: Regular Web Application
   - Update callback URLs for production domains

2. **Configure Production URLs**
   ```
   Allowed Callback URLs:
   https://sum1solutions.com/callback,
   https://cloudflaremanager.com/callback
   
   Allowed Logout URLs:
   https://sum1solutions.com/logged_out,
   https://cloudflaremanager.com/logged_out
   
   Allowed Web Origins:
   https://sum1solutions.com,
   https://cloudflaremanager.com
   ```

### SSL/TLS Certificate

```bash
# Install Certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d sum1solutions.com -d cloudflaremanager.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Monitoring & Logging

### Health Check Endpoint
Add to your `app.py`:

```python
@app.route('/health')
def health_check():
    """Health check endpoint for load balancers."""
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
```

### Production Logging
```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('logs/cloudflare-manager.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
```

## 🚨 Final Production Checklist

- [ ] All environment variables configured
- [ ] SECRET_KEY is cryptographically random (32+ characters)
- [ ] FLASK_DEBUG=false in production
- [ ] SSL/TLS certificates installed and configured
- [ ] Auth0 production application configured with correct URLs  
- [ ] Database backups configured
- [ ] Monitoring and logging setup
- [ ] Health checks working
- [ ] Security headers configured in reverse proxy
- [ ] Firewall configured (only ports 22, 80, 443 open)
- [ ] Regular security updates scheduled
- [ ] Backup and disaster recovery plan documented

## 🎯 Performance Optimization

- Use **Gunicorn** with multiple workers in production
- Configure **Nginx** reverse proxy with caching
- Enable **gzip compression**
- Set appropriate **cache headers**
- Consider **CDN** for static assets
- Monitor with **application performance monitoring (APM)**

## 🔄 Deployment Pipeline

Consider setting up CI/CD with:
- **GitHub Actions** for automated testing
- **Automated security scanning** 
- **Blue-green deployments**
- **Database migration handling**
- **Rollback procedures**

---

The application is now deployed. Test thoroughly before using with important domains.