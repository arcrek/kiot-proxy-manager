# KiotProxy Manager - Simplified Implementation Plan

## Project Overview
A simple proxy manager that assigns each KiotProxy API key a constant public endpoint (e.g., `proxy1.domain.com`, `proxy2.domain.com`) that automatically forwards HTTP/HTTPS traffic through the KiotProxy service.

---

## Core Concept

```
User adds KiotProxy key → System assigns subdomain (proxy1.domain.com) 
→ User connects to proxy1.domain.com:80 
→ Traffic forwards through KiotProxy automatically
→ When proxy rotates, subdomain stays the same
```

### Example
```
Key 1: K6fa3db6...4a77ce → proxy1.domain.com → 171.243.255.207:31194
Key 2: K036684f...89d8b0 → proxy2.domain.com → 116.97.68.237:18173
Key 3: K1abfba7...920f35 → proxy3.domain.com → 27.73.175.36:26271

When Key 1 rotates → proxy1.domain.com still works, just routes through new IP
```

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (simple JSON file storage)
- **Proxy**: `proxy.py` or `mitmproxy` for HTTP forwarding
- **Authentication**: Simple session-based auth

### Frontend
- **Framework**: React + TypeScript
- **UI Library**: Tailwind CSS + shadcn/ui
- **HTTP Client**: Axios

### Infrastructure
- **Reverse Proxy**: Traefik with wildcard domain routing
- **Container**: Docker + Docker Compose
- **Domain**: Requires wildcard DNS (*.domain.com)

---

## Simplified Database (SQLite + JSON)

### Single JSON File: `data.json`
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
      "password": "hashed_password"
    }
  ],
  "proxy_keys": [
    {
      "id": 1,
      "user_id": 1,
      "key_name": "My Proxy 1",
      "kiotproxy_key": "K6fa3db6...4a77ce",
      "subdomain": "proxy1",
      "region": "random",
      "is_active": true,
      "remote_http": "171.243.255.207:31194",
      "remote_ip": "171.243.255.207",
      "location": "Bình Thuận",
      "status": "active",
      "latency_ms": 539,
      "expiration_at": "2025-11-13T12:00:00Z",
      "ttl": 1200,
      "ttc": 847,
      "last_check_at": "2025-11-13T10:30:00Z",
      "last_rotated_at": "2025-11-13T09:00:00Z",
      "created_at": "2025-11-13T09:00:00Z"
    }
  ],
  "logs": [
    {
      "id": 1,
      "proxy_id": 1,
      "action": "new",
      "region": "random",
      "status": "success",
      "timestamp": "2025-11-13T09:00:00Z"
    }
  ]
}
```

### Data Structure
- **settings**: Global application settings
  - `auto_rotate_on_expiration`: Auto-rotate when proxy expires (after 30 mins)
  - `auto_rotate_interval_enabled`: Enable timed auto-rotation
  - `auto_rotate_interval_minutes`: Interval in minutes (min: 2, applies to all keys)
- **users**: List of user objects (username, password)
- **proxy_keys**: List of proxy configurations (includes `last_rotated_at` for interval tracking)
- **logs**: Operation history

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                    Internet/Users                      │
└───────────────────────┬────────────────────────────────┘
                        │
        Uses: proxy1.domain.com as HTTP proxy
                        │
┌───────────────────────▼────────────────────────────────┐
│                    Traefik                             │
│  Routes based on Host header:                          │
│  - app.domain.com → Frontend                           │
│  - proxy1.domain.com → Proxy Handler #1                │
│  - proxy2.domain.com → Proxy Handler #2                │
│  - proxy3.domain.com → Proxy Handler #3                │
└───────────────────────┬────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────┐
│                  Backend Service                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  FastAPI App                                     │  │
│  │  - Web UI API                                    │  │
│  │  - Auth                                          │  │
│  │  - Key Management                                │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Proxy Handlers (HTTP Proxy Servers)            │  │
│  │  Each runs on different internal port           │  │
│  │                                                  │  │
│  │  Proxy1: Port 9001 → forwards via KP key 1      │  │
│  │  Proxy2: Port 9002 → forwards via KP key 2      │  │
│  │  Proxy3: Port 9003 → forwards via KP key 3      │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Background Worker (Health Check + Auto-rotate) │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  data.json (all data stored here)                     │
└───────────────────────┬────────────────────────────────┘
                        │
              Calls KiotProxy API
                        │
┌───────────────────────▼────────────────────────────────┐
│              KiotProxy API                             │
│  api.kiotproxy.com                                     │
└────────────────────────────────────────────────────────┘
```

---

## API Endpoints (Simplified)

### Authentication
```
POST /api/auth/login
Body: { "username": "admin", "password": "pass123" }
Returns: { "session_id": "..." }

POST /api/auth/logout
Headers: Cookie: session_id=...
```

### Proxy Management
```
GET /api/proxies
Returns: List of all proxy keys with status

POST /api/proxies
Body: {
  "key_name": "My Proxy",
  "kiotproxy_key": "K6fa3db6...",
  "region": "random"
}
Returns: {
  "id": 1,
  "subdomain": "proxy1",
  "endpoint": "proxy1.domain.com",
  "status": "active"
}

PUT /api/proxies/{id}
Body: { "key_name": "Updated Name", "region": "bac" }

DELETE /api/proxies/{id}

POST /api/proxies/{id}/rotate
Body: { "region": "random" }
Returns: { "new_ip": "...", "location": "..." }

POST /api/proxies/{id}/restart
```

### Logs
```
GET /api/logs?proxy_id={id}
```

### Settings
```
GET /api/settings
Returns: {
  "auto_rotate_on_expiration": true,
  "auto_rotate_interval_enabled": false,
  "auto_rotate_interval_minutes": 10
}

PUT /api/settings
Body: {
  "auto_rotate_on_expiration": true,
  "auto_rotate_interval_enabled": true,
  "auto_rotate_interval_minutes": 5
}
Returns: { "success": true, "settings": {...} }
```

---

## Frontend UI (Matching Your Image)

### Main Dashboard - Table Layout

| # | Key | KP Proxy | IP | Public Endpoint | Status | Actions |
|---|-----|----------|----|--------------------|--------|---------|
| 1 | K6fa3db6 [Edit] | HTTP: 171.243.255.207:31194 | 171.243.255.207 Bình Thuận | **proxy1.domain.com** | ✅ 539ms | 🔄 🖥️ 🔁 ⚙️ 🗑️ |
| 2 | K036684f [Edit] | HTTP: 116.97.68.237:18173 | 116.97.68.237 Thanh Hóa | **proxy2.domain.com** | ✅ 847ms | 🔄 🖥️ 🔁 ⚙️ 🗑️ |

### Features
- **Add Proxy Button**: Opens dialog to add new KiotProxy key
- **Actions**: 
  - 🔄 Rotate: Get new proxy from KiotProxy
  - 🖥️ Details: View full info
  - 🔁 Restart: Restart proxy handler
  - ⚙️ Settings: Change region preference
  - 🗑️ Delete: Remove proxy

### Settings Page

**Global Auto-Rotation Settings** (applies to all active keys)

```
┌────────────────────────────────────────────────────┐
│  Auto-Rotation Settings                            │
├────────────────────────────────────────────────────┤
│                                                    │
│  ☑️ Auto-rotate on expiration                      │
│     Automatically rotate proxies after 30 minutes  │
│     (when KiotProxy proxy expires)                 │
│                                                    │
│  ☐ Timed auto-rotation                             │
│     Rotate all proxies at regular intervals        │
│                                                    │
│     Interval: [____10____] minutes (min: 2)       │
│                                                    │
│  [Save Settings]                                   │
└────────────────────────────────────────────────────┘
```

**How it works:**
1. **Option 1: Auto-rotate on expiration** (Default: ON)
   - Monitors `expiration_at` timestamp
   - When proxy expires (~30 mins), automatically rotates
   - Uses same region preference for each key

2. **Option 2: Timed auto-rotation** (Default: OFF)
   - Rotates ALL active keys every X minutes
   - User sets interval (minimum 2 minutes)
   - Overrides expiration-based rotation if enabled
   - Useful for frequent IP changes

---

## Implementation Phases

### Phase 1: Project Setup (Day 1)
- [ ] Initialize FastAPI project
- [ ] Create `data.json` structure
- [ ] Set up Docker Compose with Traefik
- [ ] Configure wildcard domain routing

### Phase 2: Backend Core (Days 2-4)
- [ ] Simple JSON file read/write functions
- [ ] User authentication (session-based)
- [ ] KiotProxy API client
- [ ] Proxy key CRUD operations
- [ ] HTTP proxy handler implementation

### Phase 3: Proxy Forwarding (Days 5-7)
- [ ] Create HTTP proxy server per key
- [ ] Dynamic subdomain allocation (proxy1, proxy2, etc.)
- [ ] Traefik dynamic configuration
- [ ] Proxy rotation logic
- [ ] Health check system

### Phase 4: Frontend (Days 8-11)
- [ ] React setup with TypeScript
- [ ] Login page
- [ ] Main dashboard table
- [ ] Add/Edit proxy dialogs
- [ ] Settings page with auto-rotation options
- [ ] Real-time status updates
- [ ] Copy endpoint button

### Phase 5: Polish & Deploy (Days 12-14)
- [ ] Background worker for health checks
- [ ] Auto-rotation on expiration (30 mins)
- [ ] Auto-rotation on interval (user-defined)
- [ ] Logging system
- [ ] Error handling
- [ ] Testing
- [ ] Documentation
- [ ] Production deployment

**Total: 14 days**

---

## Docker Compose Configuration

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.file.directory=/etc/traefik/dynamic"
      - "--providers.file.watch=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@domain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./traefik/dynamic:/etc/traefik/dynamic
      - ./letsencrypt:/letsencrypt
    networks:
      - proxy-net

  backend:
    build: ./backend
    volumes:
      - ./data:/app/data  # Mount data.json
      - ./traefik/dynamic:/app/traefik  # Write dynamic config
    environment:
      - DOMAIN=domain.com
      - KIOTPROXY_API=https://api.kiotproxy.com/api/v1
    labels:
      - "traefik.enable=true"
      # Main API
      - "traefik.http.routers.api.rule=Host(`app.${DOMAIN}`) && PathPrefix(`/api`)"
      - "traefik.http.services.api.loadbalancer.server.port=8000"
    networks:
      - proxy-net
    ports:
      - "9000-9100:9000-9100"  # Range for proxy handlers

  frontend:
    build: ./frontend
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`app.${DOMAIN}`)"
      - "traefik.http.services.frontend.loadbalancer.server.port=80"
    networks:
      - proxy-net

networks:
  proxy-net:
    driver: bridge
```

---

## Traefik Dynamic Configuration

Backend generates this file dynamically when proxy is added:

**traefik/dynamic/proxies.yml**
```yaml
http:
  routers:
    proxy1:
      rule: "Host(`proxy1.domain.com`)"
      service: proxy1
      entryPoints:
        - web
    proxy2:
      rule: "Host(`proxy2.domain.com`)"
      service: proxy2
      entryPoints:
        - web
    proxy3:
      rule: "Host(`proxy3.domain.com`)"
      service: proxy3
      entryPoints:
        - web

  services:
    proxy1:
      loadBalancer:
        servers:
          - url: "http://backend:9001"
    proxy2:
      loadBalancer:
        servers:
          - url: "http://backend:9002"
    proxy3:
      loadBalancer:
        servers:
          - url: "http://backend:9003"
```

---

## Backend Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app
│   ├── auth.py                 # Simple auth
│   ├── database.py             # JSON file operations
│   ├── kiotproxy.py            # KiotProxy API client
│   ├── proxy_handler.py        # HTTP proxy server
│   ├── traefik_config.py       # Generate Traefik config
│   ├── worker.py               # Background tasks
│   └── models.py               # Pydantic models
├── data/
│   └── data.json               # All data
├── traefik/
│   └── dynamic/
│       └── proxies.yml         # Generated by backend
├── requirements.txt
└── Dockerfile
```

---

## Key Implementation Details

### 1. Subdomain Allocation
```python
def allocate_subdomain():
    """Find next available proxy subdomain"""
    existing = [p['subdomain'] for p in data['proxy_keys']]
    for i in range(1, 1000):
        subdomain = f"proxy{i}"
        if subdomain not in existing:
            return subdomain
    raise Exception("No available subdomains")
```

### 2. Creating Proxy Handler
```python
async def create_proxy_handler(proxy_id, kiotproxy_key, region):
    """Create HTTP proxy server for this key"""
    # 1. Get proxy from KiotProxy
    remote_proxy = await kiotproxy_client.get_new_proxy(kiotproxy_key, region)
    
    # 2. Allocate subdomain and port
    subdomain = allocate_subdomain()
    port = 9000 + proxy_id
    
    # 3. Start HTTP proxy server
    await start_http_proxy_server(
        port=port,
        remote_proxy=remote_proxy['http']
    )
    
    # 4. Update Traefik config
    update_traefik_config(subdomain, port)
    
    # 5. Save to data.json
    save_proxy_data({
        'id': proxy_id,
        'subdomain': subdomain,
        'remote_http': remote_proxy['http'],
        'remote_ip': remote_proxy['realIpAddress'],
        'location': remote_proxy['location'],
        'port': port
    })
    
    return f"{subdomain}.{DOMAIN}"
```

### 3. HTTP Proxy Handler
```python
from proxy import Proxy
import asyncio

class KiotProxyHandler:
    def __init__(self, port, remote_proxy):
        self.port = port
        self.remote_proxy = remote_proxy  # e.g., "171.243.255.207:31194"
        
    async def start(self):
        """Start HTTP proxy server"""
        with Proxy(
            hostname='0.0.0.0',
            port=self.port,
            upstream_proxy=f'http://{self.remote_proxy}'
        ):
            while True:
                await asyncio.sleep(1)
    
    def update_remote(self, new_proxy):
        """Hot-swap remote proxy"""
        self.remote_proxy = new_proxy
```

### 4. Rotation Logic
```python
async def rotate_proxy(proxy_id, region):
    """Rotate to new KiotProxy"""
    proxy = get_proxy_by_id(proxy_id)
    
    # Get new proxy from KiotProxy
    new_remote = await kiotproxy_client.get_new_proxy(
        proxy['kiotproxy_key'], 
        region
    )
    
    # Update proxy handler (no restart needed)
    proxy_handlers[proxy_id].update_remote(new_remote['http'])
    
    # Update data.json
    proxy['remote_http'] = new_remote['http']
    proxy['remote_ip'] = new_remote['realIpAddress']
    proxy['location'] = new_remote['location']
    proxy['expiration_at'] = new_remote['expirationAt']
    proxy['ttl'] = new_remote['ttl']
    proxy['ttc'] = new_remote['ttc']
    proxy['last_rotated_at'] = datetime.now().isoformat()
    save_data()
    
    log_action(proxy_id, 'rotate', 'success')
    
    return new_remote
```

### 5. Auto-Rotation Worker Logic
```python
async def auto_rotation_worker():
    """Background worker for automatic proxy rotation"""
    while True:
        try:
            settings = get_settings()
            
            # Option 1: Rotate on expiration (30 mins)
            if settings['auto_rotate_on_expiration']:
                await rotate_expired_proxies()
            
            # Option 2: Rotate on interval (user-defined)
            if settings['auto_rotate_interval_enabled']:
                interval_minutes = settings['auto_rotate_interval_minutes']
                await rotate_by_interval(interval_minutes)
            
            # Check every 30 seconds
            await asyncio.sleep(30)
            
        except Exception as e:
            log_error(f"Auto-rotation error: {e}")
            await asyncio.sleep(30)


async def rotate_expired_proxies():
    """Rotate proxies that have expired"""
    proxies = get_active_proxies()
    now = datetime.now()
    
    for proxy in proxies:
        expiration = datetime.fromisoformat(proxy['expiration_at'])
        
        # If expired or about to expire in 1 minute
        if now >= expiration - timedelta(minutes=1):
            try:
                await rotate_proxy(proxy['id'], proxy['region'])
                log_info(f"Auto-rotated proxy {proxy['id']} (expiration)")
            except Exception as e:
                log_error(f"Failed to rotate proxy {proxy['id']}: {e}")


async def rotate_by_interval(interval_minutes):
    """Rotate proxies based on time interval"""
    proxies = get_active_proxies()
    now = datetime.now()
    
    for proxy in proxies:
        last_rotated = datetime.fromisoformat(proxy['last_rotated_at'])
        minutes_since_rotation = (now - last_rotated).total_seconds() / 60
        
        # If interval has passed
        if minutes_since_rotation >= interval_minutes:
            try:
                await rotate_proxy(proxy['id'], proxy['region'])
                log_info(f"Auto-rotated proxy {proxy['id']} (interval: {interval_minutes}min)")
            except Exception as e:
                log_error(f"Failed to rotate proxy {proxy['id']}: {e}")
```

---

## DNS Configuration

### Wildcard DNS Setup
Point these records to your server IP:

```
A     domain.com                  →  YOUR_SERVER_IP
A     *.domain.com                →  YOUR_SERVER_IP
```

This allows:
- `app.domain.com` → Frontend
- `proxy1.domain.com` → Proxy 1
- `proxy2.domain.com` → Proxy 2
- `proxy3.domain.com` → Proxy 3
- etc.

---

## Using the Proxies

### With Browser
```
Settings → Network → Manual Proxy Configuration
HTTP Proxy: proxy1.domain.com
Port: 80
```

### With cURL
```bash
curl -x http://proxy1.domain.com:80 https://ipinfo.io
```

### With Python
```python
import requests

proxies = {
    'http': 'http://proxy1.domain.com:80',
    'https': 'http://proxy1.domain.com:80'
}

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
}).then(res => console.log(res.data));
```

---

## Environment Variables

### Backend (.env)
```bash
# Domain
DOMAIN=domain.com

# KiotProxy API
KIOTPROXY_API_BASE=https://api.kiotproxy.com/api/v1

# Admin credentials (initial)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123

# Proxy ports
PROXY_PORT_START=9000
PROXY_PORT_END=9100

# Health check
HEALTH_CHECK_INTERVAL=30
```

### Frontend (.env)
```bash
REACT_APP_API_URL=https://app.domain.com/api
```

---

## Data Flow Example

### Adding New Proxy Key

```
1. User clicks "Add Proxy"
   ↓
2. User enters:
   - Key Name: "My Proxy"
   - KiotProxy Key: "K6fa3db6..."
   - Region: "random"
   ↓
3. Backend:
   - Calls KiotProxy API /proxies/new
   - Allocates subdomain: "proxy1"
   - Starts HTTP proxy server on port 9001
   - Updates Traefik config
   - Saves to data.json
   ↓
4. User receives: "proxy1.domain.com"
   ↓
5. User configures app to use: proxy1.domain.com:80
   ↓
6. Traffic flows:
   User App → proxy1.domain.com → Traefik → Backend:9001 → KiotProxy → Internet
```

### Rotating Proxy

```
1. User clicks 🔄 Rotate
   ↓
2. Backend:
   - Calls KiotProxy /proxies/new
   - Gets new IP: 116.97.68.237:18173
   - Updates proxy handler (no restart)
   - Updates data.json
   ↓
3. UI updates showing new IP
   ↓
4. Subdomain (proxy1.domain.com) unchanged
5. User's app continues working, now through new IP
```

---

## Project Structure

```
kiot-prod/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── kiotproxy.py
│   │   ├── proxy_handler.py
│   │   ├── traefik_config.py
│   │   ├── worker.py
│   │   └── models.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ProxyTable.tsx
│   │   │   ├── AddProxyDialog.tsx
│   │   │   └── LoginForm.tsx
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── data/
│   └── data.json
├── traefik/
│   └── dynamic/
│       └── proxies.yml (generated)
├── docker-compose.yml
├── .env
└── README.md
```

---

## Success Criteria

✅ Users can login with username/password
✅ Users can add KiotProxy API keys
✅ Each key gets a unique subdomain (proxy1.domain.com, proxy2.domain.com)
✅ Subdomains work as HTTP proxies
✅ Traffic forwards through KiotProxy
✅ Proxy rotation works without changing subdomain
✅ UI shows status and latency
✅ Health monitoring works
✅ Simple to deploy and manage

---

## Dependencies

### Backend (requirements.txt)
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.2
httpx==0.25.2
proxy.py==2.4.3
pyyaml==6.0.1
python-multipart==0.0.6
bcrypt==4.1.1
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.2",
    "tailwindcss": "^3.3.0",
    "@shadcn/ui": "latest"
  }
}
```

---

*Document Version: 2.0 (Simplified)*
*Last Updated: November 13, 2025*
*Architecture: Public Subdomain per Key*
