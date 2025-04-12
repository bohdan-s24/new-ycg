"""
API versioning utilities.
"""

import logging
from flask import Blueprint, jsonify, request


class VersionedBlueprint(Blueprint):
    """
    A Flask Blueprint that supports versioning.
    
    This class extends Flask's Blueprint to add version prefixes to routes.
    """
    
    def __init__(self, name, import_name, version="v1", **kwargs):
        """
        Initialize a versioned blueprint.
        
        Args:
            name: The name of the blueprint
            import_name: The import name of the blueprint
            version: The API version (default: "v1")
            **kwargs: Additional arguments to pass to Blueprint
        """
        self.version = version
        
        # Set the URL prefix to include the version
        url_prefix = kwargs.get("url_prefix", "")
        kwargs["url_prefix"] = f"/api/{version}{url_prefix}"
        
        super().__init__(name, import_name, **kwargs)
        
    def route(self, rule, **options):
        """
        Register a route with the blueprint.
        
        Args:
            rule: The URL rule
            **options: Additional options to pass to Blueprint.route
            
        Returns:
            The route decorator
        """
        # Log the versioned route
        logging.debug(f"Registering versioned route: {self.url_prefix}{rule}")
        return super().route(rule, **options)


def create_version_blueprint(app):
    """
    Create a blueprint for API version information.
    
    Args:
        app: The Flask application
        
    Returns:
        A Flask Blueprint for API version information
    """
    version_bp = Blueprint("version", __name__, url_prefix="/api")
    
    @version_bp.route("/version", methods=["GET"])
    def get_version():
        """Get API version information."""
        versions = {
            "current": "v1",
            "supported": ["v1"],
            "deprecated": [],
            "latest": "v1"
        }
        return jsonify({"success": True, "versions": versions})
    
    @version_bp.route("/", methods=["GET"])
    def api_root():
        """API root endpoint."""
        return jsonify({
            "success": True,
            "message": "YouTube Chapter Generator API",
            "version": "v1",
            "documentation": "/api/docs"
        })
    
    return version_bp
