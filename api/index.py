"""
Entry point for Vercel serverless functions
This file maintains backward compatibility while using the new modular structure
"""
import os
import sys
from flask import Flask

# We need to create app here for Vercel to import it directly
from api import create_app

# Create the Flask application
app = create_app()

# For local development (when run directly)
if __name__ == '__main__':
    app.run(debug=True)
