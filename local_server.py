#!/usr/bin/env python3
"""
Local API Server for YouTube Chapter Generator

This script runs a local version of the API server for development and testing.
It has all the same functionality as the Vercel deployment but runs locally,
avoiding any Vercel-specific issues.

Usage:
    python local_server.py

This will start the server at http://localhost:5000
"""
import os
import sys
from api.index import app

# Set host to 0.0.0.0 to make it accessible from other devices on the network
if __name__ == '__main__':
    print("Starting local API server for YouTube Chapter Generator")
    print(f"Python version: {sys.version}")
    
    # Check if OpenAI API key is set
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        print("\nWARNING: OPENAI_API_KEY environment variable is not set!")
        print("The chapter generation functionality will not work.\n")
    
    # Check Decodo credentials
    decodo_user = os.environ.get("DECODO_USERNAME", "")
    decodo_pass = os.environ.get("DECODO_PASSWORD", "")
    if not decodo_user or not decodo_pass:
        print("\nWARNING: Decodo proxy credentials are not configured!")
        print("The API may be rate-limited by YouTube.\n")
    
    # Run the server
    print("\nStarting server at http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    app.run(host='0.0.0.0', port=5000, debug=True) 