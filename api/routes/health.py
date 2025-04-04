"""
Health check endpoints
"""
import requests
from flask import Flask, jsonify

from api.config import Config
from api.utils.responses import create_error_response


def register_health_routes(app: Flask) -> None:
    """
    Register health check routes with the Flask app
    
    Args:
        app: Flask application instance
    """
    @app.route('/', methods=['GET'])
    def root():
        """Simple health check"""
        return "API is running. Try /api for more details.", 200

    @app.route('/api', methods=['GET'])
    def hello():
        """API status endpoint with detailed diagnostics"""
        try:
            # Test direct connection to YouTube
            direct_connection_success = False
            try:
                # Create a fresh session for this test
                with requests.Session() as test_session:
                    test_session.proxies.clear()
                    response = test_session.get("https://www.youtube.com", timeout=5)
                    direct_connection_success = response.status_code == 200
            except Exception as e:
                print(f"Direct connection test failed: {e}")
                direct_connection_success = False
            
            # Test proxy connection to YouTube if configured
            proxy_connection_success = None
            proxy_configured = bool(Config.get_proxy_dict())
            if proxy_configured:
                try:
                    with requests.Session() as test_session:
                        test_session.proxies.update(Config.get_proxy_dict())
                        response = test_session.get("https://www.youtube.com", timeout=5)
                        proxy_connection_success = response.status_code == 200
                except Exception as e:
                    print(f"Proxy connection test failed: {e}")
                    proxy_connection_success = False

            # Configure CORS for the response
            response_data = {
                'success': True,
                'status': 'API is operational',
                'version': '1.0.0',
                'config': {
                    'openai_key_configured': bool(Config.OPENAI_API_KEY),
                    'proxy_configured': proxy_configured,
                },
                'connectivity': {
                    'direct_youtube': direct_connection_success,
                    'proxy_youtube': proxy_connection_success,
                }
            }
            
            # Prepare response
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
            response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
            
            return response
            
        except Exception as e:
            return create_error_response(f"Error in status check: {str(e)}", 500)
