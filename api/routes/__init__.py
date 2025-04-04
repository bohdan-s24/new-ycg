"""
Routes package for the API
"""
from flask import Flask

from api.routes.health import register_health_routes
from api.routes.chapters import register_chapter_routes


def register_all_routes(app: Flask) -> None:
    """
    Register all routes with the Flask app
    
    Args:
        app: Flask application instance
    """
    register_health_routes(app)
    register_chapter_routes(app)
