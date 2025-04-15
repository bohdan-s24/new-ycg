"""
Health check endpoints
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import logging
import os
from ..utils.db import redis_operation
import requests
import asyncio

router = APIRouter()

@router.get("/health")
def health():
    return JSONResponse(content={"status": "ok"})

@router.get("/debug/routes")
def debug_routes():
    """Debug endpoint to list all registered routes"""
    routes = []
    for route in router.routes:
        routes.append({
            'endpoint': route.path,
            'methods': route.methods,
            'path': route.path
        })

    return JSONResponse(content={
        'routes': routes,
        'total_routes': len(routes)
    })

@router.get("/debug/redis")
def debug_redis():
    """Debug endpoint to check Redis connection"""
    env_vars = {k: v for k, v in os.environ.items() if k.startswith("REDIS")}
    async def _test_redis(redis):
        await redis.set("debug_test", "ok")
        return await redis.get("debug_test")
    try:
        test_value = asyncio.run(redis_operation("debug_test", _test_redis, None))
        return JSONResponse(content={
            'redis_connected': True,
            'test_value': test_value,
            'environment': env_vars
        })
    except Exception as e:
        logging.error(f"Redis debug test failed: {str(e)}")
        return JSONResponse(content={
            'error': f"Redis connection failed: {str(e)}",
            'redis_connected': False,
            'environment': env_vars
        }, status_code=500)

@router.get("/connectivity")
def connectivity_check():
    """Check connectivity to external services"""
    try:
        direct_connection_success = False
        try:
            with requests.Session() as test_session:
                test_session.proxies.clear()
                response = test_session.get("https://www.youtube.com", timeout=5)
                direct_connection_success = response.status_code == 200
        except Exception as e:
            logging.error(f"Direct connection test failed: {e}")
            direct_connection_success = False
        proxy_connection_success = None
        if os.environ.get("HTTPS_PROXY"):
            try:
                with requests.Session() as test_session:
                    response = test_session.get("https://www.youtube.com", timeout=5)
                    proxy_connection_success = response.status_code == 200
            except Exception as e:
                logging.error(f"Proxy connection test failed: {e}")
                proxy_connection_success = False
        return JSONResponse(content={
            'status': 'API is operational',
            'version': '1.0.0',
            'config': {
                'direct_connection_success': direct_connection_success,
                'proxy_connection_success': proxy_connection_success
            }
        })
    except Exception as e:
        logging.error(f"Error in connectivity check: {str(e)}")
        return JSONResponse(content={'error': f"Error checking connectivity: {str(e)}"}, status_code=500)
