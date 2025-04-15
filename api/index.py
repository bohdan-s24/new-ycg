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

app = Sanic("new-ygc")
Extend(app)  # Enables asgi property, among other features

# Register blueprints
app.blueprint(auth_bp)
app.blueprint(chapters_bp)
app.blueprint(credits_bp)
app.blueprint(health_bp)
app.blueprint(payment_bp)

# Note: Do NOT call app.run() here for Vercel/ASGI deployment.
asgi = app.asgi  # Vercel will look for 'asgi' or 'app'
