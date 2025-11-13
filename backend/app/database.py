import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import bcrypt
from app.models import User, ProxyKey, LogEntry, Settings

DATA_FILE = "/app/data/data.json"


def init_data_file():
    """Initialize data.json if it doesn't exist"""
    if not os.path.exists(DATA_FILE):
        # Get admin credentials from environment
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "changeme123")
        
        # Hash the password
        password_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt()).decode()
        
        initial_data = {
            "settings": {
                "auto_rotate_on_expiration": True,
                "auto_rotate_interval_enabled": False,
                "auto_rotate_interval_minutes": 10
            },
            "users": [
                {
                    "id": 1,
                    "username": admin_username,
                    "password": password_hash,
                    "session_id": None,
                    "session_expires": None
                }
            ],
            "proxy_keys": [],
            "logs": []
        }
        
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, 'w') as f:
            json.dump(initial_data, f, indent=2)


def load_data() -> Dict:
    """Load data from JSON file"""
    init_data_file()
    with open(DATA_FILE, 'r') as f:
        return json.load(f)


def save_data(data: Dict):
    """Save data to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# Settings operations

def get_settings() -> Settings:
    """Get application settings"""
    data = load_data()
    return Settings(**data.get("settings", {}))


def update_settings(settings: Settings) -> Settings:
    """Update application settings"""
    data = load_data()
    data["settings"] = settings.dict()
    save_data(data)
    return settings


# User operations

def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username"""
    data = load_data()
    for user_data in data["users"]:
        if user_data["username"] == username:
            return User(**user_data)
    return None


def get_user_by_session(session_id: str) -> Optional[User]:
    """Get user by session ID"""
    data = load_data()
    for user_data in data["users"]:
        if user_data.get("session_id") == session_id:
            # Check if session is expired
            if user_data.get("session_expires"):
                expires = datetime.fromisoformat(user_data["session_expires"])
                if datetime.now() > expires:
                    return None
            return User(**user_data)
    return None


def update_user_session(user_id: int, session_id: str, expires: datetime):
    """Update user session"""
    data = load_data()
    for user in data["users"]:
        if user["id"] == user_id:
            user["session_id"] = session_id
            user["session_expires"] = expires.isoformat()
            break
    save_data(data)


def clear_user_session(session_id: str):
    """Clear user session"""
    data = load_data()
    for user in data["users"]:
        if user.get("session_id") == session_id:
            user["session_id"] = None
            user["session_expires"] = None
            break
    save_data(data)


# Proxy operations

def get_all_proxies(user_id: int) -> List[ProxyKey]:
    """Get all proxies for a user"""
    data = load_data()
    proxies = []
    for proxy_data in data["proxy_keys"]:
        if proxy_data["user_id"] == user_id:
            proxies.append(ProxyKey(**proxy_data))
    return proxies


def get_active_proxies() -> List[ProxyKey]:
    """Get all active proxies"""
    data = load_data()
    proxies = []
    for proxy_data in data["proxy_keys"]:
        if proxy_data.get("is_active", True):
            proxies.append(ProxyKey(**proxy_data))
    return proxies


def get_proxy_by_id(proxy_id: int) -> Optional[ProxyKey]:
    """Get proxy by ID"""
    data = load_data()
    for proxy_data in data["proxy_keys"]:
        if proxy_data["id"] == proxy_id:
            return ProxyKey(**proxy_data)
    return None


def add_proxy(proxy: ProxyKey) -> ProxyKey:
    """Add new proxy"""
    data = load_data()
    data["proxy_keys"].append(proxy.dict())
    save_data(data)
    return proxy


def update_proxy(proxy: ProxyKey):
    """Update proxy"""
    data = load_data()
    for i, p in enumerate(data["proxy_keys"]):
        if p["id"] == proxy.id:
            data["proxy_keys"][i] = proxy.dict()
            break
    save_data(data)


def delete_proxy(proxy_id: int):
    """Delete proxy"""
    data = load_data()
    data["proxy_keys"] = [p for p in data["proxy_keys"] if p["id"] != proxy_id]
    save_data(data)


def get_next_proxy_id() -> int:
    """Get next available proxy ID"""
    data = load_data()
    if not data["proxy_keys"]:
        return 1
    return max(p["id"] for p in data["proxy_keys"]) + 1


def get_next_subdomain() -> str:
    """Get next available subdomain"""
    data = load_data()
    existing_subdomains = [p["subdomain"] for p in data["proxy_keys"]]
    for i in range(1, 1000):
        subdomain = f"proxy{i}"
        if subdomain not in existing_subdomains:
            return subdomain
    raise Exception("No available subdomains")


def get_next_port() -> int:
    """Get next available port"""
    data = load_data()
    port_start = int(os.getenv("PROXY_PORT_START", "9000"))
    used_ports = [p["port"] for p in data["proxy_keys"]]
    for port in range(port_start, port_start + 100):
        if port not in used_ports:
            return port
    raise Exception("No available ports")


# Log operations

def add_log(proxy_id: int, action: str, status: str, region: Optional[str] = None, details: Optional[str] = None):
    """Add log entry"""
    data = load_data()
    log_id = len(data["logs"]) + 1
    log = LogEntry(
        id=log_id,
        proxy_id=proxy_id,
        action=action,
        region=region,
        status=status,
        details=details,
        timestamp=datetime.now().isoformat()
    )
    data["logs"].append(log.dict())
    save_data(data)


def get_logs(proxy_id: Optional[int] = None, limit: int = 50) -> List[LogEntry]:
    """Get logs"""
    data = load_data()
    logs = data["logs"]
    
    if proxy_id is not None:
        logs = [l for l in logs if l["proxy_id"] == proxy_id]
    
    # Sort by timestamp descending
    logs = sorted(logs, key=lambda x: x["timestamp"], reverse=True)
    
    # Limit results
    logs = logs[:limit]
    
    return [LogEntry(**log) for log in logs]

