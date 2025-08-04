# OurTube Production Deployment Guide

## 🚀 Quick Start

```bash
# 1. Clone repository
git clone <your-repo-url>
cd OurTube

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Deploy with Docker
./deploy.sh
```

## 📋 Pre-Deployment Checklist

### Security
- [ ] Change default passwords
- [ ] Configure ALLOWED_ORIGINS in .env
- [ ] Set up HTTPS (see nginx config below)
- [ ] Configure firewall rules
- [ ] Enable rate limiting
- [ ] Review download directory permissions

### Configuration
- [ ] Set MAX_CONCURRENT_DOWNLOADS based on server capacity
- [ ] Configure DOWNLOAD_DIR with adequate storage
- [ ] Set up log rotation
- [ ] Configure monitoring (optional)

## 🐳 Docker Deployment Options

### Option 1: Standard Deployment
```bash
docker-compose up -d --build
```

### Option 2: Production Deployment
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### Option 3: Custom Production Build
```bash
docker build -f Dockerfile.prod -t ourtube:latest .
docker run -d \
  --name ourtube \
  -p 80:8000 \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  ourtube:latest
```

## 🔧 Manual Deployment

### Frontend Build
```bash
cd frontend
npm ci --production
npm run build
```

### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# Run with gunicorn
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## 🔒 Nginx Configuration (HTTPS)

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/api/health
```

### Logs
```bash
# Docker logs
docker-compose logs -f

# Application logs
tail -f logs/ourtube.log
```

### Metrics to Monitor
- Active downloads count
- WebSocket connections
- Disk space usage
- Memory/CPU usage
- Error rates

## 🔄 Updates

### Update yt-dlp
```bash
# Via API
curl -X POST http://localhost:8000/api/update-ytdlp

# Manual in container
docker exec ourtube yt-dlp -U
```

### Update Application
```bash
git pull
docker-compose down
docker-compose up -d --build
```

## 🐛 Troubleshooting

### Common Issues

1. **FFmpeg not found**
   - Solution: Ensure FFmpeg is installed in container
   - Check: `docker exec ourtube ffmpeg -version`

2. **Permission errors**
   - Solution: Check directory ownership
   - Fix: `chown -R 1001:1001 ./downloads`

3. **High memory usage**
   - Solution: Reduce MAX_CONCURRENT_DOWNLOADS
   - Monitor: `docker stats ourtube`

4. **WebSocket connection fails**
   - Solution: Check nginx/proxy configuration
   - Ensure WebSocket headers are forwarded

### Debug Mode
```bash
# Run with debug logging
LOG_LEVEL=DEBUG docker-compose up
```

## 🔐 Security Best Practices

1. **Use HTTPS** - Always use SSL/TLS in production
2. **Firewall** - Only expose necessary ports
3. **Updates** - Keep yt-dlp and dependencies updated
4. **Monitoring** - Set up alerts for suspicious activity
5. **Backups** - Regular backup of download history
6. **Rate Limiting** - Configure based on your needs

## 📝 Environment Variables

See `.env.example` for all available options.

Key variables:
- `MAX_CONCURRENT_DOWNLOADS`: Server capacity (default: 3)
- `ALLOWED_ORIGINS`: CORS whitelist
- `RATE_LIMIT_REQUESTS`: Requests per window
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR

## 🚨 Production Readiness

Before going live:
1. Test all endpoints with `test_endpoints.py`
2. Run security scan
3. Configure monitoring/alerting
4. Set up backup strategy
5. Document recovery procedures

## 📞 Support

- Issues: GitHub Issues
- Logs: Check `/app/logs/ourtube.log`
- Health: `GET /api/health`