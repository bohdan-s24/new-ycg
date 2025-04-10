# Google OAuth Configuration Guide for Chrome Extensions

This guide explains how to properly configure Google OAuth for Chrome extensions, specifically for the YouTube Chapter Generator extension.

## 1. Google Cloud Console Configuration

### Step 1: Access the Google Cloud Console

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (the one with client ID: 373897257675-i561f2gcpv310b61bptj0ge2bmvdm03m.apps.googleusercontent.com)
3. Navigate to "APIs & Services" > "Credentials"

### Step 2: Configure the OAuth Client ID

Find your OAuth client ID in the list and click on it to edit. For Chrome extensions, you need to configure:

1. **Application type**: Make sure it's set to "Chrome App"

2. **Application ID**: This should be your Chrome extension's ID
   - For development, this is visible in chrome://extensions when you load your extension in developer mode
   - For production, this is the ID assigned by the Chrome Web Store

3. **Authorized JavaScript origins**:
   - Add `chrome-extension://<your-extension-id>`

4. **Authorized redirect URIs**:
   - Add `https://<your-extension-id>.chromiumapp.org/`
   - This is the special redirect URI format for Chrome extensions

### Step 3: Enable Required APIs

Make sure the following APIs are enabled for your project:
- Google People API
- Google OAuth2 API

## 2. Chrome Extension Configuration

### Step 1: Update manifest.json

Ensure your manifest.json has the correct OAuth2 configuration:

```json
"oauth2": {
  "client_id": "373897257675-i561f2gcpv310b61bptj0ge2bmvdm03m.apps.googleusercontent.com",
  "scopes": [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
  ]
}
```

### Step 2: Add Required Permissions

Make sure your manifest.json includes the necessary permissions:

```json
"permissions": ["identity", "storage", "activeTab"]
```

### Step 3: Configure Content Security Policy

For Manifest V3, ensure your CSP allows connections to the necessary domains:

```json
"content_security_policy": {
  "extension_pages": "script-src 'self'; object-src 'self'; connect-src 'self' https://new-ycg.vercel.app https://www.googleapis.com"
}
```

## 3. Backend Configuration

### Step 1: Verify Token Handling

Make sure your backend is correctly configured to handle OAuth tokens from Chrome extensions:

```python
# In auth_service.py
async def verify_google_oauth_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifies a Google OAuth token by fetching user info and returns it if valid."""
    # Google's userinfo endpoint
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Make request to Google's API
    async with httpx.AsyncClient() as client:
        response = await client.get(userinfo_url, headers=headers)
    
    # Process response
    if response.status_code == 200:
        userinfo = response.json()
        # Validate and return user info
        return userinfo
    
    return None
```

### Step 2: Ensure Route Registration

Make sure your login route is properly registered:

```python
@auth_bp.route('/login/google', methods=['POST'])
async def login_via_google():
    # Handle login logic
    pass
```

## 4. Testing Your Configuration

To test if your OAuth configuration is working correctly:

1. Load your extension in Chrome
2. Open the developer console
3. Click the Google Sign-In button
4. Check the console logs for any errors
5. If you see a 500 error from your server, check the server logs for more details

## 5. Troubleshooting

### Common Issues:

1. **Incorrect Extension ID**: Make sure the extension ID in Google Cloud Console matches your actual extension ID
2. **Missing Permissions**: Ensure your extension has the "identity" permission in the manifest
3. **Incorrect Scopes**: Verify that the scopes in your manifest match the ones you're requesting
4. **Server Validation Errors**: Your server might be rejecting the token because it's not configured to accept tokens from your client ID

### Debugging Steps:

1. Check Chrome extension console for errors
2. Verify the token is being sent correctly to your backend
3. Check server logs for detailed error messages
4. Test your server's token validation logic with a known good token

## 6. Additional Resources

- [Chrome Identity API Documentation](https://developer.chrome.com/docs/extensions/reference/identity/)
- [Google OAuth 2.0 for Client-side Web Applications](https://developers.google.com/identity/protocols/oauth2/javascript-implicit-flow)
- [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
