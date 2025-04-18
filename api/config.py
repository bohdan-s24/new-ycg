import os
from typing import Optional, Dict, Any


class Config:
    """Centralized configuration management"""
    # Environment variables
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    WEBSHARE_USERNAME = os.environ.get("WEBSHARE_USERNAME")
    WEBSHARE_PASSWORD = os.environ.get("WEBSHARE_PASSWORD")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") # Loaded from Vercel env
    REDIS_URL = os.environ.get("REDIS_URL") # Full Upstash URL (e.g., rediss://...)
    KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN") # Use the Vercel KV token variable name

    # Google OAuth Client ID
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

    # Stripe Keys
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY") # Loaded from Vercel env
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET") # Loaded from Vercel env

    # Frontend URL (needed for Stripe Checkout redirects)
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000") # Default for local dev

    # API configurations
    OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini"]
    TRANSCRIPT_LANGUAGES = ["en", "en-US", "en-GB"]

    # Timeout settings
    REDIS_TIMEOUT = 30  # seconds
    API_TIMEOUT = 30    # seconds
    REQUEST_TIMEOUT = 30  # seconds

    # Connection pooling
    REDIS_POOL_SIZE = 10
    REDIS_MAX_CONNECTIONS = 20

    # Rate limiting
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW = 60  # seconds

    # Credit plans
    FREE_CREDITS = 3
    BASIC_PLAN_CREDITS = 10
    BASIC_PLAN_PRICE = 9
    PREMIUM_PLAN_CREDITS = 50
    PREMIUM_PLAN_PRICE = 29


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
