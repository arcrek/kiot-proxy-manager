# Quick Start Guide

## 5-Minute Setup

### Step 1: Prerequisites
- Docker & Docker Compose installed
- Domain with wildcard DNS: `*.yourdomain.com` → Your Server IP

### Step 2: Setup

```bash
# Clone repository
git clone <repo-url>
cd kiot-prod

# Run setup script
chmod +x setup.sh
./setup.sh

# Or manually:
cp env.example .env
nano .env  # Edit DOMAIN, passwords, SECRET_KEY
docker compose up -d
```

### Step 3: Access

Open: `http://app.yourdomain.com`

Login with credentials from `.env`:
- Username: `admin`
- Password: (what you set in `.env`)

### Step 4: Add Your First Proxy

1. Click **"➕ Add Proxy"**
2. Enter:
   - Name: "My Proxy 1"
   - KiotProxy Key: Your API key from kiotproxy.com
   - Region: Random (or choose North/Central/South)
3. Click **"Create Proxy"**
4. Copy the endpoint: `proxy1.yourdomain.com`

### Step 5: Use the Proxy

**Test with cURL:**
```bash
curl -x http://proxy1.yourdomain.com:80 https://ipinfo.io
```

**With Python:**
```python
import requests
proxies = {
    'http': 'http://proxy1.yourdomain.com:80',
    'https': 'http://proxy1.yourdomain.com:80'
}
response = requests.get('https://ipinfo.io', proxies=proxies)
print(response.json())
```

**With Browser:**
```
Settings → Network → Manual Proxy
HTTP Proxy: proxy1.yourdomain.com
Port: 80
```

## Common Tasks

### View Logs
```bash
docker compose logs -f
```

### Restart Services
```bash
docker compose restart
```

### Stop Services
```bash
docker compose down
```

### Backup Data
```bash
cp data/data.json backup-$(date +%Y%m%d).json
```

## Troubleshooting

### Can't access web UI
- Check DNS: `nslookup app.yourdomain.com`
- Check Docker: `docker compose ps`
- View logs: `docker compose logs backend`

### Proxy not working
- Check status in UI (should show latency)
- Click 🔄 Rotate to get new IP
- Click 🔁 Restart to restart handler

### High latency
- Try different region (North/Central/South)
- Rotate to new proxy
- Check network connection

## Next Steps

- Configure **Auto-Rotation** in Settings
- Add multiple proxy keys
- Set up monitoring
- Enable HTTPS (automatic with Let's Encrypt)

For detailed documentation, see [README.md](README.md)

