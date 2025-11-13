# KiotProxy Manager

A web application to manage KiotProxy API keys with constant public endpoints. Each proxy key gets a unique subdomain (e.g., `proxy1.yourdomain.com`) that automatically forwards HTTP/HTTPS traffic through KiotProxy.

## Features

✨ **Constant Public Endpoints** - Each proxy key gets a subdomain that never changes  
🔄 **Auto-Rotation** - Two rotation modes: on expiration (30 mins) or custom interval (min 2 mins)  
📊 **Health Monitoring** - Real-time latency and status tracking  
🌍 **Region Selection** - Choose North, Central, South Vietnam or Random  
🎨 **Modern UI** - Clean, responsive React interface  
🐳 **Docker Ready** - One-command deployment with Traefik auto-configuration  

## Architecture

```
User App → proxy1.yourdomain.com → Traefik → Backend → KiotProxy → Internet
```

When the proxy rotates, the subdomain stays the same, only the backend route changes.

## Prerequisites

- **Docker** and **Docker Compose** installed
- **Domain** with wildcard DNS configured (`*.yourdomain.com` → your server IP)
- **KiotProxy API keys** from [kiotproxy.com](https://kiotproxy.com)

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd kiot-prod
```

### 2. Configure Environment

```bash
# Copy example environment file
cp env.example .env

# Edit .env with your settings
nano .env
```

**Required settings in `.env`:**

```bash
# Your domain (IMPORTANT!)
DOMAIN=yourdomain.com

# Admin credentials (change these!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password-here

# Generate a secret key
SECRET_KEY=your-random-secret-key-here

# Your email for SSL certificates
SSL_EMAIL=admin@yourdomain.com
```

To generate a secure secret key:
```bash
openssl rand -hex 32
```

### 3. Configure DNS

Point these DNS records to your server IP:

```
A     yourdomain.com         → YOUR_SERVER_IP
A     *.yourdomain.com       → YOUR_SERVER_IP
```

**Example (using 1.2.3.4):**
```
A     example.com         → 1.2.3.4
A     *.example.com       → 1.2.3.4
```

This allows:
- `app.yourdomain.com` → Web UI
- `proxy1.yourdomain.com` → Proxy 1
- `proxy2.yourdomain.com` → Proxy 2
- etc.

### 4. Start Application

```bash
# Start all services
docker compose up -d
# Or for older Docker: docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps
```

### 5. Access Web UI

Open your browser and go to:
```
http://app.yourdomain.com
```

**Default login:**
- Username: `admin` (or what you set in `.env`)
- Password: `changeme123` (or what you set in `.env`)

**⚠️ IMPORTANT:** Change the default password immediately after first login!

## Usage Guide

### Adding a Proxy

1. Click **"➕ Add Proxy"** button
2. Enter:
   - **Proxy Name**: Friendly name (e.g., "My Proxy 1")
   - **KiotProxy API Key**: Your key from kiotproxy.com
   - **Region**: Bắc (North), Trung (Central), Nam (South), or Random
3. Click **"Create Proxy"**
4. Copy the endpoint (e.g., `proxy1.yourdomain.com`)

### Using the Proxy

Configure your application to use the proxy endpoint:

**With cURL:**
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
Settings → Network → Manual Proxy Configuration
HTTP Proxy: proxy1.yourdomain.com
Port: 80
```

### Auto-Rotation Settings

Go to **Settings** page to configure:

**Option 1: Auto-rotate on expiration (Default: ON)**
- Automatically rotates proxies after ~30 minutes when they expire
- Each proxy rotates independently

**Option 2: Timed auto-rotation (Default: OFF)**
- Rotates ALL proxies at custom intervals (minimum 2 minutes)
- Good for frequent IP changes

### Manual Rotation

Click the **🔄 Rotate** button next to any proxy to get a new IP immediately.

## Management Commands

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f traefik
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart backend
```

### Stop Services

```bash
docker compose down
```

### Backup Data

```bash
# Backup data.json
docker compose exec backend cat /app/data/data.json > backup-$(date +%Y%m%d).json

# Or copy directly
cp data/data.json backup-$(date +%Y%m%d).json
```

### Restore Data

```bash
# Stop backend
docker compose stop backend

# Restore data
cp backup-20251113.json data/data.json

# Start backend
docker compose start backend
```

## Troubleshooting

### DNS Not Resolving

**Check DNS records:**
```bash
nslookup proxy1.yourdomain.com
nslookup app.yourdomain.com
```

**For local development, use `/etc/hosts`:**
```bash
# Linux/Mac: /etc/hosts
# Windows: C:\Windows\System32\drivers\etc\hosts

127.0.0.1  app.yourdomain.com
127.0.0.1  proxy1.yourdomain.com
127.0.0.1  proxy2.yourdomain.com
```

### Proxy Not Working

1. **Check if proxy is running:**
```bash
docker compose ps
docker compose logs backend | grep proxy1
```

2. **Test proxy directly:**
```bash
curl -x http://proxy1.yourdomain.com:80 https://ipinfo.io -v
```

3. **Check Traefik routing:**
```bash
# View Traefik dashboard
# Open: http://YOUR_SERVER_IP:8080

# Check dynamic config
docker compose exec backend cat /app/traefik/proxies.yml
```

4. **Restart the proxy:**
   - Click the **🔁 Restart** button in the UI
   - Or use API: `POST /api/proxies/{id}/restart`

### High Latency

1. **Check proxy status** in the UI (shows latency)
2. **Rotate to new proxy** by clicking 🔄
3. **Try different region** (Bắc/Trung/Nam)

### Cannot Login

**Reset admin password:**

1. Stop backend:
```bash
docker compose stop backend
```

2. Generate new password hash:
```python
import bcrypt
password = b"new-password"
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed.decode())
```

3. Edit `data/data.json` and replace password hash

4. Start backend:
```bash
docker compose start backend
```

## Configuration Reference

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DOMAIN` | Your domain name | `localhost` | ✅ |
| `ADMIN_USERNAME` | Admin username | `admin` | ✅ |
| `ADMIN_PASSWORD` | Admin password | `changeme123` | ✅ |
| `SECRET_KEY` | Application secret key | - | ✅ |
| `SSL_EMAIL` | Email for SSL certificates | - | ✅ |
| `KIOTPROXY_API_BASE` | KiotProxy API URL | `https://api.kiotproxy.com/api/v1` | ❌ |
| `PROXY_PORT_START` | Starting port for proxies | `9000` | ❌ |
| `PROXY_PORT_END` | Ending port for proxies | `9100` | ❌ |
| `HEALTH_CHECK_INTERVAL` | Health check interval (seconds) | `30` | ❌ |
| `AUTO_ROTATION_CHECK_INTERVAL` | Rotation check interval (seconds) | `30` | ❌ |
| `VITE_API_URL` | Frontend API base (leave as `/api` in prod) | `/api` | ❌ |

### Port Usage

| Port Range | Purpose |
|------------|---------|
| 80 | HTTP traffic (Traefik) |
| 443 | HTTPS traffic (Traefik) |
| 8080 | Traefik dashboard |
| 8000 | Backend API (internal) |
| 9000-9100 | Proxy handlers (internal) |

## Security Best Practices

1. **Change default credentials** immediately
2. **Use strong passwords** (16+ characters)
3. **Enable HTTPS** (configured automatically with Let's Encrypt)
4. **Restrict access** to Traefik dashboard (port 8080)
5. **Regular backups** of `data/data.json`
6. **Keep Docker images updated**
7. **Monitor logs** for suspicious activity

## Advanced Configuration

### Using Custom Ports

Edit `docker compose.yml`:

```yaml
backend:
  ports:
    - "9000-9200:9000-9200"  # Increase range
```

And `.env`:
```bash
PROXY_PORT_START=9000
PROXY_PORT_END=9200
```

### Enable HTTPS

HTTPS is automatically enabled via Let's Encrypt. Just make sure:

1. Your domain is publicly accessible
2. `SSL_EMAIL` is set in `.env`
3. Ports 80 and 443 are open

Traefik will automatically obtain and renew SSL certificates.

### Monitoring

**Traefik Dashboard:**
```
http://YOUR_SERVER_IP:8080
```

**Backend Health:**
```bash
curl http://app.yourdomain.com/api/health
```

**Check Proxies:**
```bash
curl -b "session_id=YOUR_SESSION" http://app.yourdomain.com/api/proxies
```

## API Documentation

### Authentication

**Login:**
```bash
curl -X POST http://app.yourdomain.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  -c cookies.txt
```

### Proxies

**List proxies:**
```bash
curl -b cookies.txt http://app.yourdomain.com/api/proxies
```

**Create proxy:**
```bash
curl -X POST -b cookies.txt http://app.yourdomain.com/api/proxies \
  -H "Content-Type: application/json" \
  -d '{
    "key_name": "My Proxy",
    "kiotproxy_key": "K6fa3db6...",
    "region": "random"
  }'
```

**Rotate proxy:**
```bash
curl -X POST -b cookies.txt http://app.yourdomain.com/api/proxies/1/rotate \
  -H "Content-Type: application/json" \
  -d '{"region":"random"}'
```

**Delete proxy:**
```bash
curl -X DELETE -b cookies.txt http://app.yourdomain.com/api/proxies/1
```

### Settings

**Get settings:**
```bash
curl -b cookies.txt http://app.yourdomain.com/api/settings
```

**Update settings:**
```bash
curl -X PUT -b cookies.txt http://app.yourdomain.com/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "auto_rotate_on_expiration": true,
    "auto_rotate_interval_enabled": true,
    "auto_rotate_interval_minutes": 5
  }'
```

## Development

### Local Development

1. **Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m app.main
```

2. **Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Project Structure

```
kiot-prod/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── database.py       # JSON database operations
│   │   ├── models.py         # Pydantic models
│   │   ├── kiotproxy.py      # KiotProxy API client
│   │   ├── proxy_handler.py  # HTTP proxy servers
│   │   ├── traefik_config.py # Traefik config generator
│   │   └── worker.py         # Background workers
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main React component
│   │   ├── types.ts          # TypeScript types
│   │   └── api.ts            # API client
│   ├── package.json
│   └── Dockerfile
├── data/                     # Persistent data (created automatically)
│   └── data.json
├── traefik/                  # Traefik config (created automatically)
│   └── proxies.yml
├── docker compose.yml
├── env.example
└── README.md
```

## FAQ

**Q: Can I use this without a domain?**  
A: You can use it locally with IP addresses, but you won't have the nice subdomains. You'd need to use different ports for each proxy.

**Q: How many proxies can I have?**  
A: Up to 100 by default (ports 9000-9100). You can increase this by changing the port range.

**Q: Does this work with IPv6?**  
A: Currently only IPv4 is supported.

**Q: Can I use this on Windows/Mac?**  
A: Yes! Docker works on all platforms. The setup is the same.

**Q: What happens if KiotProxy is down?**  
A: Your proxy endpoints will stop working, but the manager will keep running. Proxies will show "error" status.

**Q: Can I have multiple users?**  
A: Currently only one admin user is supported. Multi-user support could be added in the future.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

MIT License - feel free to use this for any purpose.

## Support

For issues related to:
- **This application**: Open an issue on GitHub
- **KiotProxy service**: Contact [kiotproxy.com](https://kiotproxy.com)
- **Docker/Traefik**: Check their official documentation

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://reactjs.org/)
- [Traefik](https://traefik.io/)
- [proxy.py](https://github.com/abhinavsingh/proxy.py)
- [KiotProxy](https://kiotproxy.com/)

---

**Made with ❤️ for easy proxy management**

*Version 1.0.0 - November 2025*

