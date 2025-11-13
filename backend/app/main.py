import os
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional
import uuid
import bcrypt

from fastapi import FastAPI, HTTPException, Cookie, Response, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    LoginRequest, LoginResponse, AddProxyRequest, BulkImportRequest, ProxyResponse,
    RotateProxyRequest, UpdateSettingsRequest, SettingsResponse
)
from app.database import (
    init_data_file, get_user_by_username, get_user_by_session,
    update_user_session, clear_user_session,
    get_all_proxies, get_active_proxies, get_proxy_by_id,
    add_proxy, update_proxy, delete_proxy,
    get_next_proxy_id, get_next_subdomain, get_next_port,
    get_settings, update_settings, add_log, get_logs
)
from app.kiotproxy import kiotproxy_client
from app.proxy_handler import start_proxy_handler, stop_proxy_handler, restart_proxy_handler, cleanup_all_proxies
from app.traefik_config import generate_traefik_config, remove_proxy_from_traefik
from app.worker import health_check_worker, auto_rotation_worker, auto_update_worker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting KiotProxy Manager...")
    
    # Initialize data file
    init_data_file()
    
    # Restart all active proxies
    await restart_all_proxies()
    
    # Start background workers
    health_task = asyncio.create_task(health_check_worker())
    rotation_task = asyncio.create_task(auto_rotation_worker())
    update_task = asyncio.create_task(auto_update_worker())
    
    logger.info("KiotProxy Manager started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down KiotProxy Manager...")
    
    # Cancel background tasks
    health_task.cancel()
    rotation_task.cancel()
    update_task.cancel()
    
    # Cleanup all proxy servers
    await cleanup_all_proxies()
    
    logger.info("KiotProxy Manager shut down complete")


async def restart_all_proxies():
    """Restart all active proxies on startup"""
    try:
        # First, clean up any stale proxy server references
        from app.proxy_handler import proxy_servers
        proxy_servers.clear()
        logger.info("Cleared stale proxy server references")
        
        proxies = get_active_proxies()
        logger.info(f"Restarting {len(proxies)} active proxies...")
        
        success_count = 0
        for proxy in proxies:
            try:
                if proxy.remote_http:
                    logger.info(f"Starting proxy {proxy.id} ({proxy.key_name}) on port {proxy.port}...")
                    await start_proxy_handler(proxy.id, proxy.port, proxy.remote_http)
                    proxy.status = "active"
                    update_proxy(proxy)
                    success_count += 1
                    logger.info(f"✓ Restarted proxy {proxy.id} on port {proxy.port}")
                else:
                    logger.warning(f"Proxy {proxy.id} has no remote_http, skipping")
                    proxy.status = "pending"
                    update_proxy(proxy)
            except Exception as e:
                logger.error(f"✗ Failed to restart proxy {proxy.id}: {e}")
                proxy.status = "error"
                update_proxy(proxy)
        
        logger.info(f"Successfully restarted {success_count}/{len(proxies)} proxies")
        
        # Regenerate Traefik config with only successfully started proxies
        active_proxies = [p for p in proxies if p.status == "active"]
        generate_traefik_config(active_proxies)
        logger.info("Traefik configuration updated")
        
    except Exception as e:
        logger.error(f"Error during proxy restart: {e}")


# Create FastAPI app
app = FastAPI(title="KiotProxy Manager", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication dependency
async def get_current_user(session_id: Optional[str] = Cookie(None)):
    """Verify user session"""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = get_user_by_session(session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user


# Routes

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """Login endpoint"""
    user = get_user_by_username(request.username)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Verify password
    if not bcrypt.checkpw(request.password.encode(), user.password.encode()):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    expires = datetime.now() + timedelta(days=7)
    
    # Update user session
    update_user_session(user.id, session_id, expires)
    
    # Set cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=7 * 24 * 60 * 60,  # 7 days
        samesite="lax"
    )
    
    return LoginResponse(session_id=session_id, username=user.username)


@app.post("/api/auth/logout")
async def logout(response: Response, session_id: Optional[str] = Cookie(None)):
    """Logout endpoint"""
    if session_id:
        clear_user_session(session_id)
    
    response.delete_cookie("session_id")
    return {"success": True}


@app.get("/api/auth/me")
async def get_current_user_info(user = Depends(get_current_user)):
    """Get current user info"""
    return {"username": user.username}


@app.get("/api/proxies", response_model=List[ProxyResponse])
async def list_proxies(user = Depends(get_current_user)):
    """List all proxies for current user"""
    proxies = get_all_proxies(user.id)
    domain = os.getenv("DOMAIN", "localhost")
    
    return [
        ProxyResponse(
            id=p.id,
            key_name=p.key_name,
            subdomain=p.subdomain,
            endpoint=f"{p.subdomain}.{domain}:{p.port}",
            remote_http=p.remote_http,
            remote_ip=p.remote_ip,
            location=p.location,
            status=p.status,
            latency_ms=p.latency_ms,
            expiration_at=p.expiration_at,
            ttl=p.ttl,
            ttc=p.ttc,
            last_check_at=p.last_check_at,
            last_rotated_at=p.last_rotated_at,
            created_at=p.created_at
        )
        for p in proxies
    ]


@app.post("/api/proxies", response_model=ProxyResponse)
async def create_proxy(request: AddProxyRequest, user = Depends(get_current_user)):
    """Create new proxy"""
    try:
        # Get proxy from KiotProxy API (use current proxy, not new)
        logger.info(f"Fetching proxy for key {request.kiotproxy_key[:8]}...")
        remote_data = await kiotproxy_client.get_current_proxy(request.kiotproxy_key)
        
        # Allocate resources
        proxy_id = get_next_proxy_id()
        subdomain = get_next_subdomain()
        port = get_next_port()
        domain = os.getenv("DOMAIN", "localhost")
        
        # Create proxy object
        from app.models import ProxyKey
        
        # Auto-generate key name from location
        location = remote_data.get("location", "Unknown")
        key_name = f"{location}-{proxy_id}"
        
        # Convert expiration timestamp (milliseconds) to ISO string
        expiration_timestamp = remote_data["expirationAt"] / 1000 if remote_data.get("expirationAt") else None
        expiration_iso = datetime.fromtimestamp(expiration_timestamp).isoformat() if expiration_timestamp else None
        
        proxy = ProxyKey(
            id=proxy_id,
            user_id=user.id,
            key_name=key_name,
            kiotproxy_key=request.kiotproxy_key,
            subdomain=subdomain,
            port=port,
            region=request.region,
            is_active=True,
            remote_http=remote_data["http"],
            remote_ip=remote_data["realIpAddress"],
            location=location,
            status="active",
            expiration_at=expiration_iso,
            ttl=remote_data["ttl"],
            ttc=remote_data["ttc"],
            last_rotated_at=datetime.now().isoformat(),
            created_at=datetime.now().isoformat()
        )
        
        # Save to database
        add_proxy(proxy)
        
        # Start proxy handler
        logger.info(f"Starting proxy handler for {subdomain} on port {port}")
        await start_proxy_handler(proxy_id, port, remote_data["http"])
        
        # Update Traefik config
        active_proxies = get_active_proxies()
        generate_traefik_config(active_proxies)
        
        # Add log
        add_log(proxy_id, "create", "success", request.region, f"Created proxy {subdomain}")
        
        logger.info(f"Successfully created proxy {proxy_id} at {subdomain}.{domain}:{port}")
        
        return ProxyResponse(
            id=proxy.id,
            key_name=proxy.key_name,
            subdomain=proxy.subdomain,
            endpoint=f"{subdomain}.{domain}:{port}",
            remote_http=proxy.remote_http,
            remote_ip=proxy.remote_ip,
            location=proxy.location,
            status=proxy.status,
            latency_ms=proxy.latency_ms,
            expiration_at=proxy.expiration_at,
            ttl=proxy.ttl,
            ttc=proxy.ttc,
            last_check_at=proxy.last_check_at,
            last_rotated_at=proxy.last_rotated_at,
            created_at=proxy.created_at
        )
        
    except Exception as e:
        logger.error(f"Failed to create proxy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxies/bulk-import")
async def bulk_import_proxies(request: BulkImportRequest, user = Depends(get_current_user)):
    """Bulk import proxies from newline-separated keys"""
    try:
        # Parse keys (split by newline, filter empty lines)
        keys = [k.strip() for k in request.kiotproxy_keys.split('\n') if k.strip()]
        
        if not keys:
            raise HTTPException(status_code=400, detail="No keys provided")
        
        if len(keys) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 keys per import")
        
        results = {
            "success": [],
            "failed": []
        }
        
        for idx, kiotproxy_key in enumerate(keys):
            try:
                # Get current proxy from KiotProxy API
                logger.info(f"Importing proxy {idx+1}/{len(keys)}: {kiotproxy_key[:8]}...")
                remote_data = await kiotproxy_client.get_current_proxy(kiotproxy_key)
                
                # Allocate resources
                proxy_id = get_next_proxy_id()
                subdomain = get_next_subdomain()
                port = get_next_port()
                domain = os.getenv("DOMAIN", "localhost")
                
                # Auto-generate key name from location
                location = remote_data.get("location", "Unknown")
                key_name = f"{location}-{proxy_id}"
                
                # Convert expiration timestamp
                expiration_timestamp = remote_data["expirationAt"] / 1000 if remote_data.get("expirationAt") else None
                expiration_iso = datetime.fromtimestamp(expiration_timestamp).isoformat() if expiration_timestamp else None
                
                # Create proxy object
                from app.models import ProxyKey
                proxy = ProxyKey(
                    id=proxy_id,
                    user_id=user.id,
                    key_name=key_name,
                    kiotproxy_key=kiotproxy_key,
                    subdomain=subdomain,
                    port=port,
                    region=request.region,
                    is_active=True,
                    remote_http=remote_data["http"],
                    remote_ip=remote_data["realIpAddress"],
                    location=location,
                    status="active",
                    expiration_at=expiration_iso,
                    ttl=remote_data["ttl"],
                    ttc=remote_data["ttc"],
                    last_rotated_at=datetime.now().isoformat(),
                    created_at=datetime.now().isoformat()
                )
                
                # Save to database
                add_proxy(proxy)
                
                # Start proxy handler
                await start_proxy_handler(proxy_id, port, remote_data["http"])
                
                # Add log
                add_log(proxy_id, "bulk_import", "success", request.region, f"Imported as {key_name}")
                
                results["success"].append({
                    "key": kiotproxy_key[:8] + "...",
                    "name": key_name,
                    "subdomain": f"{subdomain}.{domain}",
                    "ip": remote_data["realIpAddress"]
                })
                
                logger.info(f"Successfully imported proxy {proxy_id}: {key_name}")
                
            except Exception as e:
                logger.error(f"Failed to import key {kiotproxy_key[:8]}: {e}")
                results["failed"].append({
                    "key": kiotproxy_key[:8] + "...",
                    "error": str(e)
                })
        
        # Update Traefik config once after all imports
        active_proxies = get_active_proxies()
        generate_traefik_config(active_proxies)
        
        return {
            "total": len(keys),
            "success_count": len(results["success"]),
            "failed_count": len(results["failed"]),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxies/{proxy_id}/rotate", response_model=ProxyResponse)
async def rotate_proxy(proxy_id: int, request: RotateProxyRequest, user = Depends(get_current_user)):
    """Rotate proxy to new IP"""
    proxy = get_proxy_by_id(proxy_id)
    
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    
    if proxy.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Get new proxy from KiotProxy
        logger.info(f"Rotating proxy {proxy_id} to region {request.region}")
        new_remote = await kiotproxy_client.get_new_proxy(proxy.kiotproxy_key, request.region)
        
        # Update proxy handler
        await restart_proxy_handler(proxy_id, proxy.port, new_remote["http"])
        
        # Convert expiration timestamp (milliseconds) to ISO string
        expiration_timestamp = new_remote["expirationAt"] / 1000 if new_remote.get("expirationAt") else None
        expiration_iso = datetime.fromtimestamp(expiration_timestamp).isoformat() if expiration_timestamp else None
        
        # Update proxy data
        proxy.remote_http = new_remote["http"]
        proxy.remote_ip = new_remote["realIpAddress"]
        proxy.location = new_remote["location"]
        proxy.expiration_at = expiration_iso
        proxy.ttl = new_remote["ttl"]
        proxy.ttc = new_remote["ttc"]
        proxy.region = request.region
        proxy.last_rotated_at = datetime.now().isoformat()
        
        update_proxy(proxy)
        add_log(proxy_id, "rotate", "success", request.region, f"Rotated to {proxy.remote_ip}")
        
        logger.info(f"Successfully rotated proxy {proxy_id} to {proxy.remote_ip}")
        
        domain = os.getenv("DOMAIN", "localhost")
        return ProxyResponse(
            id=proxy.id,
            key_name=proxy.key_name,
            subdomain=proxy.subdomain,
            endpoint=f"{proxy.subdomain}.{domain}:{proxy.port}",
            remote_http=proxy.remote_http,
            remote_ip=proxy.remote_ip,
            location=proxy.location,
            status=proxy.status,
            latency_ms=proxy.latency_ms,
            expiration_at=proxy.expiration_at,
            ttl=proxy.ttl,
            ttc=proxy.ttc,
            last_check_at=proxy.last_check_at,
            last_rotated_at=proxy.last_rotated_at,
            created_at=proxy.created_at
        )
        
    except Exception as e:
        logger.error(f"Failed to rotate proxy {proxy_id}: {e}")
        add_log(proxy_id, "rotate", "failed", request.region, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxies/{proxy_id}/update", response_model=ProxyResponse)
async def update_proxy_info(proxy_id: int, user = Depends(get_current_user)):
    """Update proxy information from KiotProxy API"""
    proxy = get_proxy_by_id(proxy_id)
    
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    
    if proxy.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        logger.info(f"Updating proxy {proxy_id} info from KiotProxy API")
        
        # Get current proxy info from KiotProxy API
        current_data = await kiotproxy_client.get_current_proxy(proxy.kiotproxy_key)
        
        # Convert expiration timestamp
        expiration_timestamp = current_data["expirationAt"] / 1000 if current_data.get("expirationAt") else None
        expiration_iso = datetime.fromtimestamp(expiration_timestamp).isoformat() if expiration_timestamp else None
        
        # Update proxy data
        proxy.remote_http = current_data["http"]
        proxy.remote_ip = current_data["realIpAddress"]
        proxy.location = current_data["location"]
        proxy.expiration_at = expiration_iso
        proxy.ttl = current_data["ttl"]
        proxy.ttc = current_data["ttc"]
        proxy.status = "active"
        
        update_proxy(proxy)
        
        # Restart proxy handler with updated info
        await restart_proxy_handler(proxy_id, proxy.port, proxy.remote_http)
        
        add_log(proxy_id, "update", "success", None, f"Updated to {proxy.remote_ip}")
        logger.info(f"Successfully updated proxy {proxy_id}")
        
        domain = os.getenv("DOMAIN", "localhost")
        return ProxyResponse(
            id=proxy.id,
            key_name=proxy.key_name,
            subdomain=proxy.subdomain,
            endpoint=f"{proxy.subdomain}.{domain}:{proxy.port}",
            remote_http=proxy.remote_http,
            remote_ip=proxy.remote_ip,
            location=proxy.location,
            status=proxy.status,
            latency_ms=proxy.latency_ms,
            expiration_at=proxy.expiration_at,
            ttl=proxy.ttl,
            ttc=proxy.ttc,
            last_check_at=proxy.last_check_at,
            last_rotated_at=proxy.last_rotated_at,
            created_at=proxy.created_at
        )
        
    except Exception as e:
        logger.error(f"Failed to update proxy {proxy_id}: {e}")
        add_log(proxy_id, "update", "failed", None, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxies/{proxy_id}/check")
async def check_proxy_health(proxy_id: int, user = Depends(get_current_user)):
    """Manually trigger health check for a proxy"""
    proxy = get_proxy_by_id(proxy_id)
    
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    
    if proxy.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        logger.info(f"Checking health of proxy {proxy_id}")
        
        if not proxy.remote_http:
            raise Exception("Proxy has no remote_http configured")
        
        # Test raw TCP proxy by connecting to remote KiotProxy
        remote_parts = proxy.remote_http.split(':')
        remote_host = remote_parts[0]
        remote_port = int(remote_parts[1])
        start_time = datetime.now()
        
        try:
            # Try to establish TCP connection to remote KiotProxy
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(remote_host, remote_port),
                timeout=10.0
            )
            
            # Send a simple HTTP request through the proxy
            http_request = b"GET http://google.com/ HTTP/1.1\r\nHost: google.com\r\nConnection: close\r\n\r\n"
            writer.write(http_request)
            await writer.drain()
            
            # Read some response
            response_data = await asyncio.wait_for(reader.read(100), timeout=10.0)
            
            # Close connection
            writer.close()
            await writer.wait_closed()
            
            # Calculate latency
            latency = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Check if we got a response
            if response_data and b"HTTP" in response_data:
                proxy.status = "active"
                proxy.latency_ms = latency
                logger.info(f"Proxy {proxy_id} health check passed: {latency}ms")
            else:
                proxy.status = "error"
                proxy.latency_ms = None
                logger.warning(f"Proxy {proxy_id} got invalid response")
                
        except (asyncio.TimeoutError, OSError, ConnectionRefusedError) as check_error:
            proxy.status = "error"
            proxy.latency_ms = None
            logger.error(f"Proxy {proxy_id} health check failed: {check_error}")
        
        proxy.last_check_at = datetime.now().isoformat()
        update_proxy(proxy)
        
        add_log(proxy_id, "health_check", "success" if proxy.status == "active" else "failed", 
                None, f"Latency: {proxy.latency_ms}ms" if proxy.latency_ms else "Check failed")
        
        return {
            "success": True,
            "status": proxy.status,
            "latency_ms": proxy.latency_ms,
            "checked_at": proxy.last_check_at
        }
        
    except Exception as e:
        logger.error(f"Failed to check proxy {proxy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxies/check-all")
async def check_all_proxies(user = Depends(get_current_user)):
    """Check health of all proxies"""
    try:
        proxies = get_all_proxies(user.id)
        
        results = {
            "total": len(proxies),
            "checked": 0,
            "active": 0,
            "error": 0
        }
        
        for proxy in proxies:
            try:
                if not proxy.remote_http:
                    continue
                
                # Test TCP connection
                remote_parts = proxy.remote_http.split(':')
                remote_host = remote_parts[0]
                remote_port = int(remote_parts[1])
                start_time = datetime.now()
                
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(remote_host, remote_port),
                        timeout=5.0
                    )
                    
                    http_request = b"GET http://google.com/ HTTP/1.1\r\nHost: google.com\r\nConnection: close\r\n\r\n"
                    writer.write(http_request)
                    await writer.drain()
                    
                    response_data = await asyncio.wait_for(reader.read(100), timeout=5.0)
                    
                    writer.close()
                    
                    latency = int((datetime.now() - start_time).total_seconds() * 1000)
                    
                    if response_data and b"HTTP" in response_data:
                        proxy.status = "active"
                        proxy.latency_ms = latency
                        results["active"] += 1
                    else:
                        proxy.status = "error"
                        proxy.latency_ms = None
                        results["error"] += 1
                        
                except Exception:
                    proxy.status = "error"
                    proxy.latency_ms = None
                    results["error"] += 1
                
                proxy.last_check_at = datetime.now().isoformat()
                update_proxy(proxy)
                results["checked"] += 1
                
            except Exception as e:
                logger.error(f"Failed to check proxy {proxy.id}: {e}")
        
        logger.info(f"Bulk check completed: {results['active']} active, {results['error']} error")
        return results
        
    except Exception as e:
        logger.error(f"Bulk check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proxies/update-all")
async def update_all_proxies(user = Depends(get_current_user)):
    """Update all proxies from KiotProxy API"""
    try:
        proxies = get_all_proxies(user.id)
        
        results = {
            "total": len(proxies),
            "updated": 0,
            "failed": 0
        }
        
        for proxy in proxies:
            try:
                # Get current proxy info from KiotProxy API
                current_data = await kiotproxy_client.get_current_proxy(proxy.kiotproxy_key)
                
                # Convert expiration timestamp
                expiration_timestamp = current_data["expirationAt"] / 1000 if current_data.get("expirationAt") else None
                expiration_iso = datetime.fromtimestamp(expiration_timestamp).isoformat() if expiration_timestamp else None
                
                # Update proxy data
                proxy.remote_http = current_data["http"]
                proxy.remote_ip = current_data["realIpAddress"]
                proxy.location = current_data["location"]
                proxy.expiration_at = expiration_iso
                proxy.ttl = current_data["ttl"]
                proxy.ttc = current_data["ttc"]
                proxy.status = "active"
                
                update_proxy(proxy)
                
                # Restart proxy handler with updated info
                await restart_proxy_handler(proxy.id, proxy.port, proxy.remote_http)
                
                add_log(proxy.id, "bulk_update", "success", None, f"Updated to {proxy.remote_ip}")
                results["updated"] += 1
                
            except Exception as e:
                logger.error(f"Failed to update proxy {proxy.id}: {e}")
                add_log(proxy.id, "bulk_update", "failed", None, str(e))
                results["failed"] += 1
        
        logger.info(f"Bulk update completed: {results['updated']} updated, {results['failed']} failed")
        return results
        
    except Exception as e:
        logger.error(f"Bulk update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/proxies/{proxy_id}/test")
async def test_proxy_connection(proxy_id: int, user = Depends(get_current_user)):
    """Test proxy connection with detailed diagnostics"""
    proxy = get_proxy_by_id(proxy_id)
    
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    
    if proxy.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    diagnostics = {
        "proxy_id": proxy_id,
        "remote_proxy": proxy.remote_http,
        "port": proxy.port,
        "tests": []
    }
    
    # Test 1: Raw TCP connection to remote KiotProxy
    test1 = {"name": "Remote KiotProxy TCP Connection", "status": "pending"}
    try:
        remote_parts = proxy.remote_http.split(':')
        remote_host = remote_parts[0]
        remote_port = int(remote_parts[1])
        
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(remote_host, remote_port),
            timeout=5.0
        )
        
        # Send HTTP request
        http_request = b"GET http://httpbin.org/ip HTTP/1.1\r\nHost: httpbin.org\r\nConnection: close\r\n\r\n"
        writer.write(http_request)
        await writer.drain()
        
        # Read response
        response_data = await asyncio.wait_for(reader.read(500), timeout=5.0)
        
        writer.close()
        await writer.wait_closed()
        
        test1["status"] = "success"
        test1["details"] = f"Connected successfully. Response: {response_data[:200].decode('utf-8', errors='ignore')}"
    except Exception as e:
        test1["status"] = "failed"
        test1["error"] = str(e)
    diagnostics["tests"].append(test1)
    
    return diagnostics


@app.delete("/api/proxies/{proxy_id}")
async def delete_proxy_endpoint(proxy_id: int, user = Depends(get_current_user)):
    """Delete proxy"""
    proxy = get_proxy_by_id(proxy_id)
    
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    
    if proxy.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        logger.info(f"Deleting proxy {proxy_id}")
        
        # Stop proxy handler
        await stop_proxy_handler(proxy_id)
        
        # Remove from database
        delete_proxy(proxy_id)
        
        # Update Traefik config
        active_proxies = get_active_proxies()
        remove_proxy_from_traefik(proxy.subdomain, active_proxies)
        
        add_log(proxy_id, "delete", "success")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to delete proxy {proxy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings", response_model=SettingsResponse)
async def get_settings_endpoint(user = Depends(get_current_user)):
    """Get application settings"""
    settings = get_settings()
    return SettingsResponse(**settings.dict())


@app.put("/api/settings", response_model=SettingsResponse)
async def update_settings_endpoint(request: UpdateSettingsRequest, user = Depends(get_current_user)):
    """Update application settings"""
    settings = get_settings()
    
    # Update only provided fields
    if request.auto_rotate_on_expiration is not None:
        settings.auto_rotate_on_expiration = request.auto_rotate_on_expiration
    
    if request.auto_rotate_interval_enabled is not None:
        settings.auto_rotate_interval_enabled = request.auto_rotate_interval_enabled
    
    if request.auto_rotate_interval_minutes is not None:
        # Validate minimum interval
        if request.auto_rotate_interval_minutes < 2:
            raise HTTPException(status_code=400, detail="Minimum interval is 2 minutes")
        settings.auto_rotate_interval_minutes = request.auto_rotate_interval_minutes
    
    updated_settings = update_settings(settings)
    logger.info(f"Updated settings: {updated_settings.dict()}")
    
    return SettingsResponse(**updated_settings.dict())


@app.get("/api/logs")
async def get_logs_endpoint(proxy_id: Optional[int] = None, limit: int = 50, user = Depends(get_current_user)):
    """Get logs"""
    logs = get_logs(proxy_id, limit)
    return [log.dict() for log in logs]


# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

