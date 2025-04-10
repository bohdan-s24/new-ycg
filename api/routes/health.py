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

    @app.route('/api/debug/routes', methods=['GET'])
    def debug_routes():
        """Debug endpoint to list all registered routes"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': [method for method in rule.methods if method not in ['HEAD', 'OPTIONS']],
                'path': str(rule)
            })

        return jsonify({
            'success': True,
            'routes': routes,
            'total_routes': len(routes)
        })

    @app.route('/api/debug/redis', methods=['GET'])
    async def debug_redis():
        """Debug endpoint to check Redis connection"""
        from ..utils.db import get_redis_connection
        from ..config import Config
        import os

        # Get environment variables (without exposing sensitive values)
        env_vars = {
            'REDIS_URL_FORMAT': 'rediss://' if Config.REDIS_URL and Config.REDIS_URL.startswith('rediss://') else 'other',
            'REDIS_URL_LENGTH': len(Config.REDIS_URL) if Config.REDIS_URL else 0,
            'REDIS_URL_PREFIX': Config.REDIS_URL[:10] + '...' if Config.REDIS_URL and len(Config.REDIS_URL) > 10 else None,
            'KV_REST_API_TOKEN_AVAILABLE': bool(Config.KV_REST_API_TOKEN),
            'KV_REST_API_TOKEN_LENGTH': len(Config.KV_REST_API_TOKEN) if Config.KV_REST_API_TOKEN else 0,
            'VERCEL_ENV': os.environ.get('VERCEL_ENV', 'unknown'),
            'VERCEL_REGION': os.environ.get('VERCEL_REGION', 'unknown')
        }

        # Try to connect to Redis
        try:
            redis = await get_redis_connection()
            # Try a simple operation
            await redis.set('debug_test', 'ok')
            test_value = await redis.get('debug_test')
            await redis.delete('debug_test')

            return jsonify({
                'success': True,
                'redis_connected': True,
                'test_value': test_value,
                'environment': env_vars
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'redis_connected': False,
                'error': str(e),
                'environment': env_vars
            }), 500

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
