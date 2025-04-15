"""
Entry point for Vercel serverless functions
This file maintains backward compatibility while using the new modular structure
"""
import os
import sys
from sanic import Sanic
from sanic_ext import Extend

# We need to create app here for Vercel to import it directly
from api.routes.auth import auth_bp
from api.routes.chapters import chapters_bp
from api.routes.credits import credits_bp
from api.routes.health import health_bp
from api.routes.payment import payment_bp

sanic_app = Sanic("new-ygc")
Extend(sanic_app)  # Enables asgi property, among other features

# Register blueprints
sanic_app.blueprint(auth_bp)
sanic_app.blueprint(chapters_bp)
sanic_app.blueprint(credits_bp)
sanic_app.blueprint(health_bp)
sanic_app.blueprint(payment_bp)

# Note: Do NOT call app.run() here for Vercel/ASGI deployment.
app = sanic_app.asgi  # Export as 'app' for Vercel ASGI compatibility
