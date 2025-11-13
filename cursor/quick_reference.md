# KiotProxy Manager - Quick Reference (Simplified)

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Domain with wildcard DNS configured (*.domain.com → your server IP)

### First Time Setup
```bash
# 1. Clone repository
git clone <repo>
cd kiot-prod

# 2. Configure environment
cp .env.example .env
nano .env  # Set your DOMAIN

# 3. Start services
docker-compose up -d

# 4. Check logs
docker-compose logs -f

# 5. Access UI
# Open browser: http://app.domain.com
# Default login: admin / changeme123
```

---

## API Quick Reference

### Authentication

**Login**
```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "changeme123"
}

# Returns:
{
  "session_id": "abc123...",
  "username": "admin"
}
```

**Logout**
```bash
POST /api/auth/logout
Cookie: session_id=abc123...
```

---

### Proxy Management

**List All Proxies**
```bash
GET /api/proxies
Cookie: session_id=abc123...

# Returns:
[
  {
    "id": 1,
    "key_name": "My Proxy 1",
    "subdomain": "proxy1",
    "endpoint": "proxy1.domain.com",
    "remote_ip": "171.243.255.207",
    "location": "Bình Thuận",
    "status": "active",
    "latency_ms": 539,
    "ttc": 847
  },
  ...
]
```

**Add New Proxy**
```bash
POST /api/proxies
Cookie: session_id=abc123...
Content-Type: application/json

{
  "key_name": "My Proxy 1",
  "kiotproxy_key": "K6fa3db6...4a77ce",
  "region": "random"
}

# Returns:
{
  "id": 1,
  "endpoint": "proxy1.domain.com",
  "remote_ip": "171.243.255.207",
  "location": "Bình Thuận"
}
```

**Rotate Proxy**
```bash
POST /api/proxies/1/rotate
Cookie: session_id=abc123...
Content-Type: application/json

{
  "region": "nam"
}

# Returns:
{
  "new_ip": "116.97.68.237",
  "location": "Thanh Hóa",
  "ttc": 1200
}
```

**Delete Proxy**
```bash
DELETE /api/proxies/1
Cookie: session_id=abc123...
```

**Restart Proxy**
```bash
POST /api/proxies/1/restart
Cookie: session_id=abc123...
```

**Get Settings**
```bash
GET /api/settings
Cookie: session_id=abc123...

# Returns:
{
  "auto_rotate_on_expiration": true,
  "auto_rotate_interval_enabled": false,
  "auto_rotate_interval_minutes": 10
}
```

**Update Settings**
```bash
PUT /api/settings
Cookie: session_id=abc123...
Content-Type: application/json

{
  "auto_rotate_on_expiration": true,
  "auto_rotate_interval_enabled": true,
  "auto_rotate_interval_minutes": 5
}

# Returns:
{
  "success": true,
  "settings": {
    "auto_rotate_on_expiration": true,
    "auto_rotate_interval_enabled": true,
    "auto_rotate_interval_minutes": 5
  }
}
```

---

## Using the Proxies

### With cURL
```bash
# Basic usage
curl -x http://proxy1.domain.com:80 https://ipinfo.io

# Check your IP
curl -x http://proxy1.domain.com:80 https://api.ipify.org

# With authentication if needed
curl -x http://proxy1.domain.com:80 https://example.com
```

### With Browser

**Chrome**
```bash
# Windows
chrome.exe --proxy-server="http://proxy1.domain.com:80"

# macOS/Linux
google-chrome --proxy-server="http://proxy1.domain.com:80"
```

**Firefox**
```
Settings → Network Settings → Manual proxy configuration
HTTP Proxy: proxy1.domain.com
Port: 80
✅ Also use this proxy for HTTPS
```

### With Python
```python
import requests

# Configure proxy
proxies = {
    'http': 'http://proxy1.domain.com:80',
    'https': 'http://proxy1.domain.com:80'
}

# Make request
response = requests.get('https://ipinfo.io', proxies=proxies)
print(response.json())
```

### With Node.js
```javascript
const axios = require('axios');

axios.get('https://ipinfo.io', {
  proxy: {
    host: 'proxy1.domain.com',
    port: 80
  }
})
.then(response => console.log(response.data))
.catch(error => console.error(error));
```

### With wget
```bash
wget -e use_proxy=yes \
     -e http_proxy=http://proxy1.domain.com:80 \
     -e https_proxy=http://proxy1.domain.com:80 \
     https://ipinfo.io
```

---

## Docker Commands

### Service Management
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart backend

# View logs
docker-compose logs -f backend

# Check status
docker-compose ps
```

### Data Management
```bash
# Backup data
docker-compose exec backend cat /app/data/data.json > backup.json

# Restore data
cat backup.json | docker-compose exec -T backend tee /app/data/data.json

# View current data
docker-compose exec backend cat /app/data/data.json | jq
```

### Debugging
```bash
# Enter backend container
docker-compose exec backend /bin/bash

# Check proxy handlers
docker-compose exec backend ps aux | grep proxy

# View Traefik config
docker-compose exec backend cat /app/traefik/dynamic/proxies.yml

# Test internal proxy
docker-compose exec backend curl -x http://localhost:9001 https://ipinfo.io
```

---

## Configuration Files

### .env
```bash
# Domain configuration
DOMAIN=yourdomain.com

# Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123

# KiotProxy API
KIOTPROXY_API_BASE=https://api.kiotproxy.com/api/v1

# Proxy configuration
PROXY_PORT_START=9000
PROXY_PORT_END=9100

# Health check interval (seconds)
HEALTH_CHECK_INTERVAL=30

# Auto-rotation check interval (seconds)
AUTO_ROTATION_CHECK_INTERVAL=60
```

### data.json Structure
```json
{
  "settings": {
    "auto_rotate_on_expiration": true,
    "auto_rotate_interval_enabled": false,
    "auto_rotate_interval_minutes": 10
  },
  "users": [
    {
      "id": 1,
      "username": "admin",
      "password": "$2b$12$...",
      "session_id": "abc123",
      "session_expires": "2025-11-14T10:00:00Z"
    }
  ],
  "proxy_keys": [
    {
      "id": 1,
      "user_id": 1,
      "key_name": "My Proxy",
      "kiotproxy_key": "K6fa3db6...",
      "subdomain": "proxy1",
      "port": 9001,
      "region": "random",
      "is_active": true,
      "remote_http": "171.243.255.207:31194",
      "remote_ip": "171.243.255.207",
      "location": "Bình Thuận",
      "status": "active",
      "latency_ms": 539,
      "last_check_at": "2025-11-13T10:30:00Z",
      "expiration_at": "2025-11-13T12:00:00Z",
      "ttl": 1200,
      "ttc": 847,
      "last_rotated_at": "2025-11-13T09:00:00Z",
      "created_at": "2025-11-13T09:00:00Z"
    }
  ],
  "logs": [
    {
      "id": 1,
      "proxy_id": 1,
      "action": "create",
      "status": "success",
      "timestamp": "2025-11-13T09:00:00Z"
    }
  ]
}
```

---

## DNS Configuration

### Required DNS Records
```
A     yourdomain.com         → YOUR_SERVER_IP
A     *.yourdomain.com       → YOUR_SERVER_IP
```

This allows:
- `app.yourdomain.com` → Frontend UI
- `proxy1.yourdomain.com` → Proxy 1
- `proxy2.yourdomain.com` → Proxy 2
- `proxy3.yourdomain.com` → Proxy 3
- etc.

### Testing DNS
```bash
# Check if wildcard DNS works
nslookup proxy1.yourdomain.com
nslookup proxy2.yourdomain.com
nslookup app.yourdomain.com

# Should all resolve to YOUR_SERVER_IP
```

---

## Troubleshooting

### Proxy Not Working

**Check if proxy exists**
```bash
curl -b "session_id=xxx" http://app.domain.com/api/proxies
```

**Check proxy handler is running**
```bash
docker-compose exec backend ps aux | grep 9001
```

**Test proxy directly**
```bash
curl -x http://proxy1.domain.com:80 https://ipinfo.io -v
```

**Check Traefik routing**
```bash
docker-compose exec backend cat /app/traefik/dynamic/proxies.yml
```

**View backend logs**
```bash
docker-compose logs backend | grep proxy1
```

---

### Cannot Login

**Reset admin password**
```bash
# Stop backend
docker-compose stop backend

# Edit data.json manually
docker-compose exec backend nano /app/data/data.json

# Or reset with new password (requires Python bcrypt)
python3 -c "import bcrypt; print(bcrypt.hashpw(b'newpassword', bcrypt.gensalt()).decode())"

# Update data.json with new hash
# Restart
docker-compose start backend
```

---

### DNS Not Resolving

**Check DNS records**
```bash
dig yourdomain.com
dig proxy1.yourdomain.com
```

**If local development, use /etc/hosts**
```bash
# Add to /etc/hosts (Linux/Mac)
127.0.0.1  app.domain.com
127.0.0.1  proxy1.domain.com
127.0.0.1  proxy2.domain.com

# Windows: C:\Windows\System32\drivers\etc\hosts
```

---

### High Latency

**Check proxy status**
```bash
curl -b "session_id=xxx" http://app.domain.com/api/proxies
# Look at latency_ms field
```

**Rotate to new proxy**
```bash
curl -X POST -b "session_id=xxx" \
  -H "Content-Type: application/json" \
  -d '{"region":"random"}' \
  http://app.domain.com/api/proxies/1/rotate
```

**Try different region**
- `bac` - North Vietnam (usually faster from north)
- `trung` - Central Vietnam
- `nam` - South Vietnam  
- `random` - Any region

---

### Traefik Not Routing

**Check Traefik logs**
```bash
docker-compose logs traefik
```

**Check if config file exists**
```bash
docker-compose exec backend cat /app/traefik/dynamic/proxies.yml
```

**Restart Traefik**
```bash
docker-compose restart traefik
```

**Check Traefik dashboard** (if enabled)
```
http://YOUR_SERVER_IP:8080
```

---

## Common Workflows

### Workflow 1: First Time Setup

```bash
# 1. Configure DNS
# Point *.yourdomain.com to your server

# 2. Update .env
nano .env
# Set DOMAIN=yourdomain.com

# 3. Start services
docker-compose up -d

# 4. Login to UI
# Go to http://app.yourdomain.com
# Login: admin / changeme123

# 5. Add first proxy
# Click "Add Proxy"
# Enter KiotProxy API key
# Choose region

# 6. Copy endpoint
# Get: proxy1.yourdomain.com

# 7. Configure your app
# Set HTTP proxy to: proxy1.yourdomain.com:80

# 8. Test
curl -x http://proxy1.yourdomain.com:80 https://ipinfo.io
```

---

### Workflow 2: Adding Multiple Proxies

```bash
# Method 1: Via UI
# - Click "Add Proxy" for each key
# - Each gets unique subdomain (proxy1, proxy2, proxy3...)

# Method 2: Via API
for key in "K6fa3db6..." "K036684f..." "K1abfba7..."; do
  curl -X POST -b "session_id=xxx" \
    -H "Content-Type: application/json" \
    -d "{\"key_name\":\"Proxy\",\"kiotproxy_key\":\"$key\",\"region\":\"random\"}" \
    http://app.domain.com/api/proxies
done
```

---

### Workflow 3: Rotating All Proxies

```bash
# Get all proxy IDs
PROXIES=$(curl -b "session_id=xxx" http://app.domain.com/api/proxies | jq -r '.[].id')

# Rotate each
for id in $PROXIES; do
  echo "Rotating proxy $id..."
  curl -X POST -b "session_id=xxx" \
    -H "Content-Type: application/json" \
    -d '{"region":"random"}' \
    http://app.domain.com/api/proxies/$id/rotate
  sleep 2
done
```

---

### Workflow 4: Monitoring Health

```bash
# Continuous monitoring
watch -n 5 'curl -s -b "session_id=xxx" http://app.domain.com/api/proxies | jq ".[] | {name:.key_name, endpoint:.endpoint, status:.status, latency:.latency_ms}"'

# Output:
# {
#   "name": "My Proxy 1",
#   "endpoint": "proxy1.domain.com",
#   "status": "active",
#   "latency": 539
# }
```

---

### Workflow 5: Configure Auto-Rotation

#### Option 1: Auto-rotate on expiration (Default)
```bash
# Enable auto-rotation when proxies expire (~30 mins)
curl -X PUT -b "session_id=xxx" \
  -H "Content-Type: application/json" \
  -d '{"auto_rotate_on_expiration":true,"auto_rotate_interval_enabled":false}' \
  http://app.domain.com/api/settings

# This will automatically rotate proxies when they reach expiration_at timestamp
# Works individually for each proxy based on its expiration time
```

#### Option 2: Timed auto-rotation (Custom interval)
```bash
# Rotate ALL proxies every 5 minutes
curl -X PUT -b "session_id=xxx" \
  -H "Content-Type: application/json" \
  -d '{"auto_rotate_on_expiration":false,"auto_rotate_interval_enabled":true,"auto_rotate_interval_minutes":5}' \
  http://app.domain.com/api/settings

# Minimum interval: 2 minutes
# Maximum interval: No limit (but recommended < 60 minutes)
# Applies to ALL active proxies simultaneously
```

#### Option 3: Both enabled (Interval takes priority)
```bash
# Enable both: Will rotate based on interval (overrides expiration)
curl -X PUT -b "session_id=xxx" \
  -H "Content-Type: application/json" \
  -d '{"auto_rotate_on_expiration":true,"auto_rotate_interval_enabled":true,"auto_rotate_interval_minutes":10}' \
  http://app.domain.com/api/settings

# With this config, proxies will rotate every 10 minutes
```

#### Check Current Settings
```bash
curl -b "session_id=xxx" http://app.domain.com/api/settings | jq

# Returns:
# {
#   "auto_rotate_on_expiration": true,
#   "auto_rotate_interval_enabled": false,
#   "auto_rotate_interval_minutes": 10
# }
```

#### Use Cases
- **Expiration mode**: Good for normal use, lets each proxy live its full TTL (~30 mins)
- **2-min interval**: Maximum IP changes, good for avoiding rate limits
- **5-min interval**: Balanced between IP freshness and API calls
- **30-min interval**: Minimal rotation, good for stable sessions

---

## Performance Tips

### For Better Speed
1. Choose nearest region (bac/trung/nam based on your location)
2. Rotate proxies that have high latency (>1000ms)
3. Avoid overloading single proxy (distribute load across multiple)

### For Better Reliability
1. Add multiple proxy keys as backup
2. Enable auto-rotation (background worker handles this)
3. Monitor health regularly

### For Many Proxies (50+)
Increase resource limits in docker-compose.yml:
```yaml
backend:
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: '2'
```

---

## Testing Checklist

- [ ] DNS resolves correctly (app.domain.com, proxy1.domain.com)
- [ ] Can access UI at app.domain.com
- [ ] Can login with admin credentials
- [ ] Can add new proxy key
- [ ] Proxy endpoint is assigned (proxy1.domain.com)
- [ ] Can use proxy with curl
- [ ] Can use proxy with browser
- [ ] Can rotate proxy
- [ ] Endpoint stays same after rotation
- [ ] Status shows correct latency
- [ ] Health check updates every 30s
- [ ] Logs show all operations
- [ ] Can delete proxy
- [ ] Endpoint is released after deletion

---

## Security Notes

### Production Checklist
- [ ] Change default admin password
- [ ] Enable HTTPS (configure Let's Encrypt in Traefik)
- [ ] Restrict access to specific IPs if possible
- [ ] Regular backups of data.json
- [ ] Monitor logs for suspicious activity
- [ ] Keep Docker images updated

### Enabling HTTPS
Already configured in docker-compose.yml! Just update:
```yaml
traefik:
  command:
    - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
```

Traefik will automatically get SSL certificates for:
- app.domain.com
- proxy1.domain.com
- proxy2.domain.com
- etc.

---

## Backup & Restore

### Manual Backup
```bash
# Backup data
cp data/data.json data/data.json.backup-$(date +%Y%m%d)

# Backup Traefik config
cp traefik/dynamic/proxies.yml traefik/dynamic/proxies.yml.backup
```

### Automated Backup (Cron)
```bash
# Add to crontab
0 2 * * * cd /path/to/kiot-prod && cp data/data.json data/data.json.backup-$(date +\%Y\%m\%d)
```

### Restore
```bash
# Stop backend
docker-compose stop backend

# Restore data
cp data/data.json.backup-20251113 data/data.json

# Start backend (will reload data and regenerate Traefik config)
docker-compose start backend
```

---

## Logs

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f traefik

# Last 100 lines
docker-compose logs --tail=100 backend

# With timestamps
docker-compose logs -f -t backend
```

### Log Locations
- Backend logs: `docker-compose logs backend`
- Traefik logs: `docker-compose logs traefik`
- Application logs: Inside container at `/app/logs/app.log`

---

## Quick Commands Summary

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart backend

# Logs
docker-compose logs -f backend

# Test proxy
curl -x http://proxy1.domain.com:80 https://ipinfo.io

# Backup
cp data/data.json backup.json

# Enter container
docker-compose exec backend /bin/bash

# View data
docker-compose exec backend cat /app/data/data.json | jq

# Health check
curl -b "session_id=xxx" http://app.domain.com/api/proxies
```

---

*Quick Reference Version: 2.0*
*Last Updated: November 13, 2025*
*Simplified Architecture with Public Subdomains*
