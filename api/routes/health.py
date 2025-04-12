"""
Health check endpoints
"""
import requests
import logging
from flask import jsonify, current_app

from ..config import Config
from ..utils.responses import success_response, error_response
from ..utils.versioning import VersionedBlueprint

# Create a versioned blueprint
health_bp = VersionedBlueprint('health', __name__, url_prefix='/health')

@health_bp.route('/', methods=['GET'])
def health_check():
    """Simple health check"""
    return success_response({
        "status": "API is operational",
        "version": "1.0.0"
    })

@health_bp.route('/debug/routes', methods=['GET'])
def debug_routes():
    """Debug endpoint to list all registered routes"""

    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': [method for method in rule.methods if method not in ['HEAD', 'OPTIONS']],
            'path': str(rule)
        })

    return success_response({
        'routes': routes,
        'total_routes': len(routes)
    })

@health_bp.route('/debug/redis', methods=['GET'])
async def debug_redis():
    """Debug endpoint to check Redis connection"""
    from ..utils.db import redis_operation
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

    # Define the Redis test operation
    async def _test_redis(redis, _):
        await redis.set('debug_test', 'ok')
        test_value = await redis.get('debug_test')
        await redis.delete('debug_test')
        return test_value

    # Try to connect to Redis
    try:
        test_value = await redis_operation("debug_test", _test_redis, None)
        return success_response({
            'redis_connected': True,
            'test_value': test_value,
            'environment': env_vars
        })
    except Exception as e:
        logging.error(f"Redis debug test failed: {str(e)}")
        return error_response(f"Redis connection failed: {str(e)}", 500, {
            'redis_connected': False,
            'environment': env_vars
        })

@health_bp.route('/connectivity', methods=['GET'])
def connectivity_check():
    """Check connectivity to external services"""
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
            logging.error(f"Direct connection test failed: {e}")
            direct_connection_success = False

        # Test proxy connection to YouTube if configured
        proxy_connection_success = None
        proxy_configured = bool(Config.get_proxy_dict()) if hasattr(Config, 'get_proxy_dict') else False
        if proxy_configured:
            try:
                with requests.Session() as test_session:
                    test_session.proxies.update(Config.get_proxy_dict())
                    response = test_session.get("https://www.youtube.com", timeout=5)
                    proxy_connection_success = response.status_code == 200
            except Exception as e:
                logging.error(f"Proxy connection test failed: {e}")
                proxy_connection_success = False

        # Return connectivity information
        return success_response({
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
        })
    except Exception as e:
        logging.error(f"Error in connectivity check: {str(e)}")
        return error_response(f"Error checking connectivity: {str(e)}", 500)
