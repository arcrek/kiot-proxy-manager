import asyncio
import httpx
import os
import logging
from datetime import datetime, timedelta
from typing import List
from app.database import (
    get_settings,
    get_active_proxies,
    update_proxy,
    add_log
)
from app.kiotproxy import kiotproxy_client
from app.proxy_handler import restart_proxy_handler

logger = logging.getLogger(__name__)


async def health_check_worker():
    """Background worker for health checking proxies"""
    interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
    
    logger.info(f"Starting health check worker (interval: {interval}s)")
    
    while True:
        try:
            proxies = get_active_proxies()
            
            for proxy in proxies:
                try:
                    # Test proxy by making a request through it
                    start_time = datetime.now()
                    
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        # Use the internal port to test
                        proxies_dict = {
                            "http://": f"http://127.0.0.1:{proxy.port}",
                            "https://": f"http://127.0.0.1:{proxy.port}"
                        }
                        
                        try:
                            response = await client.get(
                                "http://google.com",
                                proxies=proxies_dict
                            )
                            
                            # Calculate latency
                            latency = int((datetime.now() - start_time).total_seconds() * 1000)
                            
                            # Update proxy status
                            proxy.status = "active"
                            proxy.latency_ms = latency
                            proxy.last_check_at = datetime.now().isoformat()
                            
                        except Exception as e:
                            logger.warning(f"Proxy {proxy.id} health check failed: {e}")
                            proxy.status = "error"
                            proxy.latency_ms = 0
                            proxy.last_check_at = datetime.now().isoformat()
                    
                    # Save updated proxy
                    update_proxy(proxy)
                    
                except Exception as e:
                    logger.error(f"Health check error for proxy {proxy.id}: {e}")
            
            await asyncio.sleep(interval)
            
        except Exception as e:
            logger.error(f"Health check worker error: {e}")
            await asyncio.sleep(interval)


async def auto_rotation_worker():
    """Background worker for automatic proxy rotation"""
    interval = int(os.getenv("AUTO_ROTATION_CHECK_INTERVAL", "30"))
    
    logger.info(f"Starting auto-rotation worker (interval: {interval}s)")
    
    while True:
        try:
            settings = get_settings()
            proxies = get_active_proxies()
            
            # Option 1: Rotate on expiration
            if settings.auto_rotate_on_expiration:
                await rotate_expired_proxies(proxies)
            
            # Option 2: Rotate on interval
            if settings.auto_rotate_interval_enabled:
                await rotate_by_interval(proxies, settings.auto_rotate_interval_minutes)
            
            await asyncio.sleep(interval)
            
        except Exception as e:
            logger.error(f"Auto-rotation worker error: {e}")
            await asyncio.sleep(interval)


async def rotate_expired_proxies(proxies: List):
    """Rotate proxies that have expired"""
    now = datetime.now()
    
    for proxy in proxies:
        try:
            if not proxy.expiration_at:
                continue
            
            expiration = datetime.fromisoformat(proxy.expiration_at)
            
            # Rotate if expired or about to expire in 1 minute
            if now >= expiration - timedelta(minutes=1):
                logger.info(f"Auto-rotating proxy {proxy.id} (expiration)")
                
                # Get new proxy from KiotProxy
                new_remote = await kiotproxy_client.get_new_proxy(
                    proxy.kiotproxy_key,
                    proxy.region
                )
                
                # Update proxy handler
                await restart_proxy_handler(
                    proxy.id,
                    proxy.port,
                    new_remote["http"]
                )
                
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
                proxy.last_rotated_at = datetime.now().isoformat()
                
                update_proxy(proxy)
                add_log(proxy.id, "auto_rotate_expiration", "success", proxy.region, "Rotated on expiration")
                
                logger.info(f"Successfully rotated proxy {proxy.id} to {proxy.remote_ip}")
                
        except Exception as e:
            logger.error(f"Failed to rotate expired proxy {proxy.id}: {e}")
            add_log(proxy.id, "auto_rotate_expiration", "failed", proxy.region, str(e))


async def rotate_by_interval(proxies: List, interval_minutes: int):
    """Rotate proxies based on time interval"""
    now = datetime.now()
    
    for proxy in proxies:
        try:
            if not proxy.last_rotated_at:
                # If never rotated, use creation time
                last_rotated = datetime.fromisoformat(proxy.created_at)
            else:
                last_rotated = datetime.fromisoformat(proxy.last_rotated_at)
            
            minutes_since_rotation = (now - last_rotated).total_seconds() / 60
            
            # Rotate if interval has passed
            if minutes_since_rotation >= interval_minutes:
                logger.info(f"Auto-rotating proxy {proxy.id} (interval: {interval_minutes}min)")
                
                # Get new proxy from KiotProxy
                new_remote = await kiotproxy_client.get_new_proxy(
                    proxy.kiotproxy_key,
                    proxy.region
                )
                
                # Update proxy handler
                await restart_proxy_handler(
                    proxy.id,
                    proxy.port,
                    new_remote["http"]
                )
                
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
                proxy.last_rotated_at = datetime.now().isoformat()
                
                update_proxy(proxy)
                add_log(proxy.id, "auto_rotate_interval", "success", proxy.region, 
                       f"Rotated on {interval_minutes}min interval")
                
                logger.info(f"Successfully rotated proxy {proxy.id} to {proxy.remote_ip}")
                
        except Exception as e:
            logger.error(f"Failed to rotate proxy {proxy.id} by interval: {e}")
            add_log(proxy.id, "auto_rotate_interval", "failed", proxy.region, str(e))

