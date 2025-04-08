"""
Routes package for the API
"""
from flask import Flask

# Import blueprints or registration functions
from api.routes.health import register_health_routes
# Remove old chapter route registration function import
# from api.routes.chapters import register_chapter_routes 
from api.routes.chapters import chapters_bp # Import the chapters blueprint
from api.routes.auth import auth_bp # Import the auth blueprint
from api.routes.credits import credits_bp # Import the credits blueprint


def register_all_routes(app: Flask) -> None:
    """
    Register all routes with the Flask app

    Args:
        app: Flask application instance
    """
    # Existing routes
    register_health_routes(app)
    # Remove old chapter route registration call
    # register_chapter_routes(app) 

    # Register the new blueprints
    app.register_blueprint(chapters_bp) 
    app.register_blueprint(auth_bp)
    app.register_blueprint(credits_bp)
