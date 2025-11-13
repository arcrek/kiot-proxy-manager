import yaml
import os
from typing import List
from app.models import ProxyKey
import logging

logger = logging.getLogger(__name__)

TRAEFIK_CONFIG_FILE = "/app/traefik/proxies.yml"


def generate_traefik_config(proxies: List[ProxyKey]):
    """
    Generate Traefik dynamic configuration for all active proxies
    
    Args:
        proxies: List of active proxy keys
    """
    try:
        config = {
            "http": {
                "routers": {},
                "services": {}
            }
        }
        
        for proxy in proxies:
            if not proxy.is_active:
                continue
            
            # Router configuration
            router_name = f"{proxy.subdomain}-router"
            config["http"]["routers"][router_name] = {
                "rule": f"Host(`{proxy.subdomain}.{os.getenv('DOMAIN', 'localhost')}`)",
                "service": f"{proxy.subdomain}-service",
                "entryPoints": ["web"]
            }
            
            # Service configuration
            service_name = f"{proxy.subdomain}-service"
            config["http"]["services"][service_name] = {
                "loadBalancer": {
                    "servers": [
                        {"url": f"http://backend:{proxy.port}"}
                    ]
                }
            }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(TRAEFIK_CONFIG_FILE), exist_ok=True)
        
        # Write configuration
        with open(TRAEFIK_CONFIG_FILE, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"Generated Traefik config for {len(proxies)} proxies")
        
    except Exception as e:
        logger.error(f"Failed to generate Traefik config: {e}")
        raise


def remove_proxy_from_traefik(subdomain: str, active_proxies: List[ProxyKey]):
    """
    Remove a proxy from Traefik configuration
    
    Args:
        subdomain: Subdomain to remove
        active_proxies: List of remaining active proxies
    """
    # Simply regenerate the config without the removed proxy
    generate_traefik_config(active_proxies)
    logger.info(f"Removed {subdomain} from Traefik config")

