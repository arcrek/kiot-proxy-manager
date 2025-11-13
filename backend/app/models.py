from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# Request/Response Models

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    session_id: str
    username: str


class AddProxyRequest(BaseModel):
    key_name: str
    kiotproxy_key: str
    region: str = "random"


class BulkImportRequest(BaseModel):
    kiotproxy_keys: str  # Newline-separated keys
    region: str = "random"


class ProxyResponse(BaseModel):
    id: int
    key_name: str
    subdomain: str
    endpoint: str
    remote_http: Optional[str] = None
    remote_ip: Optional[str] = None
    location: Optional[str] = None
    status: str
    latency_ms: Optional[int] = None
    expiration_at: Optional[str] = None
    ttl: Optional[int] = None
    ttc: Optional[int] = None
    last_check_at: Optional[str] = None
    last_rotated_at: Optional[str] = None
    created_at: str


class RotateProxyRequest(BaseModel):
    region: str = "random"


class UpdateSettingsRequest(BaseModel):
    auto_rotate_on_expiration: Optional[bool] = None
    auto_rotate_interval_enabled: Optional[bool] = None
    auto_rotate_interval_minutes: Optional[int] = None


class SettingsResponse(BaseModel):
    auto_rotate_on_expiration: bool
    auto_rotate_interval_enabled: bool
    auto_rotate_interval_minutes: int


# Data Models (internal)

class User(BaseModel):
    id: int
    username: str
    password: str
    session_id: Optional[str] = None
    session_expires: Optional[str] = None


class ProxyKey(BaseModel):
    id: int
    user_id: int
    key_name: str
    kiotproxy_key: str
    subdomain: str
    port: int
    region: str = "random"
    is_active: bool = True
    remote_http: Optional[str] = None
    remote_ip: Optional[str] = None
    location: Optional[str] = None
    status: str = "pending"
    latency_ms: Optional[int] = None
    last_check_at: Optional[str] = None
    expiration_at: Optional[str] = None
    ttl: Optional[int] = None
    ttc: Optional[int] = None
    last_rotated_at: Optional[str] = None
    created_at: str


class LogEntry(BaseModel):
    id: int
    proxy_id: int
    action: str
    region: Optional[str] = None
    status: str
    details: Optional[str] = None
    timestamp: str


class Settings(BaseModel):
    auto_rotate_on_expiration: bool = True
    auto_rotate_interval_enabled: bool = False
    auto_rotate_interval_minutes: int = 10

