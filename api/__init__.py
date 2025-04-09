"""
API package initialization
"""
import os
import sys
import traceback
import time
import stripe # Import stripe
import logging # Import logging
from flask import Flask
from flask_cors import CORS

from api.config import Config
from api.routes import register_all_routes


def create_app() -> Flask:
    """
    Create and configure the Flask application

    Returns:
        Configured Flask application instance
    """
    # Print debug info
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Files in current directory: {os.listdir()}")

    # Create Flask app
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    print("Flask app created and CORS configured")

    # Print config information
    print(f"Environment variables loaded: OPENAI_API_KEY={'✓' if Config.OPENAI_API_KEY else '✗'}, "
          f"WEBSHARE_USERNAME={'✓' if Config.WEBSHARE_USERNAME else '✗'}, "
          f"WEBSHARE_PASSWORD={'✓' if Config.WEBSHARE_PASSWORD else '✗'}, "
          f"JWT_SECRET_KEY={'✓' if Config.JWT_SECRET_KEY else '✗'}, "
          f"REDIS_URL={'✓' if Config.REDIS_URL else '✗'}, "
          f"STRIPE_SECRET_KEY={'✓' if Config.STRIPE_SECRET_KEY else '✗'}, " # Corrected key name
          f"STRIPE_WEBHOOK_SECRET={'✓' if Config.STRIPE_WEBHOOK_SECRET else '✗'}")
    
    # Initialize Stripe
    if Config.STRIPE_SECRET_KEY:
        stripe.api_key = Config.STRIPE_SECRET_KEY
        logging.info("Stripe API key configured.")
    else:
        logging.warning("Stripe API key not found in environment variables. Payment features will be disabled.")

    # Register routes
    register_all_routes(app)
    
    return app
