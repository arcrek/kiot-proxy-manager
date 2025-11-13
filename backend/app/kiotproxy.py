import httpx
import os
from typing import Dict, Optional


class KiotProxyClient:
    def __init__(self):
        self.base_url = os.getenv("KIOTPROXY_API_BASE", "https://api.kiotproxy.com/api/v1")
        self.timeout = 30.0
    
    async def get_new_proxy(self, key: str, region: str = "random") -> Dict:
        """
        Get new proxy or change proxy
        
        Args:
            key: KiotProxy API key
            region: Region ('bac', 'trung', 'nam', or 'random')
        
        Returns:
            Dict with proxy information
        
        Raises:
            Exception if request fails
        """
        url = f"{self.base_url}/proxies/new"
        params = {"key": key, "region": region}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            if not data.get("success"):
                error_msg = data.get("message", "Unknown error")
                raise Exception(f"KiotProxy API error: {error_msg}")
            
            return data["data"]
    
    async def get_current_proxy(self, key: str) -> Dict:
        """
        Get current proxy information
        
        Args:
            key: KiotProxy API key
        
        Returns:
            Dict with current proxy information
        
        Raises:
            Exception if request fails
        """
        url = f"{self.base_url}/proxies/current"
        params = {"key": key}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            if not data.get("success"):
                error_msg = data.get("message", "Unknown error")
                raise Exception(f"KiotProxy API error: {error_msg}")
            
            return data["data"]
    
    async def exit_proxy(self, key: str) -> bool:
        """
        Exit proxy from key
        
        Args:
            key: KiotProxy API key
        
        Returns:
            True if successful
        
        Raises:
            Exception if request fails
        """
        url = f"{self.base_url}/proxies/out"
        params = {"key": key}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            if not data.get("success"):
                error_msg = data.get("message", "Unknown error")
                raise Exception(f"KiotProxy API error: {error_msg}")
            
            return data["data"]


# Global client instance
kiotproxy_client = KiotProxyClient()

