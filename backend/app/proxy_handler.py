import asyncio
import subprocess
import signal
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Global registry of running proxy processes
proxy_processes: Dict[int, subprocess.Popen] = {}


class ProxyHandler:
    """Manages HTTP proxy server processes"""
    
    def __init__(self, proxy_id: int, port: int, remote_proxy: str):
        self.proxy_id = proxy_id
        self.port = port
        self.remote_proxy = remote_proxy
        self.process: Optional[subprocess.Popen] = None
    
    async def start(self):
        """Start the HTTP proxy server"""
        try:
            # Use proxy.py to create HTTP proxy that forwards through remote proxy
            cmd = [
                "proxy",
                "--hostname", "0.0.0.0",
                "--port", str(self.port),
                "--upstream-proxy", f"http://{self.remote_proxy}",
                "--log-level", "ERROR"
            ]
            
            logger.info(f"Starting proxy handler on port {self.port} -> {self.remote_proxy}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Store in global registry
            proxy_processes[self.proxy_id] = self.process
            
            # Wait a bit to ensure it started
            await asyncio.sleep(0.5)
            
            if self.process.poll() is not None:
                raise Exception(f"Proxy process failed to start on port {self.port}")
            
            logger.info(f"Proxy handler started successfully on port {self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start proxy handler: {e}")
            raise
    
    async def stop(self):
        """Stop the HTTP proxy server"""
        if self.process:
            try:
                logger.info(f"Stopping proxy handler on port {self.port}")
                self.process.send_signal(signal.SIGTERM)
                self.process.wait(timeout=5)
                logger.info(f"Proxy handler stopped on port {self.port}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing proxy handler on port {self.port}")
                self.process.kill()
            except Exception as e:
                logger.error(f"Error stopping proxy handler: {e}")
            finally:
                if self.proxy_id in proxy_processes:
                    del proxy_processes[self.proxy_id]
                self.process = None
    
    async def restart(self, new_remote_proxy: Optional[str] = None):
        """Restart the proxy server with optional new remote proxy"""
        if new_remote_proxy:
            self.remote_proxy = new_remote_proxy
        
        await self.stop()
        await self.start()
    
    def is_running(self) -> bool:
        """Check if proxy is running"""
        if not self.process:
            return False
        return self.process.poll() is None


async def start_proxy_handler(proxy_id: int, port: int, remote_proxy: str) -> ProxyHandler:
    """Start a new proxy handler"""
    handler = ProxyHandler(proxy_id, port, remote_proxy)
    await handler.start()
    return handler


async def stop_proxy_handler(proxy_id: int):
    """Stop a proxy handler"""
    if proxy_id in proxy_processes:
        process = proxy_processes[proxy_id]
        try:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as e:
            logger.error(f"Error stopping proxy {proxy_id}: {e}")
        finally:
            del proxy_processes[proxy_id]


async def restart_proxy_handler(proxy_id: int, port: int, remote_proxy: str):
    """Restart a proxy handler"""
    await stop_proxy_handler(proxy_id)
    await asyncio.sleep(0.5)
    await start_proxy_handler(proxy_id, port, remote_proxy)


def cleanup_all_proxies():
    """Clean up all proxy processes on shutdown"""
    for proxy_id, process in list(proxy_processes.items()):
        try:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=2)
        except:
            process.kill()

