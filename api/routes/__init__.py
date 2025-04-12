"""
Routes package for the API
"""
from flask import Flask
import logging

# Import blueprints
from api.routes.health import health_bp
from api.routes.chapters import chapters_bp
from api.routes.auth import auth_bp
from api.routes.credits import credits_bp
from api.routes.payment import payment_bp


def register_all_routes(app: Flask) -> None:
    """
    Register all routes with the Flask app

    Args:
        app: Flask application instance
    """
    # Register all blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(chapters_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(credits_bp)
    app.register_blueprint(payment_bp)

    # Log registered routes
    logging.info(f"Registered blueprints: health, chapters, auth, credits, payment")
