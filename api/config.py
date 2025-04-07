import os
from typing import Optional, Dict, Any


class Config:
    """Centralized configuration management"""
    # Environment variables
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    WEBSHARE_USERNAME = os.environ.get("WEBSHARE_USERNAME")
    WEBSHARE_PASSWORD = os.environ.get("WEBSHARE_PASSWORD")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") # Loaded from Vercel env
    REDIS_URL = os.environ.get("REDIS_URL") # Loaded from Vercel env (Upstash)
    # Google OAuth Client ID (for verifying ID tokens from frontend)
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID") # Loaded from Vercel env

    # API configurations
    OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini"]
    TRANSCRIPT_LANGUAGES = ["en", "en-US", "en-GB"]

    
    # Proxy configuration
    @classmethod
    def get_proxy_url(cls) -> Optional[str]:
        """Get proxy URL if credentials are available"""
        if cls.WEBSHARE_USERNAME and cls.WEBSHARE_PASSWORD:
            return f"http://{cls.WEBSHARE_USERNAME}:{cls.WEBSHARE_PASSWORD}@p.webshare.io:80"
        return None
    
    @classmethod
    def get_proxy_dict(cls) -> Optional[Dict[str, str]]:
        """Get proxy dictionary for requests"""
        proxy_url = cls.get_proxy_url()
        if proxy_url:
            return {
                'http': proxy_url,
                'https': proxy_url
            }
        return None
    
    @classmethod
    def get_webshare_proxy_config(cls) -> Any:
        """Get WebshareProxyConfig for youtube_transcript_api"""
        from youtube_transcript_api.proxies import WebshareProxyConfig
        
        if cls.WEBSHARE_USERNAME and cls.WEBSHARE_PASSWORD:
            return WebshareProxyConfig(
                proxy_username=cls.WEBSHARE_USERNAME,
                proxy_password=cls.WEBSHARE_PASSWORD
            )
        return None
