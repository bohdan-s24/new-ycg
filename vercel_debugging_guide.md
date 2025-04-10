# Debugging Vercel Serverless Functions

This guide provides detailed instructions for debugging issues with Vercel serverless functions, particularly for Flask applications.

## Understanding Vercel Logs

Vercel provides several types of logs that can help diagnose issues:

1. **Build Logs**: Show errors during the build process
2. **Function Logs**: Show runtime errors and console output
3. **Edge Logs**: Show errors in edge functions (if used)

## Accessing Logs in Vercel Dashboard

1. Go to your Vercel dashboard
2. Select your project
3. Go to "Deployments" > [latest deployment]
4. Click on "Functions"
5. Select the function to view its logs

## Common Error Types and Solutions

### 1. 500 Internal Server Error

A 500 error indicates that something went wrong on the server side. Common causes include:

- **Unhandled Exceptions**: Add try/except blocks to catch and log errors
- **Missing Dependencies**: Ensure all required packages are installed
- **Configuration Issues**: Check environment variables and configuration settings
- **Memory/CPU Limits**: Vercel has limits on function resources

### 2. 404 Not Found Error

A 404 error indicates that the requested resource was not found. Common causes include:

- **Route Not Registered**: Check that the route is properly registered
- **URL Mismatch**: Ensure the client is using the correct URL
- **Blueprint Prefix Issues**: Check blueprint URL prefixes

### 3. CORS Errors

CORS errors occur when a client tries to access a resource from a different origin. Common causes include:

- **Missing CORS Headers**: Ensure CORS headers are properly configured
- **Incorrect Origin**: Check that the client's origin is allowed
- **Preflight Requests**: Ensure OPTIONS requests are handled correctly

## Adding Debug Endpoints

Debug endpoints can provide valuable information about your application's state:

```python
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
```

## Enhanced Logging

Add detailed logging to help diagnose issues:

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/example', methods=['POST'])
def example_route():
    try:
        logger.info("Request received at /api/example")
        logger.info(f"Request data: {request.json}")
        
        # Process request
        result = process_request(request.json)
        
        logger.info(f"Request processed successfully: {result}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
```

## Debugging Blueprint Issues

Flask blueprints can be tricky to debug. Here are some tips:

1. **Check Blueprint Registration**:
   ```python
   # Debug endpoint to check blueprint registration
   @app.route('/api/debug/blueprints', methods=['GET'])
   def debug_blueprints():
       blueprints = []
       for name, blueprint in app.blueprints.items():
           blueprints.append({
               'name': name,
               'url_prefix': blueprint.url_prefix
           })
       return jsonify({
           'success': True,
           'blueprints': blueprints,
           'total_blueprints': len(blueprints)
       })
   ```

2. **Check URL Prefixes**:
   - Ensure blueprint URL prefixes are correct
   - Remember that Vercel functions are accessed via `/api/[filename]`
   - Blueprint routes are prefixed with the blueprint's `url_prefix`

## Debugging Environment Variables

Environment variables can be a common source of issues:

```python
@app.route('/api/debug/env', methods=['GET'])
def debug_env():
    # Don't expose sensitive values in production!
    env_vars = {}
    for key in ['NODE_ENV', 'VERCEL_ENV', 'VERCEL_REGION']:
        env_vars[key] = os.environ.get(key, 'Not set')
    
    # Check if required variables are set (without exposing values)
    for key in ['JWT_SECRET_KEY', 'REDIS_URL', 'OPENAI_API_KEY']:
        env_vars[key] = 'Set' if os.environ.get(key) else 'Not set'
    
    return jsonify({
        'success': True,
        'environment': env_vars
    })
```

## Testing Locally with Vercel CLI

Test your application locally before deploying:

```bash
# Install vercel CLI
npm install -g vercel

# Run locally
vercel dev
```

## Debugging Redis Connection Issues

Redis connection issues are common in serverless environments:

```python
@app.route('/api/debug/redis', methods=['GET'])
async def debug_redis():
    try:
        r = await get_redis_connection()
        await r.set('test_key', 'test_value')
        value = await r.get('test_key')
        await r.delete('test_key')
        
        return jsonify({
            'success': True,
            'redis_connected': True,
            'test_value': value
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'redis_connected': False,
            'error': str(e)
        }), 500
```

## Debugging Authentication Issues

Authentication issues can be difficult to diagnose:

```python
@app.route('/api/debug/auth', methods=['GET'])
async def debug_auth():
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({
            'success': False,
            'error': 'No valid Authorization header found'
        }), 401
    
    token = auth_header.split(' ')[1]
    
    try:
        # Don't expose sensitive data in production!
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return jsonify({
            'success': True,
            'token_valid': True,
            'payload': {
                'sub': payload.get('sub'),
                'exp': payload.get('exp')
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'token_valid': False,
            'error': str(e)
        }), 401
```

## Best Practices for Debugging

1. **Start Simple**: Begin with simple debug endpoints that don't require authentication
2. **Isolate Issues**: Test one component at a time
3. **Use Try/Except**: Wrap code in try/except blocks to catch and log errors
4. **Check Logs Frequently**: Monitor logs after each deployment
5. **Test Locally First**: Use the Vercel CLI to test locally before deploying

## Conclusion

Debugging Vercel serverless functions requires a systematic approach. By adding debug endpoints, enhancing logging, and following best practices, you can quickly identify and fix issues in your application.
