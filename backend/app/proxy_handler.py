import asyncio
import httpx
from typing import Dict, Optional
import logging
from aiohttp import web

logger = logging.getLogger(__name__)

# Global registry of running proxy servers
proxy_servers: Dict[int, dict] = {}


class LightweightProxyHandler:
    """Lightweight async HTTP proxy handler - uses minimal RAM"""
    
    def __init__(self, proxy_id: int, port: int, remote_proxy: str):
        self.proxy_id = proxy_id
        self.port = port
        self.remote_proxy = remote_proxy
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
    async def handle_request(self, request: web.Request) -> web.Response:
        """Forward HTTP request through remote proxy"""
        try:
            # Build target URL
            target_url = f"{request.scheme}://{request.host}{request.path_qs}"
            
            # Create proxy URL (httpx uses 'proxies' dict, not 'proxy')
            proxy_url = f"http://{self.remote_proxy}"
            
            # Forward request through proxy
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=30.0,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=50, max_keepalive_connections=10)
            ) as client:
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=dict(request.headers),
                    content=await request.read() if request.body_exists else None,
                )
                
                # Return response
                return web.Response(
                    body=response.content,
                    status=response.status_code,
                    headers=dict(response.headers)
                )
                
        except Exception as e:
            logger.error(f"Proxy error on port {self.port}: {e}")
            return web.Response(text=f"Proxy Error: {str(e)}", status=502)
    
    async def start(self, retry=True):
        """Start the lightweight proxy server"""
        try:
            # Check if port is already in use by this proxy
            if self.proxy_id in proxy_servers:
                logger.warning(f"Proxy {self.proxy_id} already exists, stopping old instance")
                await self.stop()
                await asyncio.sleep(0.3)
            
            app = web.Application()
            app.router.add_route('*', '/{path:.*}', self.handle_request)
            
            self.runner = web.AppRunner(app, access_log=None)  # Disable access log to save RAM
            await self.runner.setup()
            
            # Use reuse_address for better port handling
            self.site = web.TCPSite(
                self.runner, 
                '0.0.0.0', 
                self.port,
                reuse_address=True
            )
            await self.site.start()
            
            # Store in global registry
            proxy_servers[self.proxy_id] = {
                'handler': self,
                'port': self.port,
                'remote': self.remote_proxy
            }
            
            logger.info(f"Lightweight proxy started on port {self.port} -> {self.remote_proxy}")
            
        except OSError as e:
            if retry and (e.errno == 98 or 'address already in use' in str(e).lower()):
                logger.warning(f"Port {self.port} is already in use. Attempting cleanup...")
                # Try to stop any existing handler on this port
                cleaned = False
                for pid, data in list(proxy_servers.items()):
                    if data['port'] == self.port and pid != self.proxy_id:
                        logger.info(f"Found conflicting proxy {pid} on port {self.port}, stopping it...")
                        try:
                            await stop_proxy_handler(pid)
                            cleaned = True
                        except Exception as cleanup_err:
                            logger.error(f"Failed to cleanup proxy {pid}: {cleanup_err}")
                        break
                
                if cleaned:
                    await asyncio.sleep(0.5)
                    # Retry once without retry flag to prevent infinite loop
                    await self.start(retry=False)
                else:
                    raise Exception(f"Port {self.port} is in use and couldn't be cleaned up")
            else:
                logger.error(f"Failed to bind to port {self.port}: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to start proxy handler on port {self.port}: {e}")
            # Cleanup runner if it was created
            if self.runner:
                try:
                    await self.runner.cleanup()
                except:
                    pass
            raise
    
    async def stop(self):
        """Stop the proxy server"""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            
            if self.proxy_id in proxy_servers:
                del proxy_servers[self.proxy_id]
                
            logger.info(f"Proxy stopped on port {self.port}")
            
        except Exception as e:
            logger.error(f"Error stopping proxy: {e}")
    
    async def restart(self, new_remote_proxy: Optional[str] = None):
        """Restart proxy with new remote"""
        if new_remote_proxy:
            self.remote_proxy = new_remote_proxy
        await self.stop()
        await self.start()
    
    def is_running(self) -> bool:
        """Check if proxy is running"""
        return self.proxy_id in proxy_servers


async def start_proxy_handler(proxy_id: int, port: int, remote_proxy: str):
    """Start a new lightweight proxy handler"""
    handler = LightweightProxyHandler(proxy_id, port, remote_proxy)
    await handler.start()
    return handler


async def stop_proxy_handler(proxy_id: int):
    """Stop a proxy handler"""
    if proxy_id in proxy_servers:
        handler = proxy_servers[proxy_id]['handler']
        await handler.stop()


async def restart_proxy_handler(proxy_id: int, port: int, remote_proxy: str):
    """Restart a proxy handler"""
    await stop_proxy_handler(proxy_id)
    await asyncio.sleep(0.2)
    await start_proxy_handler(proxy_id, port, remote_proxy)


async def cleanup_all_proxies():
    """Clean up all proxy servers on shutdown"""
    for proxy_id in list(proxy_servers.keys()):
        try:
            await stop_proxy_handler(proxy_id)
        except Exception as e:
            logger.error(f"Error cleaning up proxy {proxy_id}: {e}")

