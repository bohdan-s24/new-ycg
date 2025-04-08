from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/auth/login/google', methods=['POST'])
def login_via_google():
    """
    Test endpoint for Google login
    """
    logger.info("Google login request received")
    
    if not request.is_json:
        logger.error("Request is not JSON")
        return jsonify({"success": False, "error": "Request must be JSON"}), 400
    
    data = request.get_json()
    logger.info(f"Request data: {data}")
    
    token = data.get('token')
    platform = data.get('platform', 'web')
    
    if not token:
        logger.error("Missing token in request")
        return jsonify({"success": False, "error": "Missing token in request"}), 400
    
    logger.info(f"Token: {token}")
    logger.info(f"Platform: {platform}")
    
    # For testing, just return a successful response
    return jsonify({
        "success": True,
        "data": {
            "access_token": "test_access_token",
            "token_type": "bearer",
            "new_user": False
        }
    })

@app.route('/api/auth/user', methods=['GET'])
def get_user_info():
    """
    Test endpoint for getting user info
    """
    logger.info("User info request received")
    
    # Check for Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logger.error("Missing or invalid Authorization header")
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    # Extract token
    token = auth_header.split(' ')[1]
    logger.info(f"Token: {token}")
    
    # For testing, just return a successful response
    return jsonify({
        "success": True,
        "data": {
            "id": "test_user_id",
            "email": "test@example.com",
            "name": "Test User",
            "email_verified": True,
            "credits": 3,
            "created_at": "2023-01-01T00:00:00Z"
        }
    })

if __name__ == '__main__':
    logger.info("Starting test server on http://localhost:5000")
    app.run(debug=True, port=5000)
