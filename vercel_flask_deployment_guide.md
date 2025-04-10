# Vercel Deployment Guide for Flask Applications

This guide explains how to properly configure and deploy Flask applications on Vercel, with a focus on handling routes correctly.

## Understanding Vercel's Serverless Architecture

Vercel's serverless architecture works differently from traditional web servers:

1. **Serverless Functions**: Each file in the `/api` directory becomes a separate serverless function
2. **URL Structure**: Functions are accessed via `/api/[filename]`
3. **Flask Integration**: When using Flask, all routes are handled by a single function (usually `api/index.py`)

## Key Configuration Files

### 1. vercel.json

The `vercel.json` file is crucial for configuring how Vercel handles your application:

```json
{
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "rewrites": [
    { "source": "/api/(.*)", "destination": "api/index.py" },
    { "source": "/(.*)", "destination": "api/index.py" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Origin", "value": "*" },
        { "key": "Access-Control-Allow-Methods", "value": "GET, POST, PUT, DELETE, OPTIONS" },
        { "key": "Access-Control-Allow-Headers", "value": "X-Requested-With, Content-Type, Accept" }
      ]
    }
  ]
}
```

This configuration:
- Builds the `api/index.py` file using the Python builder
- Rewrites all requests to be handled by `api/index.py`
- Sets CORS headers for all routes

### 2. api/index.py

This is the entry point for your Flask application:

```python
"""
Entry point for Vercel serverless functions
"""
from flask import Flask

# Import the create_app function
from api import create_app

# Create the Flask application
app = create_app()

# For local development (when run directly)
if __name__ == '__main__':
    app.run(debug=True)
```

### 3. Blueprint Registration

When registering blueprints, be careful with URL prefixes:

```python
# Create a blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Register the blueprint
app.register_blueprint(auth_bp)
```

## URL Structure in Vercel

Understanding the URL structure is crucial:

1. **Vercel Function Path**: `/api/index.py` (the serverless function)
2. **Flask App Routes**: Handled by the Flask app in `index.py`
3. **Blueprint Routes**: Prefixed with the blueprint's `url_prefix`

For example:
- A route defined as `@auth_bp.route('/login')` with `url_prefix='/auth'`
- Will be accessible at `https://your-app.vercel.app/auth/login` (NOT `/api/auth/login`)

## Common Issues and Solutions

### 1. 404 Errors

If you're getting 404 errors:

- **Check URL Prefixes**: Make sure your client is using the correct URL structure
- **Check Blueprint Registration**: Ensure blueprints are registered with the correct prefixes
- **Check Vercel Rewrites**: Make sure all requests are being routed to your Flask app

### 2. CORS Issues

If you're having CORS issues:

- **Check Headers in vercel.json**: Make sure the CORS headers are correctly configured
- **Check Flask CORS Configuration**: If using Flask-CORS, ensure it's properly set up

### 3. Environment Variables

Make sure all required environment variables are set in the Vercel dashboard:

1. Go to your Vercel dashboard
2. Select your project
3. Go to "Settings" > "Environment Variables"
4. Add all required variables

## Debugging Vercel Deployments

### 1. Use Debug Endpoints

Create debug endpoints to help diagnose issues:

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

### 2. Check Vercel Logs

Vercel provides detailed logs for each function:

1. Go to your Vercel dashboard
2. Select your project
3. Go to "Deployments" > [latest deployment]
4. Click on "Functions"
5. Select the function to view its logs

### 3. Local Testing

Test your application locally before deploying:

```bash
# Install vercel CLI
npm install -g vercel

# Run locally
vercel dev
```

## Best Practices

1. **Keep URL Structure Consistent**: Use the same URL structure in both your client and server code
2. **Use Environment Variables**: Store sensitive information in environment variables
3. **Minimize Function Size**: Keep your functions small to avoid hitting Vercel's size limits
4. **Use Proper Error Handling**: Implement proper error handling to make debugging easier
5. **Add Detailed Logging**: Add detailed logging to help diagnose issues

## Conclusion

Deploying Flask applications on Vercel requires careful attention to URL structure and routing. By following this guide, you should be able to avoid common pitfalls and successfully deploy your Flask application on Vercel.
