import asyncio
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Global registry of running proxy servers
proxy_servers: Dict[int, dict] = {}


class RawProxyHandler:
    """Raw TCP proxy handler - forwards all data without parsing"""
    
    def __init__(self, proxy_id: int, port: int, remote_proxy: str):
        self.proxy_id = proxy_id
        self.port = port
        # Parse remote_proxy (format: "ip:port")
        remote_parts = remote_proxy.split(':')
        self.remote_host = remote_parts[0]
        self.remote_port = int(remote_parts[1])
        self.server: Optional[asyncio.Server] = None
        
    async def handle_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """Handle incoming client connection"""
        client_addr = client_writer.get_extra_info('peername')
        logger.debug(f"Proxy {self.port}: New connection from {client_addr}")
        
        remote_reader = None
        remote_writer = None
        
        try:
            # Connect to remote KiotProxy
            remote_reader, remote_writer = await asyncio.wait_for(
                asyncio.open_connection(self.remote_host, self.remote_port),
                timeout=10.0
            )
            
            logger.debug(f"Proxy {self.port}: Connected to {self.remote_host}:{self.remote_port}")
            
            # Forward data bidirectionally
            await asyncio.gather(
                self._forward_data(client_reader, remote_writer, "client->remote"),
                self._forward_data(remote_reader, client_writer, "remote->client"),
                return_exceptions=True
            )
            
        except asyncio.TimeoutError:
            logger.error(f"Proxy {self.port}: Connection timeout to {self.remote_host}:{self.remote_port}")
        except Exception as e:
            logger.error(f"Proxy {self.port}: Connection error: {e}")
        finally:
            # Close connections
            if remote_writer:
                try:
                    remote_writer.close()
                    await remote_writer.wait_closed()
                except:
                    pass
            try:
                client_writer.close()
                await client_writer.wait_closed()
            except:
                pass
            
            logger.debug(f"Proxy {self.port}: Connection closed from {client_addr}")
    
    async def _forward_data(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, direction: str):
        """Forward data from reader to writer"""
        try:
            while True:
                data = await reader.read(8192)  # 8KB chunks
                if not data:
                    break
                
                writer.write(data)
                await writer.drain()
                
                logger.debug(f"Proxy {self.port}: Forwarded {len(data)} bytes ({direction})")
                
        except asyncio.CancelledError:
            # Connection closed normally
            pass
        except Exception as e:
            logger.debug(f"Proxy {self.port}: Forward error ({direction}): {e}")
    
    async def start(self, retry=True):
        """Start the raw TCP proxy server"""
        try:
            # Check if port is already in use by this proxy
            if self.proxy_id in proxy_servers:
                logger.warning(f"Proxy {self.proxy_id} already exists, stopping old instance")
                await self.stop()
                await asyncio.sleep(0.3)
            
            # Start TCP server
            self.server = await asyncio.start_server(
                self.handle_client,
                '0.0.0.0',
                self.port,
                reuse_address=True,
                reuse_port=True
            )
            
            # Store in global registry
            proxy_servers[self.proxy_id] = {
                'handler': self,
                'port': self.port,
                'remote': f"{self.remote_host}:{self.remote_port}"
            }
            
            logger.info(f"Raw TCP proxy started on port {self.port} -> {self.remote_host}:{self.remote_port}")
            
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
            raise
    
    async def stop(self):
        """Stop the proxy server"""
        try:
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            if self.proxy_id in proxy_servers:
                del proxy_servers[self.proxy_id]
                
            logger.info(f"Proxy stopped on port {self.port}")
            
        except Exception as e:
            logger.error(f"Error stopping proxy: {e}")
    
    async def restart(self, new_remote_proxy: Optional[str] = None):
        """Restart proxy with new remote"""
        if new_remote_proxy:
            remote_parts = new_remote_proxy.split(':')
            self.remote_host = remote_parts[0]
            self.remote_port = int(remote_parts[1])
        await self.stop()
        await self.start()
    
    def is_running(self) -> bool:
        """Check if proxy is running"""
        return self.proxy_id in proxy_servers


async def start_proxy_handler(proxy_id: int, port: int, remote_proxy: str):
    """Start a new raw TCP proxy handler"""
    handler = RawProxyHandler(proxy_id, port, remote_proxy)
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

