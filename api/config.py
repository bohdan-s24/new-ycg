import os
from typing import Optional, Dict, Any


class Config:
    """Centralized configuration management"""
    # Environment variables
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") # Loaded from Vercel env
    REDIS_URL = os.environ.get("REDIS_URL") # Full Upstash URL (e.g., rediss://...)
    KV_REST_API_TOKEN = os.environ.get("KV_REST_API_TOKEN") # Use the Vercel KV token variable name

    # Google OAuth Client ID
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

    # Stripe Keys
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY") # Loaded from Vercel env
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET") # Loaded from Vercel env

    # Frontend URL (needed for Stripe Checkout redirects)
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://ycg-frontend.vercel.app") # Updated to new frontend domain

    # Stripe URLs
    STRIPE_SUCCESS_URL = "https://ycg-frontend.vercel.app/payment-success.html"
    STRIPE_CANCEL_URL = "https://ycg-frontend.vercel.app/payment-cancel.html"

    # API configurations
    OPENAI_MODELS = ["gpt-4.1-mini", "gpt-4o"]
    # Language codes in order of preference (English first, then other languages)
    TRANSCRIPT_LANGUAGES = [
        # English (various locales)
        "en", "en-US", "en-GB",
        # Ukrainian
        "uk",
        # Polish
        "pl",
        # German
        "de",
        # Spanish
        "es", "es-ES", "es-419",
        # Italian
        "it",
        # French
        "fr", "fr-FR", "fr-CA",
        # Japanese
        "ja",
        # Chinese (Simplified and Traditional)
        "zh", "zh-Hans", "zh-Hant", "zh-CN", "zh-TW"
    ]

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

    # Proxy configuration for Decodo
    DECODO_USERNAME = os.environ.get("DECODO_USERNAME")
    DECODO_PASSWORD = os.environ.get("DECODO_PASSWORD")
    DECODO_HOST = "gate.decodo.com"
    DECODO_PORT = 7000

    @classmethod
    def get_proxy_url(cls) -> Optional[str]:
        """Get proxy URL if Decodo credentials are available"""
        if cls.DECODO_USERNAME and cls.DECODO_PASSWORD:
            return f"http://{cls.DECODO_USERNAME}:{cls.DECODO_PASSWORD}@{cls.DECODO_HOST}:{cls.DECODO_PORT}"
        return None

    @classmethod
    def get_proxy_dict(cls) -> Optional[Dict[str, str]]:
        """Get proxy dictionary for requests/httpx"""
        proxy_url = cls.get_proxy_url()
        if proxy_url:
            return {
                'http': proxy_url,
                'https': proxy_url
            }
        return None
