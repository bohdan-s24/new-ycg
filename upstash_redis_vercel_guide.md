# Configuring Upstash Redis with Vercel

This guide explains how to properly configure Upstash Redis with Vercel for your Flask application.

## Understanding Upstash Redis Connection Methods

Upstash Redis offers two ways to connect:

1. **Traditional Redis Protocol** (`rediss://` URLs)
2. **REST API** (HTTP-based, using `https://` URLs)

When using Upstash Redis with Vercel, the REST API method is recommended because:
- It works well with serverless functions
- It doesn't require maintaining persistent connections
- It's more compatible with Vercel's architecture

## Setting Up Upstash Redis in Vercel

### 1. Create an Upstash Redis Database

1. Go to [Upstash Console](https://console.upstash.com/)
2. Create a new Redis database
3. Choose the region closest to your Vercel deployment
4. Note down the connection details:
   - REST API endpoint (https://...)
   - REST API token

### 2. Configure Vercel Environment Variables

In your Vercel project settings, add these environment variables:

1. `REDIS_URL`: The REST API endpoint (https://...)
2. `KV_REST_API_TOKEN`: The REST API token

If you're using the Vercel KV integration, these variables might be set automatically.

### 3. Handling Traditional Redis URLs

If you're using a traditional Redis URL (starting with `rediss://`), you need to convert it to the REST API format:

```python
# Example Redis URL: rediss://default:password@fast-monarch-12345.upstash.io:6379

# Extract the hostname
hostname = "fast-monarch-12345.upstash.io"

# Convert to REST API URL
rest_url = f"https://{hostname}"

# Use the password as the token if needed
token = "password"
```

## Code Implementation

Here's how to implement the Upstash Redis connection in your Flask application:

```python
from upstash_redis.asyncio import Redis as UpstashRedisAsync
import logging

async def get_redis_connection():
    """
    Initializes and returns an async upstash-redis connection.
    """
    redis_url = os.environ.get("REDIS_URL")
    rest_token = os.environ.get("KV_REST_API_TOKEN")
    
    # Convert traditional Redis URL to REST API format if needed
    if redis_url and redis_url.startswith('rediss://'):
        try:
            # Extract hostname from the URL
            parts = redis_url.split('@')
            if len(parts) > 1:
                hostname = parts[1].split(':')[0]
                redis_url = f"https://{hostname}"
                
                # If no token is provided, extract it from the URL
                if not rest_token:
                    password_part = parts[0].split(':')
                    if len(password_part) > 2:
                        rest_token = password_part[2]
        except Exception as e:
            logging.error(f"Error parsing Redis URL: {e}")
    
    # Connect using the Upstash Redis client
    redis_client = UpstashRedisAsync(url=redis_url, token=rest_token)
    
    # Test the connection
    await redis_client.ping()
    
    return redis_client
```

## Debugging Redis Connection Issues

If you're having issues connecting to Upstash Redis, try these debugging steps:

### 1. Check Environment Variables

Make sure the environment variables are set correctly:

```python
import os

redis_url = os.environ.get("REDIS_URL")
token = os.environ.get("KV_REST_API_TOKEN")

print(f"Redis URL: {redis_url[:10]}... (truncated)")
print(f"Token available: {bool(token)}")
```

### 2. Test the Connection

Create a debug endpoint to test the Redis connection:

```python
@app.route('/api/debug/redis', methods=['GET'])
async def debug_redis():
    try:
        redis = await get_redis_connection()
        await redis.set('test_key', 'test_value')
        value = await redis.get('test_key')
        await redis.delete('test_key')
        
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

### 3. Check Upstash Console

In the Upstash Console:
1. Verify that your database is active
2. Check the connection details
3. Look at the metrics to see if there are any connection attempts

## Common Issues and Solutions

### 1. "Unsupported Protocol 'rediss://'"

**Problem**: The Upstash Redis client doesn't support the traditional Redis protocol.

**Solution**: Convert the Redis URL to the REST API format:
```python
if redis_url.startswith('rediss://'):
    parts = redis_url.split('@')
    if len(parts) > 1:
        hostname = parts[1].split(':')[0]
        redis_url = f"https://{hostname}"
```

### 2. "Authentication Failed"

**Problem**: The REST API token is incorrect or missing.

**Solution**: Make sure the `KV_REST_API_TOKEN` environment variable is set correctly. If not, extract the password from the Redis URL:
```python
if not rest_token:
    parts = redis_url.split('@')
    if len(parts) > 0:
        password_part = parts[0].split(':')
        if len(password_part) > 2:
            rest_token = password_part[2]
```

### 3. "Connection Timeout"

**Problem**: The Redis server is not reachable.

**Solution**: 
- Check if the Redis database is active
- Verify that the hostname is correct
- Make sure your Vercel region can access the Upstash region

## Best Practices

1. **Use Environment Variables**: Store connection details in environment variables
2. **Handle Both URL Formats**: Support both traditional Redis URLs and REST API URLs
3. **Add Detailed Logging**: Log connection attempts and errors for debugging
4. **Implement Connection Pooling**: Reuse Redis connections when possible
5. **Add Error Handling**: Gracefully handle Redis connection errors

## Conclusion

By following this guide, you should be able to successfully connect your Vercel-deployed Flask application to Upstash Redis using the REST API. Remember to use the debug endpoints to troubleshoot any issues that arise.
